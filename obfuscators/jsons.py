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
import json
import os
import random
import time
import uuid
from itertools import chain
from typing import Any

import aiofiles
import aioshutil
import regex as re
from wcmatch import glob

from config import cfg
from models import FileHandler, OBFStrType, pbm
from utils import TraverseJson, async_mkdirs, default_dumps, gen_crc

from . import OBF


class Jsons(OBF):
    async def async_obf(self, *args: list[FileHandler]):
        self.comment_pattern = re.compile(r'(?<="[^"]*"):(?=\s*[^",\{\[]|".*?[^"]*")')
        update_pbar = lambda: None if is_merged else pbm.update()

        for j in chain(*args):
            path = os.path.join(self.work_path if j.processed else self.pack_path, j.path)
            new_dir = os.path.dirname(new_path := os.path.join(self.work_path, j.path))
            is_merged = j.path == cfg.merged_ui_path or "MERGED" in OBFStrType.OBFFILE.bi_map.backward.get(
                os.path.splitext(os.path.basename(j.path))[0], ""
            )
            if glob.globmatch(j.path, cfg.exclude_jsons, flags=glob.D | glob.G):
                if not j.processed:
                    await async_mkdirs(new_dir)
                    await aioshutil.copy2(path, new_path)
                pbm.revert_t_item(sum((cfg.comment, cfg.empty_dict, cfg.sort, cfg.unicode)))
            else:
                try:
                    async with aiofiles.open(path, "r", encoding="utf-8") as f:
                        data = await f.read()
                except Exception as e:
                    print(f"An error occurred while loading json ({path}):{e}")
                    self.logger.exception(e)
                    data = "{}"
                if cfg.sort:
                    data = self.sort_json(data)
                    update_pbar()
                if cfg.comment:
                    comments = self.stats_comment(data)
                if cfg.unicode:
                    data = self.custom_json(self.encode_to_unicode(data))
                    update_pbar()
                if not cfg.unformat:
                    data = default_dumps(json.loads(data) if isinstance(data, str) else data, indent=2)
                if cfg.empty_dict:
                    if any(s in str(data) for s in cfg.exclude_entity_names):
                        if not is_merged:
                            pbm.revert_t_item()
                    else:
                        data = (data if isinstance(data, str) else default_dumps(data)) + "{}"
                        update_pbar()
                if cfg.comment:
                    data = self.add_comment(data, comments)
                    update_pbar()
                try:
                    await async_mkdirs(new_dir)
                    async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                        await f.write(data)
                except Exception as e:
                    print(f"An error occurred while writing json ({new_path}):{e}")
                    self.logger.exception(e)

            if not is_merged:
                pbm.update_n_file()
        pbm.pbar.refresh()

    def is_exclude(self, data: str, plus=True):
        return (
            plus
            and data in cfg.exclude_names
            or data.partition("@")[0] in cfg.exclude_jsonui_names
            or any(".".join(data[-len(s.split(".")) :]) == s for s in cfg.exclude_entity_names)
        )

    def encode_to_unicode(self, data):
        def process_dict(data: dict):
            new_dict = {}
            stop = set()

            for k, v in data.items():
                if self.is_exclude(k):
                    stop.add(k)
                    new_dict[k] = v
                elif isinstance(v, dict):
                    if any(self.is_exclude(sk) or (isinstance(sv, str) and self.is_exclude(sv)) for sk, sv in v.items()):
                        stop.add(k)
                        new_dict[k] = v
                    else:
                        new_dict[process_str(k)] = v
                elif isinstance(v, list):
                    if any(isinstance(i, str) and self.is_exclude(i) for i in v):
                        stop.add(k)
                        new_dict[k] = v
                    else:
                        new_dict[process_str(k)] = v
                elif isinstance(v, str) and self.is_exclude(v):
                    stop.add(k)
                    new_dict[k] = v
                else:
                    new_dict[process_str(k)] = v
            return new_dict, stop

        def process_str(data: str, *_):
            return data if data in cfg.exclude_names else "".join([rf"\u{ord(c):04x}" for c in data])

        return TraverseJson(process_dict, str_fun=process_str).traverse(data)

    # Does not allow whitelisted keys and their values to be escaped to unicode.
    # TODO: Multi-level JSON Whitelist Formatting.
    def custom_json(self, data):
        total_items = len(data := data if isinstance(data, dict) else json.loads(data))
        return (
            "{"
            + "".join(
                (
                    default_dumps({k: v}, indent=2)[1:-2].replace(r"\\u", r"\u")
                    if self.is_exclude(k, False)
                    else (default_dumps({k: v}, indent=None if cfg.unformat else 2)[1:-1]).replace(r"\\u", r"\u")
                )
                + ("" if index == total_items - 1 else (",\n" if self.is_exclude(k, False) else ", "))
                for index, (k, v) in enumerate(data.items())
            )
            + "}"
        )

    def sort_json(self, data):
        def process_dict(data: dict[str, Any]):
            sorted_data = {k: v for k, v in sorted(data.items()) if self.is_exclude(k)}
            sorted_data.update({k: v for k, v in sorted(data.items()) if not self.is_exclude(k)})
            return sorted_data, False

        return TraverseJson(process_dict).traverse(data)

    def stats_comment(self, data):
        return [gen_crc(s + self.namespace) for s in self.comment_pattern.split(data)]

    def add_comment(self, data, comments):
        splited = self.comment_pattern.split(data)
        return "".join(
            (
                v
                if i == len(splited) - 1
                else (f"{v}:" if r"\u" not in splited[i] or r"\u" not in splited[i + 1] else f"{v}:/*{comments[i]}*/")
            )
            for i, v in enumerate(splited)
        )

    async def async_manifest(
        self, manifest: FileHandler, pack_name, header_uuid, header_version, modules_uuid, modules_version
    ):
        path = os.path.join(self.pack_path, manifest.path)
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                data = await f.read()
        except Exception as e:
            print(f"An error occurred while loading json ({path}):{e}")
            self.logger.exception(e)
            data = "{}"
        data = json.loads(data)
        if pack_name:
            data["header"]["name"] = pack_name
        gen_uuid = lambda c: c if isinstance(c, str) else str(uuid.UUID(int=rd.getrandbits(128), version=4))
        if header_uuid:
            (rd := random.Random()).seed(self.namespace)
            data["header"]["uuid"] = gen_uuid(header_uuid)
        if header_version:
            data["header"]["version"] = (
                header_version.split(".")
                if isinstance(header_version, str)
                else [int(str(time.time_ns())[:12][i : i + 4]) for i in range(0, 12, 4)]
            )
        (rd := random.Random()).seed(data["header"]["name"])
        for i in data["modules"]:
            if modules_uuid:
                i["uuid"] = gen_uuid(modules_uuid)
            if modules_version:
                num_digits = rd.randint(3, 12)
                random_number = "".join(str(rd.randint(0, 9)) for _ in range(num_digits))
                split_points = sorted(rd.sample(range(1, num_digits), 2))
                i["version"] = (
                    modules_version.split(".")
                    if isinstance(modules_version, str)
                    else [
                        int(random_number[: split_points[0]]),
                        int(random_number[split_points[0] : split_points[1]]),
                        int(random_number[split_points[1] :]),
                    ]
                )
        new_dir = os.path.dirname(new_path := os.path.join(self.work_path, manifest.path))
        data = default_dumps(data, indent=2)
        try:
            await async_mkdirs(new_dir)
            async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                await f.write(data)
        except Exception as e:
            print(f"An error occurred while writing json ({new_path}):{e}")
            self.logger.exception(e)
        pbm.update_n_file()
        pbm.update()
