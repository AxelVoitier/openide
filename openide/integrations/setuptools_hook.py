# Copyright (c) 2021 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import yaml

# Local imports
from openide.integrations.parser import parse_file
from openide.utils import RecursiveDict

if TYPE_CHECKING:
    from setuptools.command.egg_info import egg_info


def egg_info_writer(cmd: egg_info, basename: str, filename: str) -> None:
    """This is a setuptools hook for writing an egg-info file.
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
    """
    # raise RuntimeError(f'{basename=}, {filename=}')

    config = RecursiveDict()
    for pkg in cmd.distribution.packages:  # For every sub-package discovered in this package
        pkg_path = Path(pkg.replace('.', '/'))
        for module_file in pkg_path.glob('*.py'):  # For every .py file of this sub-pacakge
            file_config = parse_file(pkg, module_file)

            if file_config:
                print(f'[{pkg}] Collected the following config:')  # noqa: T201
                print(yaml.dump(file_config.to_dict()))  # noqa: T201

                config.merge(file_config)

    # We now have all the relevant config declared in all python modules of this package
    config = config.prune_none().to_dict()
    # If nothing to config, will delete any previous openide.yaml
    result = yaml.dump(config) if config else None
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    cmd.write_or_delete_file('OpenIDE setup', filename, result)
