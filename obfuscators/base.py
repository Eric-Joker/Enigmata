# Enigmata, an obfuscator for Minecraft Bedrock Editon resource packs.
# Copyright (C) 2024 github.com/Eric-Joker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import logging
import os

import aiofiles

from models import FileHandler
from utils import default_dumps


class OBF:
    def __init__(self, pack_path: str, work_path: str, namespace: str):
        self.logger = logging.getLogger(__name__)
        self.pack_path = pack_path
        self.work_path = work_path
        self.namespace = namespace
        self.processed = {}

    async def async_get_json_data(self, j: FileHandler, output_str: bool = None):
        if j.path in self.processed:
            return default_dumps(self.processed[j.path]) if output_str else self.processed[j.path]
        path = os.path.join(self.work_path if j.processed else self.pack_path, j.path)
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            print(f"An error occurred while loading json ({path}):{e}")
            self.logger.exception(e)
            return "{}"
