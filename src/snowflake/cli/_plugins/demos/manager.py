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
import filecmp
import os
import posixpath
import shutil
import tempfile
from datetime import datetime
from os import getenv
from pathlib import Path

import git
from github import Auth, Github
from snowflake.cli._plugins.demos.test_manager import TestManager
from snowflake.cli.api.console import cli_console as cc
from snowflake.cli.api.output.types import MessageResult

DIR_NOTEBOOKS = "notebooks"
DIR_SCRIPTS = "scripts"
MAPPINGS_CSV = "demo-mappings.csv"
SNOWPY_REPO_NAME = "snowflakedb/daniszewski-snowpy"
# SNOWPY_REPO_NAME = "snowflakedb/snowpy"
SNOWPY_REPO = f"git@github.com:{SNOWPY_REPO_NAME}.git"


class DemosManager:
    demos_repo = None
    __demo_mappings_csv = (
        f"libs/snowflake.demos/src/snowflake/demos/resources/{MAPPINGS_CSV}"
    )
    __demos_dir = "libs/snowflake.demos"
    __demos_data_dir = Path(f"{__demos_dir}/src/snowflake/demos/data")

    def __init__(self):
        github = Github(auth=Auth.Token(getenv("GITHUB_TOKEN")))
        self.dir = Path(tempfile.mkdtemp())
        self.snowpy_repo_dir = Path.joinpath(self.dir, "snowpy")
        self.snowpy_libs_demos_dir = Path.joinpath(
            self.snowpy_repo_dir, self.__demos_dir
        )
        self.github_repo = github.get_repo(SNOWPY_REPO_NAME)
        self.demos_repo = self.__clone_repo(SNOWPY_REPO, self.snowpy_repo_dir)
        self.test_manager = TestManager(self.snowpy_libs_demos_dir)

    def sync_demo(self, demo):
        sync_timestamp = self._timestamp()
        repo_name = self.__get_repo_name_from_repo_url(demo.source_repo)
        repo_dir = Path.joinpath(self.dir, repo_name)
        self.__clone_repo(demo.source_repo, repo_dir)

        path_in_repo_abs = (
            Path.joinpath(repo_dir, demo.path_in_source_repo)
            if demo.path_in_source_repo
            else repo_dir
        )

        demos_package_dir = Path.joinpath(self.__demos_data_dir, demo.package_name)
        demos_notebooks_dir = Path.joinpath(demos_package_dir, DIR_NOTEBOOKS)
        demos_scripts_dir = Path.joinpath(demos_package_dir, DIR_SCRIPTS)

        demos_package_abs_dir = Path.joinpath(self.snowpy_repo_dir, demos_package_dir)
        demos_notebooks_abs_dir = Path.joinpath(demos_package_abs_dir, DIR_NOTEBOOKS)
        demos_scripts_abs_dir = Path.joinpath(demos_package_abs_dir, DIR_SCRIPTS)

        repo_notebooks_dir = Path.joinpath(path_in_repo_abs, DIR_NOTEBOOKS)
        repo_scripts_dir = Path.joinpath(path_in_repo_abs, DIR_SCRIPTS)

        self.demos_repo.git.checkout("main")
        with cc.phase(enter_message=f"Synchronizing package `{demo.package_name}`"):
            if not Path.exists(demos_package_abs_dir):
                with cc.phase(enter_message="Package not found in snowpy repo"):
                    branch_name = f"new-notebook-{demo.package_name}_{sync_timestamp}"
                    branch = self.demos_repo.create_head(branch_name)
                    branch.checkout()
                    cc.step(f"Created branch `{branch_name}`")
                    if Path.exists(repo_notebooks_dir):
                        shutil.copytree(repo_notebooks_dir, demos_notebooks_abs_dir)
                        self.demos_repo.git.add(demos_notebooks_dir)
                        cc.step(f"Copied {DIR_NOTEBOOKS} dir")

                    if Path.exists(repo_scripts_dir):
                        shutil.copytree(repo_scripts_dir, demos_scripts_abs_dir)
                        self.demos_repo.git.add(demos_scripts_dir)
                        cc.step(f"Copied {DIR_SCRIPTS} dir")

                    mappings_path = Path.joinpath(
                        self.snowpy_repo_dir, self.__demo_mappings_csv
                    )
                    with open(mappings_path, "a") as fp:
                        fp.write(f"\n{demo.package_name},{demo.human_name},1")
                    self.demos_repo.git.add(mappings_path)
                    cc.step(f"Updated {MAPPINGS_CSV}")
                    self.demos_repo.git.commit(
                        "--no-verify",
                        "-m",
                        f"Adding package `{demo.package_name}` for `{demo.human_name}`.",
                    )
                    cc.step(f"Commit created")
                    self.demos_repo.git.push("origin", "-u", branch_name)
                    cc.step(f"Branch pushed")
                    pr_handle = self.__create_pr(
                        branch_name, f"Add notebook `{demo.human_name}`"
                    )
                    cc.step(f"Created PR#{pr_handle.number}: {pr_handle.html_url}")
                    self.test_manager.run_tests_for_demo(demo, pr_handle)

            else:
                with cc.phase(
                    enter_message=f"Package `{demo.package_name}` exists in snowpy repo, syncing"
                ):
                    changed_files = []

                    for f in os.listdir(repo_notebooks_dir):
                        cur = Path.joinpath(repo_notebooks_dir, f)
                        expected_rel_path_in_demos = Path.joinpath(
                            self.__demos_data_dir, demo.package_name, "notebooks", f
                        )
                        expected_abs_path_in_demos = Path.joinpath(
                            self.snowpy_repo_dir, expected_rel_path_in_demos
                        )
                        comparison = filecmp.cmp(expected_abs_path_in_demos, cur)

                        if not comparison:
                            changed_files.append(
                                (
                                    cur,
                                    expected_rel_path_in_demos,
                                    expected_abs_path_in_demos,
                                )
                            )

                    if changed_files:
                        cc.step(
                            f"There are {len(changed_files)} differences in demo {demo.package_name}"
                        )
                        with cc.phase(enter_message="Updating"):
                            branch_name = (
                                f"update-notebook-{demo.package_name}_{sync_timestamp}"
                            )
                            branch = self.demos_repo.create_head(branch_name)
                            branch.checkout()
                            cc.step(f"Created branch `{branch_name}`")

                            for (
                                cur,
                                expected_rel_path_in_demos,
                                expected_abs_path_in_demos,
                            ) in changed_files:
                                shutil.copy(cur, expected_abs_path_in_demos)
                                self.demos_repo.git.add(expected_rel_path_in_demos)
                                cc.step(f"Added `{expected_rel_path_in_demos}`")

                            self.demos_repo.git.commit(
                                "--no-verify",
                                "-m",
                                f"Updating package {demo.package_name}.",
                            )
                            cc.step(f"Commit created")
                            self.demos_repo.git.push("origin", "-u", branch_name)
                            pr_handle = self.__create_pr(
                                branch_name, f"Update notebook `{demo.human_name}`"
                            )
                            self.test_manager.run_tests_for_demo(demo, pr_handle)

                    else:
                        cc.step(
                            f"No differences in demo {demo.package_name}. Carry on."
                        )

        return MessageResult("done")

    @staticmethod
    def _timestamp():
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def __get_repo_name_from_repo_url(repo_url):
        repo_name = posixpath.splitext(posixpath.split(repo_url)[1])[0]
        return repo_name

    @staticmethod
    def __clone_repo(repo_link, target_directory) -> git.Repo:
        git.Repo.clone_from(repo_link, target_directory)
        repo = git.Repo(target_directory)
        return repo

    def __create_pr(self, branch_name, pr_title):
        with open(
            Path.joinpath(self.snowpy_repo_dir, ".github", "pull_request_template.md"),
            "r",
        ) as fp:
            body = fp.read()
        return self.github_repo.create_pull(
            base="main", head=branch_name, title=pr_title, body=body, draft=True
        )
