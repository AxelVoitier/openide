# Copyright (c) 2025 Contributors as noted in the AUTHORS file
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import annotations

# System imports
import contextlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

# Third-party imports
import yaml
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

# Local imports
from openide.integrations.parser import parse_file
from openide.utils import RecursiveDict

if TYPE_CHECKING:
    from typing import Any


class OpenIDEYAMLBuildHook(BuildHookInterface):
    PLUGIN_NAME = 'openide_integrations'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__temp_dir: Path | None = None

    @property
    def temp_dir(self) -> Path:
        if self.__temp_dir is None:
            self.__temp_dir = Path(tempfile.mkdtemp()).absolute()

        return self.__temp_dir

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if self.target_name != 'wheel':
            return

        config = RecursiveDict()
        for file in self.build_config.builder.recurse_included_files():
            if not file.path.endswith('.py'):
                continue
            base_path = file.path.replace(file.relative_path, '').rstrip('/')
            path = Path(file.path)
            pkg = str(Path(file.distribution_path).parent).replace('/', '.')
            file_config = parse_file(pkg, path, base_path)

            if file_config:
                self.app.display_info(f'[{file.distribution_path}] Collected the following config:')
                self.app.display_info(yaml.dump(file_config.to_dict()))

                config.merge(file_config)

        # We now have all the relevant config declared in all python modules of this package
        config = config.prune_none().to_dict()
        if config:
            openide_yaml = self.temp_dir / 'openide.yaml'
            openide_yaml.write_text(yaml.dump(config))

            build_data['extra_metadata'][openide_yaml] = 'openide.yaml'

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        import shutil  # noqa: PLC0415

        with contextlib.suppress(Exception):
            shutil.rmtree(self.temp_dir)


@hookimpl
def hatch_register_build_hook() -> type[OpenIDEYAMLBuildHook]:
    return OpenIDEYAMLBuildHook
