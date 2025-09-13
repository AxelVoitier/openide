# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# spell-checker:enableCompoundWords
# spell-checker:words
# spell-checker:ignore

from __future__ import annotations

# System imports
import logging
from typing import TYPE_CHECKING, Any

# Third-party imports
from lookups import DelegatedLookup, Item, Lookup, ProxyLookup
from rich import print  # noqa: A004
from rich.tree import Tree
from typer import Typer

# Local imports
from openide.config import load_config
from openide.startup.main import IDEApplication

_logger = logging.getLogger(__name__)


cmd = Typer()
config_cli = Typer()
cmd.add_typer(config_cli, name='config')
lookup_cli = Typer()
cmd.add_typer(lookup_cli, name='lookup')


@config_cli.command('show')
def config_show() -> None:
    def per_package_cb(package_name: str, config: str) -> None:
        print(f'Found config for package {package_name}:')
        print('----------')
        print(config.strip())
        print('----------')
        print()

    full_config = load_config(per_package_cb)

    def handle_value(k: str, v: Any, tree: Tree) -> None:
        if isinstance(v, dict):
            sub_tree = tree.add(k)
            traverse(v, sub_tree)
        elif isinstance(v, list):
            sub_tree = tree.add(k)
            for vv in v:
                handle_value('-', vv, sub_tree)
        else:
            tree.add(f'{k}: {v}')

    def traverse(config: dict[str, Any], tree: Tree) -> None:
        for k, v in config.items():
            handle_value(k, v, tree)

    root_tree = Tree('Final config:', guide_style='bold bright_green')
    traverse(full_config, root_tree)
    print(root_tree)


@lookup_cli.command('ls')
def lookup_ls() -> None:
    default_lookup = Lookup.get_default()

    visited: set[Lookup] = set()
    root_tree = Tree('Lookups content:', guide_style='bold bright_blue')

    def class_fqname(obj: object | type) -> str:
        cls = obj if isinstance(obj, type) else type(obj)
        return f'{cls.__module__}.[bold]{cls.__qualname__}[/bold]'

    def add_item(item: Item[Any], tree: Tree) -> Tree:
        return tree.add(f'[grey]{class_fqname(item.get_type())}')

    def traverse(lookup: Lookup, tree: Tree) -> None:
        if lookup in visited:
            tree.add(f'[green]...{class_fqname(lookup)}...')
            return
        else:
            visited.add(lookup)

            if isinstance(lookup, ProxyLookup):
                sub_tree = tree.add(f'(proxy) [green]{class_fqname(lookup)}[/]')
                for instance in lookup._lookups:
                    traverse(instance, sub_tree)
            elif isinstance(lookup, DelegatedLookup):
                sub_tree = tree.add(
                    f'(delegated) [green]{class_fqname(lookup)}[/] (provider: {class_fqname(lookup._provider)})'
                )
                traverse(lookup._lookup, sub_tree)
            else:
                sub_tree = tree.add(f'[green]{class_fqname(lookup)}[/]')
                items = lookup.lookup_result(object).all_items()
                for item in items:
                    if issubclass(item.get_type(), Lookup):
                        traverse(item.get_instance(), sub_tree)
                    else:
                        add_item(item, sub_tree)

    traverse(default_lookup, root_tree)

    print(root_tree)


@cmd.command()
def app(name: str | None = None) -> None:
    app = IDEApplication(app_name=name)
    app.start()
