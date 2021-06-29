# -*- coding: utf-8 -*-
# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# System imports
import ast
import importlib
from pathlib import Path

# Third-party imports
import yaml

# Local imports
from openide.utils import RecursiveDict


def mark_setup(mark, is_static=True):
    '''Function decorator intended to mark the decorated function as one that participate in
    OpenIDE setup system.'''
    def _inner(func):
        func.openide_setup = mark
        if is_static:
            return staticmethod(func)
        else:
            return func
    return _inner


class LoadNameFinder(ast.NodeVisitor):

    @classmethod
    def find(cls, root):
        finder = cls()
        finder.visit(root)
        return finder.found

    def __init__(self):
        self.reset()

    def reset(self):
        self.found = []

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.found.append(node)
        self.generic_visit(node)


class SetupFinder(ast.NodeVisitor):
    '''Will walk the AST of a parsed module to search for class decorated with a decorator that
    itself has been marked as a setup function (with mark_setup() decorator above)'''

    def __init__(self, module_path):
        self.module_path = module_path
        self.config = RecursiveDict()  # We merge all the configs returned by config decorators
        self.qualpath = []  # Stack of class hierarchy inside the module
        self.imports = {}  # code name: (module path to import, module attribute to get)

    def visit_Import(self, node):
        '''Store import references'''
        for name in node.names:
            code_name = name.asname if name.asname else name.name
            self.imports[code_name] = name.name.split('.')[:-1], name.name

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        '''Store import references, handle possible relative imports'''
        base_path = []
        if node.level:  # Is relative, just back up in our self.module_path
            base_path += self.module_path.split('.')[:-node.level]
        if node.module:  # Can be None in case of a "from . import something"
            base_path.append(node.module)
        base_path = '.'.join(base_path)

        for name in node.names:
            code_name = name.asname if name.asname else name.name
            self.imports[code_name] = base_path, name.name

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        '''Check decorators of a class to see if one has been marked by our mark_setup()'''
        # For when a class is referencing another class in the same module:
        self.imports[node.name] = self.module_path, node.name

        self.qualpath.append(node.name)
        for decorator in node.decorator_list:
            # Setup decorators needs to be callable by us (and not just be a pure decorator).
            # Ie. in the form of "@decorator(...)", and not just "@decorator".
            if not isinstance(decorator, ast.Call):
                continue

            def get_full_path(elem):
                '''Walk down the AST to get the full path of the decorator'''
                if isinstance(elem, ast.Name):
                    yield elem.id
                elif isinstance(elem, ast.Attribute):
                    yield from get_full_path(elem.value)
                    yield elem.attr

            path = list(get_full_path(decorator.func))
            # path[0] is the class owning the decorator
            # path[1:] is the rest of the path to the decorator itself
            # print('>>>', '.'.join(self.qualpath), '.'.join(path))

            try:
                # From path[0], we lookup which module needs to be imported, and what is
                # the module attribute corresponding to path[0] (it could have an "as" alias)
                to_import, attr_name = self.imports[path[0]]
                module = importlib.import_module(to_import)
                decorator_owner = getattr(module, attr_name)
                # print('>>> Loaded', decorator_owner)

                # Go down to the actual decorator function
                attr = decorator_owner
                for attr_name in path[1:]:
                    attr = getattr(attr, attr_name)
                decorator_func = attr

            except (KeyError, ImportError, AttributeError) as ex:
                # Ignores:
                # - Decorator (or its owner) not actually imported
                # - Not importable module (might not be installed yet)
                # - Non-existant path to decorator function
                # print('>>>', 'ERR', type(ex), ex)
                continue

            # print('>>> Function is', func, hasattr(func, 'openide_setup'))
            if not hasattr(decorator_func, 'openide_setup'):
                continue

            # print('>>> openide_setup is', getattr(func, 'openide_setup'))
            setup_type = getattr(decorator_func, 'openide_setup')
            if setup_type == 'config':
                self.do_config(node, decorator, path, decorator_owner)

        self.generic_visit(node)
        self.qualpath.pop()

    def do_config(self, node, decorator, path, decorator_owner):
        '''Excecute the decorator function, passing it an additional "_config" kwarg.
        This is a dictionary containing various info about the actual target class this function
        is decorating.

        The function should then fill up the _config dict with more data that should be written to
        the package egg-info "openide.yaml" file.

        To actually execute the function, instead of trying to parse the AST to reconstruct a call,
        we just compile that part of the AST, and then we eval() it.
        '''

        glbs = {}
        lcls = {}
        # We will let eval(compile(...)) load the function from its owner. So, we need to at least
        # put the owner object in the locals() dict of the eval.
        # lcls[path[0]] = decorator_owner

        for elem in set([elem.id for elem in LoadNameFinder.find(decorator)]):
            try:
                to_import, attr_name = self.imports[elem]
                module = importlib.import_module(to_import)
                lcls[elem] = getattr(module, attr_name)

            except (KeyError, ImportError, AttributeError) as ex:
                # Silently ignores:
                # - Decorator (or its owner) not actually imported
                # - Not importable module (might not be installed yet)
                # - Non-existant path to decorator function
                # print('>>>', 'ERR', type(ex), ex)
                continue

        # Provide info about the target class the function decorates
        self.config['_fqname'] = f"{self.module_path}:{'.'.join(self.qualpath)}"

        # To pass the config dict to the function, the actual dict is loaded in the locals() as
        # "openide_setup" variable. Then, we manipulate the AST to include the additional "_config"
        # kwarg, that will reference this "openide_setup" local variable.
        lcls['openide_setup'] = self.config
        decorator.keywords.append(ast.keyword(
            '_config', ast.Name(id='openide_setup', ctx=ast.Load())
        ))

        ast.fix_missing_locations(decorator)  # Needed to resolve lineno
        # print('>>>', eval(compile(ast.Expression(decorator), '<string>', 'eval'), glbs, lcls))
        eval(compile(ast.Expression(decorator), Path(self.module_path).resolve(), 'eval'), glbs, lcls)

        # At this point, our own self.config dict should have been updated with whatever the
        # decorator added. We just need to purge the target class info.
        del self.config['_fqname']


def setup(cmd, basename, filename):
    '''This is a setuptools hook for writing an egg-info file.
    It gets triggered by any (third party) package build that already have openide installed in its
    environment. Which means an openide "plugin" package would need to at least declare openide as a
    setup dependency for this process to work.

    The point of this setup process is to figure out what is to be declared in the egg-info file
    openide.yaml, such that it can be "discovered" at run time by the openide framework machinery.
    That's how, for instance, it will add menu entries, load default components in the GUI,
    pre-populate some lookups, register lookup listeners, or load some service providers.

    We are going to load and parse every python file of this package. We will walk their AST,
    searching for class decorators that have been marked as part of the openide setup system, and
    execute this decorator calls only, such that they can provide us with data to write to this
    egg-info file.
    '''

    config = RecursiveDict()
    for pkg in cmd.distribution.packages:  # For every sub-package discovered in this package
        pkg_path = Path(pkg.replace('.', '/'))
        for module_file in pkg_path.glob('*.py'):  # For every .py file of this sub-pacakge
            tree = ast.parse(module_file.read_text(), filename=module_file.name)
            finder = SetupFinder(f'{pkg}.{module_file.stem}')
            finder.visit(tree)
            config.merge(finder.config)

    # We now have all the relevant config declared in all python modules of this package
    config = config.prune_none().to_dict()
    if config:
        result = yaml.dump(config)
    else:
        result = None  # If nothing to config, will delete any previous openide.yaml
    cmd.write_or_delete_file('OpenIDE setup', filename, result)
