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


class Demo:
    package_name: str
    human_name: str
    source_repo: str
    path_in_source_repo: str

    @staticmethod
    def from_dict(data):
        d = Demo()
        d.package_name = data["package_name"]
        d.human_name = data["human_name"]
        d.source_repo = data["source_repo"]
        d.path_in_source_repo = data["path_in_source_repo"] or None
        return d
