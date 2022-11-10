# Copyright 2020 Nafallo Bjälevik <nafallo@ubuntu.com>
#
# user_host_vars.py is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# user_host_vars.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with user_host_vars.py.  If not, see <http://www.gnu.org/licenses/>.
#############################################
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    vars: user_host_vars
    version_added: "2.10"
    short_description: In charge of loading user_vars and host_vars vars for 'localhost'
    requirements:
        - whitelist in configuration
    description:
        - Loads all vars for the corresponding user from the user_vars/ directory and hostname from host_vars/ directory.
        - Files are restricted by extension to one of .yaml, .json, .yml or no extension.
        - Hidden (starting with '.') and backup (ending with '~') files and directories are ignored.
        - Only applies to usernames and hostnames that are existing paths.
    notes:
        - This plugin will only provide the extra variables for the 'localhost' host entity.
        - This plugin will append hostname vars to user vars. We might make this configurable.
    options:
      stage:
        ini:
          - key: stage
            section: vars_user_host_vars
        env:
          - name: ANSIBLE_VARS_PLUGIN_STAGE
      _valid_extensions:
        default: [".yml", ".yaml", ".json"]
        description:
          - "Check all of these extensions when looking for 'variable' files which should be YAML or JSON or vaulted versions of these."
          - 'This affects vars_files, include_vars, inventory and vars plugins among others.'
        env:
          - name: ANSIBLE_YAML_FILENAME_EXT
        ini:
          - section: yaml_valid_extensions
            key: defaults
        type: list
    extends_documentation_fragment:
      - vars_plugin_staging
"""

import os
import socket
from ansible import constants as C
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.plugins.vars import BaseVarsPlugin
from ansible.utils.vars import merge_hash, combine_vars

FOUND = {}


class VarsModule(BaseVarsPlugin):

    REQUIRES_ENABLED = False

    # Get the current user and hostname just once
    user = os.getlogin(), "user_vars"
    host = socket.gethostname(), "host_vars"

    def get_vars(self, loader, path, entities, cache=True):
        if not isinstance(entities, list):
            entities = [entities]

        super(VarsModule, self).get_vars(loader, path, entities)

        data = {}
        for entity in entities:
            if entity.name == "localhost":
                for user_host in [self.user, self.host]:
                    name, subdir = user_host

                    try:
                        found_files = []
                        # load vars
                        b_opath = os.path.realpath(
                            to_bytes(os.path.join(self._basedir, subdir))
                        )
                        opath = to_text(b_opath)
                        key = "%s.%s" % (name, opath)
                        if cache and key in FOUND:
                            found_files = FOUND[key]
                        else:
                            # no need to do much if path does not exist for basedir
                            if os.path.exists(b_opath):
                                if os.path.isdir(b_opath):
                                    self._display.debug("\tprocessir dir %s" % opath)
                                    found_files = loader.find_vars_files(opath, name)
                                    FOUND[key] = found_files
                                else:
                                    self._display.warning(
                                        "Found %s that is not a directory, skipping: %s"
                                        % (subdir, opath)
                                    )

                        for found in found_files:
                            new_data = loader.load_from_file(
                                found, cache=True, unsafe=True
                            )
                            if new_data:  # ignore empty files
                                data = merge_hash(data, new_data, list_merge="append")

                    except Exception as e:
                        raise AnsibleParserError(to_native(e))
        return data
