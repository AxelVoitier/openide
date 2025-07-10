# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import ast
import builtins
import contextlib
import importlib
import sys
from pathlib import Path
from pprint import pformat
from typing import TYPE_CHECKING, override

# Third-party imports
# Local imports
from openide.utils import RecursiveDict

if TYPE_CHECKING:
    from ast import Call, ClassDef, Import, ImportFrom, Name, expr
    from collections.abc import Iterator
    from typing import Any


class LoadNameFinder(ast.NodeVisitor):
    @classmethod
    def find(cls, root: Call) -> list[Name]:
        finder = cls()
        finder.visit(root)
        return finder.found

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.found: list[Name] = []

    @override
    def visit_Name(self, node: Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.found.append(node)
        self.generic_visit(node)


class SetupFinder(ast.NodeVisitor):
    """Will walk the AST of a parsed module to search for class decorated with a decorator that
    itself has been marked as a setup function (with mark_setup() decorator above)"""

    def __init__(self, module_path: str) -> None:
        super().__init__()

        self.module_path = module_path
        self.config = RecursiveDict()  # We merge all the configs returned by config decorators
        self.qualpath: list[str] = []  # Stack of class hierarchy inside the module
        self.imports: dict[
            str,
            tuple[str, str],  # code name: (module path to import, module attribute to get)
        ] = {}

    @override
    def visit_Import(self, node: Import) -> None:
        """Store import references"""
        for name in node.names:
            code_name = name.asname if name.asname else name.name
            self.imports[code_name] = name.name.split('.')[:-1], name.name

        self.generic_visit(node)

    @override
    def visit_ImportFrom(self, node: ImportFrom) -> None:
        """Store import references, handle possible relative imports"""
        base_path = []
        if node.level:  # Is relative, just back up in our self.module_path
            base_path += self.module_path.split('.')[: -node.level]
        if node.module:  # Can be None in case of a "from . import something"
            base_path.append(node.module)
        base_path = '.'.join(base_path)

        for name in node.names:
            code_name = name.asname if name.asname else name.name
            self.imports[code_name] = base_path, name.name

        self.generic_visit(node)

    @override
    def visit_ClassDef(self, node: ClassDef) -> None:
        """Check decorators of a class to see if one has been marked by our mark_setup()"""
        # For when a class is referencing another class in the same module:
        self.imports[node.name] = self.module_path, node.name

        # print(f'ClassDef {node.name}')

        self.qualpath.append(node.name)
        for decorator in node.decorator_list:
            # Setup decorators needs to be callable by us (and not just be a pure decorator).
            # Ie. in the form of "@decorator(...)", and not just "@decorator".
            if not isinstance(decorator, ast.Call):
                continue

            def get_full_path(elem: expr) -> Iterator[str]:
                """Walk down the AST to get the full path of the decorator"""
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
                # print(
                #     f'[{self.module_path}] {to_import=}, {attr_name=}: {ex}',
                # )

                # Ignores:
                # - Decorator (or its owner) not actually imported
                # - Not importable module (might not be installed yet)
                # - Non-existant path to decorator function
                continue

            # print('>>> Function is', decorator_func, hasattr(decorator_func, 'openide_setup'))
            if not hasattr(decorator_func, 'openide_setup'):
                continue

            # print('>>> openide_setup is', getattr(decorator_func, 'openide_setup'))
            # setup_type = getattr(decorator_func, 'openide_setup')
            setup_type = decorator_func.openide_setup
            if setup_type == 'config':
                self.do_config(node, decorator, path, decorator_owner)

        self.generic_visit(node)
        self.qualpath.pop()

    def do_config(
        self,
        node: ClassDef,
        decorator: Call,
        path: list[str],
        decorator_owner: Any,  # noqa: ANN401
    ) -> None:
        """Excecute the decorator function, passing it an additional "_config" kwarg.
        This is a dictionary containing various info about the actual target class this function
        is decorating.

        The function should then fill up the _config dict with more data that should be written to
        the package egg-info "openide.yaml" file.

        To actually execute the function, instead of trying to parse the AST to reconstruct a call,
        we just compile that part of the AST, and then we eval() it.
        """

        glbs = {}
        lcls = {}
        # We will let eval(compile(...)) load the function from its owner. So, we need to at least
        # put the owner object in the locals() dict of the eval.
        # lcls[path[0]] = decorator_owner

        for elem in {elem.id for elem in LoadNameFinder.find(decorator)}:
            try:
                to_import, attr_name = self.imports[elem]
            except KeyError as ex:
                if hasattr(builtins, elem):
                    continue

                print(
                    f'[{self.module_path}] Cannot import {elem} as it is not even '
                    f'declared in the file',
                )
                raise

            try:
                module = importlib.import_module(to_import)
                lcls[elem] = getattr(module, attr_name)

            except (KeyError, ImportError, AttributeError) as ex:  # noqa: PERF203
                print(
                    f'[{self.module_path}] Cannot import {elem} ({to_import=}, {attr_name=}): {ex}',
                )
                raise
                # Silently ignores:
                # - Decorator (or its owner) not actually imported
                # - Not importable module (might not be installed yet)
                # - Non-existant path to decorator function
                # continue

        # Provide info about the target class the function decorates
        self.config['_fqname'] = f'{self.module_path}:{".".join(self.qualpath)}'

        # To pass the config dict to the function, the actual dict is loaded in the locals() as
        # "openide_setup" variable. Then, we manipulate the AST to include the additional "_config"
        # kwarg, that will reference this "openide_setup" local variable.
        lcls['openide_setup'] = self.config
        decorator.keywords.append(
            ast.keyword('_config', ast.Name(id='openide_setup', ctx=ast.Load())),
        )

        ast.fix_missing_locations(decorator)  # Needed to resolve lineno
        # print('>>>', eval(compile(ast.Expression(decorator), '<string>', 'eval'), glbs, lcls))
        eval(  # noqa: S307
            compile(ast.Expression(decorator), Path(self.module_path).resolve(), 'eval'),
            glbs,
            lcls,
        )

        # At this point, our own self.config dict should have been updated with whatever the
        # decorator added. We just need to purge the target class info.
        del self.config['_fqname']


def parse_file(pkg: str, file_path: Path, base_path: str = '') -> RecursiveDict:
    # print(f'parsing {file_path} ({pkg=}, {base_path=})')

    with contextlib.ExitStack() as exit_stack:
        if base_path:
            sys.path.insert(0, base_path)
            exit_stack.callback(sys.path.pop, 0)

        try:
            tree = ast.parse(file_path.read_text(), filename=file_path.name)
        except Exception:  # noqa: BLE001
            return RecursiveDict()

        finder = SetupFinder(f'{pkg}.{file_path.stem}')
        finder.visit(tree)

        return finder.config
