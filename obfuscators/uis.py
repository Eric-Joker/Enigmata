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
import asyncio
import json
import os
from functools import partial

import aiofiles
import aiofiles.os as aioos
import aioshutil
import regex as re

from config import cfg
from models import FileHandler, OBFStrType, pbm, vd
from utils import (
    TraverseControls,
    TraverseJson,
    async_mkdirs,
    comment_pattern,
    default_dumps,
    gen_obfstr,
    l10n_pattern,
    uivar_pattern,
)

from . import OBF


class UIs(OBF):
    async def async_obf(
        self,
        jsonuis: list[FileHandler],
        uniqueuis: list[FileHandler],
        langs: list[FileHandler],
        ui_global_vars: list[FileHandler],
        ui_defs: list[FileHandler],
    ):
        self.jsonuis = jsonuis
        self.uniqueuis = uniqueuis
        self.langs = langs
        self.global_vars = ui_global_vars
        self.ui_defs = ui_defs

        self.processed = {}
        self.uniqueui_namespace = []
        self.variable_pattern = re.compile(r"([\$#].*?)(?=([@\|\)\s]|$))")

        if cfg.obfuscate_jsonui:
            stats_g_var_task = asyncio.create_task(self.async_stats_global_var())
        process_l10n_task = asyncio.create_task(self.async_process_l10n())
        if cfg.obfuscate_jsonui or cfg.merged_ui_path:
            await self.async_merge()
        if cfg.obfuscate_jsonui:
            await process_l10n_task
            await self.async_fix_l10n()
            await stats_g_var_task
            await self.async_obf_variable()
            await self.async_obf_ctrl_name()

        for k, v in self.processed.items():
            if k == "MERGED":
                uniqueuis.append(FileHandler(cfg.merged_ui_path, processed=True))

            new_path = os.path.join(self.work_path, cfg.merged_ui_path if k == "MERGED" else k)
            new_dir = os.path.dirname(new_path)
            data = v if isinstance(v, str) else json.dumps(v)
            try:
                await async_mkdirs(new_dir)
                async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                    await f.write(data)
            except Exception as e:
                print(f"An error occurred while writing json ({new_path}):{e}")
                self.logger.exception(e)

    async def async_merge(self):
        control_split_pattern = re.compile(r"[@\.]")
        exclude_namespace = set()

        def stats_ctrl_name(data: dict, renamed: list):
            if (ns := data.get("namespace")) not in exclude_namespace:
                self.uniqueui_namespace.append(ns)

                new_dict = {"namespace": self.namespace}
                for k, v in data.items():
                    if k != "namespace":
                        renamed.append((splited := k.partition("@"))[0])
                        new_ctrl_name = f"{self.uniqueui_namespace[-1]}_{splited[0]}"
                        OBFStrType.UIMERGE.bi_map[f"{self.uniqueui_namespace[-1]}.{splited[0]}"] = new_ctrl_name
                        new_dict[f"{new_ctrl_name}{"".join(splited[1:])}"] = v
            return new_dict, True

        def fix_self_namespace_dict(data: dict, is_control: bool, renamed: list):
            if (ns := data.get("namespace")) and ns in exclude_namespace:
                return {}, True
            return {fix_self_namespace_str(k, renamed=renamed) if is_control else k: v for k, v in data.items()}, False

        def fix_self_namespace_str(data: str, *_, renamed: list):
            data = data.replace(f"{self.uniqueui_namespace[-1]}.", f"{self.namespace}.")
            for control_name in renamed:
                # Modify the namespace of all controls that inherit from first-level controls and have not been renamed. like "a@b.a"
                cache_data = re.sub(
                    rf"(^{control_name}@({self.namespace}\.)?){control_name}$",
                    rf"{self.uniqueui_namespace[-1]}_\1{self.uniqueui_namespace[-1]}_{control_name}",
                    data,
                )
                if cache_data == data:
                    # Modify the namespace of all controls that inherit from first-level controls and have been renamed. like "a@b.c"
                    cache_data = re.sub(
                        rf"(^|@|(^|@){self.namespace}\.){control_name}$",
                        rf"\1{self.uniqueui_namespace[-1]}_{control_name}",
                        data,
                    )
                    if cache_data != data:
                        return cache_data
                else:
                    return cache_data
            return data

        def fix_all_namespace_str(data: str, *_, namespace: str):
            lens = len(splited := control_split_pattern.split(data))
            if (three := lens == 3) and namespace == splited[1] or lens == 2 and namespace == splited[0]:
                data = (f"{namespace}_{data}" if three and splited[0] == splited[2] else data).replace(
                    f"{namespace}.", f"{self.namespace}.{namespace}_"
                )
                OBFStrType.UIMERGE.bi_map.replace_value(
                    (o_str := ".".join(splited[-2:])), o_str.replace(f"{namespace}.", f"{namespace}_")
                )
            return data

        # TODO: Since I don’t need it, the functionality of exclude all unique JsonUIs with the same name as those in the subpack has not been tested.
        for j in self.uniqueuis:
            if j.subpack_path:
                data = self.processed[j.path] = await self.async_get_json_data(j)
                ns = (json.loads(comment_pattern.sub("", data)) if isinstance(data, str) else data)["namespace"]
                self.uniqueui_namespace.append(ns)
                exclude_namespace.add(ns)

        # start merge
        merged_dict = {"namespace": self.namespace}
        exclude_files = set()
        for j in self.uniqueuis.copy():
            renamed_controls = []
            data = TraverseJson(partial(stats_ctrl_name, renamed=renamed_controls)).traverse(
                await self.async_get_json_data(j), True
            )
            is_exclude = True
            if cfg.merged_ui_path:
                if not j.subpack_path and (
                    # fix its own namespace
                    new_dict := (
                        TraverseControls(
                            partial(fix_self_namespace_dict, renamed=renamed_controls),
                            str_fun=partial(fix_self_namespace_str, renamed=renamed_controls),
                        ).traverse(data, exclude=False)
                    )
                ):
                    merged_dict.update(new_dict)

                    if j.processed:
                        await aioos.remove(os.path.join(self.work_path, j.path))
                    self.processed["MERGED"] = merged_dict

                    self.uniqueuis.remove(j)
                    pbm.revert_t_item(sum((cfg.comment, cfg.empty_dict, cfg.sort, cfg.unicode, cfg.obfuscate_jsonui)))
                    pbm.update_n_file()
                    pbm.update()
                    is_exclude = False
                else:
                    pbm.revert_t_item()

            # TODO: NOT TESTED
            # obfuscate the filenames of files that cannot be merged
            if cfg.obfuscate_jsonui and is_exclude:
                new_name = gen_obfstr((splited := os.path.basename(j.cut).partition("."))[0], OBFStrType.OBFFILE) + splited[2]
                # new_name = (gen_obfstr((splited := os.path.basename(j.cut).partition("."))[0], OBFStrType.OBFFILE, 1) + splited[2])
                new_path = os.path.join(new_dir := os.path.join(self.work_path, (rel_dir := os.path.dirname(j.path))), new_name)
                old_path = os.path.join(self.pack_path, j.path)
                try:
                    await async_mkdirs(new_dir)
                    await aioshutil.copy2(old_path, new_path)
                except Exception as e:
                    print(f"An error occurred while write json ({new_path}):{e}")
                    self.logger.exception(e)

                exclude_files.add(j.cut)
                j.path = os.path.join(rel_dir, new_name)
                j.processed = True

        if not cfg.merged_ui_path:
            return

        # Fix all namespaces for each JsonUI.
        for ns in self.uniqueui_namespace:
            if ns not in exclude_namespace:
                instance = TraverseControls(
                    lambda data, *_: ({fix_all_namespace_str(k, namespace=ns): v for k, v in data.items()}, False),
                    str_fun=partial(fix_all_namespace_str, namespace=ns),
                )
                self.processed["MERGED"] = instance.traverse(self.processed["MERGED"], exclude=False)

                for j in self.jsonuis:
                    self.processed[j.path] = instance.traverse(await self.async_get_json_data(j), True, False)

                    j.processed = True
        pbm.update(len(self.jsonuis))

        # process _ui_def.json
        try:
            cfg.defs_confused = json.loads(cfg.defs_confused) if cfg.defs_confused else {}
            if not isinstance(cfg.defs_confused, dict):
                raise
        except Exception:
            cfg.defs_confused = {}
            self.logger.error("defs_confused must be a JSON dictionary string or an empty string.")
        for j in self.ui_defs:
            new_path = os.path.join(self.pack_path, j.path)
            try:
                async with aiofiles.open(new_path, "r", encoding="utf-8") as f:
                    data = await f.read()
                data: dict = json.loads(data)
            except Exception as e:
                print(f"An error occurred while reading json ({new_path}):{e}")
                self.logger.exception(e)
                data = {}
            unique_cuts = {os.path.splitext(c.cut)[0] for c in self.uniqueuis}
            (
                data := {
                    k: (
                        # TODO: NOT TESTED
                        [
                            gen_obfstr(i, OBFStrType.OBFFILE) if i in exclude_files else i
                            for i in data["ui_defs"]
                            if os.path.splitext(i)[0] not in unique_cuts
                        ]
                        + [cfg.merged_ui_path]
                        if k == "ui_defs"
                        else v
                    )
                    for k, v in data.items()
                }
            ).update(cfg.defs_confused)
            data = default_dumps(data)
            new_dir = os.path.dirname(new_path := os.path.join(self.work_path, j.path))
            try:
                await async_mkdirs(new_dir)
                async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                    await f.write(data)
            except Exception as e:
                print(f"An error occurred while writing json ({new_path}):{e}")
                self.logger.exception(e)

            j.processed = True
            pbm.update()

    async def async_obf_ctrl_name(self):
        def stats_ctrl_dict(data: dict, is_control: bool, is_unique=False):
            if not is_control:
                return data, False

            return {
                (
                    k
                    if "$" in (splited := k.partition("@"))[0]
                    or "#" in splited[0]
                    or splited[0].isdigit()
                    or splited[0] in vd.ui_keywords
                    else (
                        f"{gen_obfstr(splited[0], OBFStrType.UICONTROL)}@{splited[2]}"
                        if "@" in k and (self.namespace in k or is_unique)
                        else gen_obfstr(splited[0], OBFStrType.UICONTROL) if "@" not in k and is_unique else k
                    )
                ): v
                for k, v in data.items()
            }, False

        def process_dict(data: dict, is_control: bool, is_unique=False):
            if not is_control:
                return data, vd.ui_properties

            new_dict = {}
            for k, v in data.items():
                new_key = k
                for ns in [self.namespace] if cfg.merged_ui_path else self.uniqueui_namespace:
                    if f"@{ns}." in k and (o_key := (splited := k.partition(f"@{ns}."))[2]) in OBFStrType.UICONTROL.bi_map:
                        new_key = f"{splited[0]}@{ns}.{OBFStrType.UICONTROL.bi_map[o_key]}"
                        break
                    elif "@" in k and is_unique and (o_key := (splited := k.partition("@"))[2]) in OBFStrType.UICONTROL.bi_map:
                        new_key = f"{splited[0]}@{OBFStrType.UICONTROL.bi_map[o_key]}"
                        break
                new_dict[new_key] = v
            return new_dict, vd.ui_properties

        def process_str(data: str, *_, is_unique=False):
            for o_key, n_key in OBFStrType.UICONTROL.bi_map.items():
                for ns in [self.namespace] if cfg.merged_ui_path else self.uniqueui_namespace:
                    if o_key in data:
                        new_data = data
                        if f"@{ns}." in data:
                            new_data = re.sub(f"^(.*?)@{ns}.{o_key}$", rf"\1@{ns}.{n_key}", data)
                        elif "@" in data and is_unique:
                            new_data = re.sub(f"^@{o_key}$", f"@{n_key}", data)
                        elif f"{ns}." in data:
                            new_data = re.sub(f"^{ns}.{o_key}$", f"{ns}.{n_key}", data)
                        elif is_unique:
                            new_data = re.sub(f"^{o_key}$", n_key, data)
                        if data != new_data:
                            return new_data
            return data

        stats = TraverseControls(partial(stats_ctrl_dict, is_unique=True))
        process = TraverseControls(partial(process_dict, is_unique=True), str_fun=partial(process_str, is_unique=True))
        if cfg.merged_ui_path:
            self.processed["MERGED"] = process.traverse(stats.traverse(self.processed["MERGED"]), exclude=False)
        for j in self.uniqueuis:
            self.processed[j.path] = stats.traverse(await self.async_get_json_data(j))
        for j in self.uniqueuis:
            self.processed[j.path] = process.traverse(self.processed[j.path], exclude=False)
        for j in self.jsonuis:
            self.processed[j.path] = TraverseControls(stats_ctrl_dict).traverse(  # process sub controls
                TraverseControls(process_dict, str_fun=process_str).traverse(await self.async_get_json_data(j), exclude=False)
            )

    async def async_stats_global_var(self):
        for j in self.global_vars:
            path = os.path.join(self.pack_path, j.path)
            try:
                async with aiofiles.open(path, "r", encoding="utf-8") as f:
                    data = await f.read()
            except Exception as e:
                print(f"An error occurred while loading json ({path}):{e}")
                self.logger.exception(e)
                data = "{}"
            vd.ui_variables.update(iter(uivar_pattern.findall(data)))

    async def async_obf_variable(self):
        def process_dict(data: dict, *_, is_unique=False):
            return {process_str(k, is_unique=is_unique): v for k, v in data.items()}, False

        def process_str(data: str, *_, is_unique=False):
            def repl(m: re.Match):
                if (var := m.group(1)) in vd.ui_variables or var in vd.ui_bindings:
                    return var

                is_var = var[0] == "$"
                return ("$" if is_var else "#") + (
                    gen_obfstr(var[1:], OBFStrType.UIVARIABLE if is_var else OBFStrType.UIBINDIND)
                    if is_unique
                    else (OBFStrType.UIVARIABLE if is_var else OBFStrType.UIBINDIND).bi_map.get(var[1:], var[1:])
                )

            return self.variable_pattern.sub(repl, data)

        process = TraverseControls(partial(process_dict, is_unique=True), str_fun=partial(process_str, is_unique=True))
        if cfg.merged_ui_path:
            self.processed["MERGED"] = process.traverse(self.processed["MERGED"])
        for j in self.uniqueuis:
            self.processed[j.path] = process.traverse(await self.async_get_json_data(j))
        for j in self.jsonuis:
            self.processed[j.path] = TraverseControls(process_dict, str_fun=process_str).traverse(
                await self.async_get_json_data(j), exclude=False
            )

    async def async_process_l10n(self):
        def repl(m: re.Match):
            return l10n if (l10n := m.group(1)) in vd.l10n else gen_obfstr(l10n, OBFStrType.LOCALIZATION)

        for l in self.langs:
            path = os.path.join(self.pack_path, l.path)
            try:
                async with aiofiles.open(path, "r", encoding="utf-8") as f:
                    data = await f.read()
            except Exception as e:
                print(f"An error occurred while loading lang ({path}):{e}")
                self.logger.exception(e)
                data = "{}"
            if cfg.obfuscate_jsonui:
                data = l10n_pattern.sub(repl, data)
                pbm.update_n_file()
                pbm.update()
            new_dir = os.path.dirname(new_path := os.path.join(self.work_path, l.path))
            try:
                await async_mkdirs(new_dir)
                async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                    await f.write(data)
            except Exception as e:
                print(f"An error occurred while writing lang ({new_path}):{e}")
                self.logger.exception(e)
            l.processed = True

    async def async_fix_l10n(self):
        def process_dict(data: dict, *_):
            return data, {k for k, v in data.items() if isinstance(v, str)} if data.get("localize") == False else False

        def process_str(data: str, *_):
            return OBFStrType.LOCALIZATION.bi_map.get(data, data)

        process = TraverseControls(process_dict, str_fun=process_str)
        if cfg.merged_ui_path:
            self.processed["MERGED"] = process.traverse(self.processed.get("MERGED", {}), exclude=False)
        for j in self.uniqueuis:
            self.processed[j.path] = process.traverse(await self.async_get_json_data(j), exclude=False)
            j.processed = True
            pbm.update()
        for j in self.jsonuis:
            self.processed[j.path] = process.traverse(await self.async_get_json_data(j), exclude=False)
            j.processed = True
            pbm.update()
