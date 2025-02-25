# Copyright (c) 2024 Snowflake Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import logging

import click
import yaml
from snowflake.cli._plugins.demos.manager import DemosManager
from snowflake.cli._plugins.demos.types import Demo
from snowflake.cli.api.commands.snow_typer import SnowTyperFactory
from snowflake.cli.api.console import cli_console as cc
from snowflake.cli.api.output.types import CommandResult, MessageResult

app = SnowTyperFactory(
    name="demos",
    help="Helps to keep demos in DemosAPI in sync.",
)
log = logging.getLogger(__name__)

manager = DemosManager()


@app.command("sync_demo", requires_connection=True)
def sync_demo(yml_file_path, **options) -> CommandResult:
    """
    Adds new demo by source repository.
    """
    with cc.phase(
        enter_message="About to add following following repo...",
        exit_message="",
    ):
        with open(yml_file_path, "r") as fp:
            d: Demo = Demo.from_dict(yaml.safe_load(fp))
        cc.step(f"Human name:\t{d.human_name}")
        cc.step(f"Package name:\t{d.package_name}")
        cc.step(f"Repo URL:\t{d.source_repo}")
        cc.step(f"Path in repo:\t{d.path_in_source_repo}")

    if click.confirm("Do you wan to continue?"):
        return manager.sync_demo(d)
    return MessageResult("Aborted")
