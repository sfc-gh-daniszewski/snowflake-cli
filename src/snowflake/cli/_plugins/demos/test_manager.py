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

import subprocess

from snowflake.cli.api.console import cli_console as cc


class TestManager:
    def __init__(self, snowpy_libs_demos_dir):
        self.snowpy_libs_demos_dir = snowpy_libs_demos_dir

    def run_tests_for_demo(self, demo, pr_handle):
        with cc.phase(enter_message="Running tests", exit_message="Finished"):
            self.__run_precommit(pr_handle)
            self.__run_regular_tests(pr_handle)
            self.__test_help(demo, pr_handle)
            self.__test_load_demo(demo, pr_handle)

    def __test_help(self, demo, pr_handle):
        output = self.__get_cmd_output("hatch run e2e:help")
        comment_body = f"""
    This is automated comment.


    Below is output of `help()` method.
    Expect to see:
    * demo name: `{demo.package_name}`
    * title: `{demo.human_name}`

    ```
    {output}
    ```
    """
        c = pr_handle.create_issue_comment(comment_body)
        cc.step(f"Created comment #{c.id}: {c.html_url}")

    def __run_precommit(self, pr_handle):
        output = self.__get_cmd_output("hatch run precommit:check")
        comment_body = f"""
    This is automated comment.


    Below is output of `hatch run precommit:check` method.
    ```
    {output}
    ```
    """
        c = pr_handle.create_issue_comment(comment_body)
        cc.step(f"Created comment #{c.id}: {c.html_url}")

    def __run_regular_tests(self, pr_handle):
        output = self.__get_cmd_output("hatch run test:check")
        comment_body = f"""
    This is automated comment.


    Below is output of `hatch run test:check` method.
    ```
    {output}
    ```
    """
        c = pr_handle.create_issue_comment(comment_body)
        cc.step(f"Created comment #{c.id}: {c.html_url}")

    def __test_load_demo(self, demo, pr_handle):
        output = self.__get_cmd_output(f"hatch run e2e:load_demo {demo.package_name}")
        comment_body = f"""
    This is automated comment.


    Below is output of `load_demo("{demo.package_name}")` method.

    ```
    {output}
    ```
    """
        c = pr_handle.create_issue_comment(comment_body)
        cc.step(f"Created comment #{c.id}: {c.html_url}")

    def __get_cmd_output(self, cmd):
        cc.step(f"Running {cmd}")
        try:
            output = subprocess.check_output(
                cmd, shell=True, stderr=subprocess.PIPE, cwd=self.snowpy_libs_demos_dir
            )
        except subprocess.CalledProcessError as ex:
            output = ex.output
        return output.decode("utf-8")
