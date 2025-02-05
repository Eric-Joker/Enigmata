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
import os
import random
from functools import partial
from itertools import chain

import aiofiles
import aioshutil
import regex as re
from PIL import PngImagePlugin

from config import cfg
from models import FileHandler, OBFStrType, pbm
from utils import async_mkdirs, async_pil_dump, async_pil_load, gen_obfstr

from . import OBF


class Images(OBF):
    async def async_rename(
        self,
        pngs: list[FileHandler],
        tgas: list[FileHandler],
        renames: list[FileHandler],
        obf_names: list[FileHandler],
        texture_jsons: list[FileHandler],
        texture_jsons_2: list[FileHandler],
        image_jsons: list[FileHandler],
    ):
        self.pngs = pngs
        self.tgas = tgas

        for file, need_obf in chain(((x, False) for x in renames), ((x, True) for x in obf_names)):
            name, ext = os.path.splitext(os.path.basename(file.path))
            if name in cfg.exclude_image_names:
                new_dir = os.path.join(self.work_path, os.path.dirname(file.path))
                new_path = os.path.join(self.work_path, file.path)
                pbm.revert_t_item()
            else:
                # If the filenames of the subpack are different from those of the main pack, it will lead to a decrease in resource pack performance.
                (rd := random.Random()).seed(
                    file.path
                    if await self._async_check_sub_ref(file, texture_jsons_2 if need_obf else texture_jsons)
                    else file.cut
                )
                if need_obf:
                    new_name = gen_obfstr(name, OBFStrType.OBFFILE) + ext
                else:
                    # insert string
                    len1 = len(self.namespace)
                    if (len2 := len(name)) == 1:
                        insert_position = rd.randint(0, len1)
                        return self.namespace[:insert_position] + name + self.namespace[insert_position:]
                    insert_positions = sorted(rd.sample(range(len1 + len2), len1))
                    result, char1_index, char2_index = [], 0, 0
                    for i in range(len1 + len2):
                        if char1_index < len1 and i == insert_positions[char1_index]:
                            result.append(self.namespace[char1_index])
                            char1_index += 1
                        else:
                            result.append(name[char2_index])
                            char2_index += 1
                    new_name = "".join(result) + ext
                new_path = os.path.join(new_dir := os.path.join(self.work_path, os.path.dirname(file.path)), new_name)
                OBFStrType.FILENAME.bi_map[file.path.replace("\\", "/")] = os.path.join(
                    os.path.dirname(file.path), new_name
                ).replace("\\", "/")
                pbm.update()

            old_path = os.path.join(self.pack_path, file.path)
            try:
                await async_mkdirs(new_dir)
                await aioshutil.copy2(old_path, new_path)
            except Exception as e:
                print(f"An error occurred while rename image ({new_path}):{e}")
                self.logger.exception(e)
            if ext == ".png":
                self.pngs.append(FileHandler(new_path, processed=True))
            else:
                self.tgas.append(FileHandler(new_path, processed=True))

        # rename the JSON files to match the names of the image files.
        for j in image_jsons:
            if os.path.splitext(os.path.basename(j.path))[0] in cfg.exclude_image_names:
                pbm.revert_t_item()
            else:
                new_dir = os.path.join(self.work_path, (rel_dir := os.path.dirname(j.path)))
                path = os.path.splitext(j.path)[0].replace("\\", "/")
                new_name = os.path.splitext(
                    os.path.basename(
                        OBFStrType.FILENAME.bi_map.get(f"{path}.png") or OBFStrType.FILENAME.bi_map.get(f"{path}.tga")
                    )
                )[0]
                new_path = os.path.join(new_dir, f"{new_name}.json")
                old_path = os.path.join(self.pack_path, j.path)
                try:
                    await async_mkdirs(new_dir)
                    await aioshutil.copy2(old_path, new_path)
                except Exception as e:
                    print(f"An error occurred while rename json ({new_path}):{e}")
                    self.logger.exception(e)

                j.path = os.path.join(rel_dir, f"{new_name}.json")
                j.processed = True
                pbm.update()

        # fix jsons
        def repl(match: re.Match, subp):
            if os.path.splitext(path := os.path.join(subp, (data := match.group(0))).replace("\\", "/"))[1] == "":
                for ext in [".png", ".tga"]:
                    spliced_path = path + ext
                    if spliced_path in OBFStrType.FILENAME.bi_map:  # returns False when carrying subpack.
                        return os.path.relpath(OBFStrType.FILENAME.bi_map[spliced_path], subp).replace("\\", "/")[: -len(ext)]
                    elif (spliced_data := data + ext) in OBFStrType.FILENAME.bi_map:
                        return OBFStrType.FILENAME.bi_map[spliced_data][: -len(ext)]
                return data
            elif path in OBFStrType.FILENAME.bi_map:
                return os.path.relpath(OBFStrType.FILENAME.bi_map[path], subp).replace("\\", "/")[
                    : -len(os.path.splitext(path)[1])
                ]
            elif data in OBFStrType.FILENAME.bi_map:
                return OBFStrType.FILENAME.bi_map[data][: -len(os.path.splitext(data)[1])]
            return data

        subp_pattern = re.compile(r"[/\\]?(subpacks[/\\].+?)[/\\]")
        value_pattern = re.compile(r'(?<=(?<!//.*|/\*[\s\S]*(?!\*/))(?::|,|\[)(?:\s*/\*[\s\S]*\*/)*\s*(?<!//.*)").*?(?=")')
        for file in texture_jsons + texture_jsons_2:
            path = os.path.join(self.pack_path, file.path)
            try:
                async with aiofiles.open(path, "r", encoding="utf-8") as f:
                    data = await f.read()
            except Exception as e:
                print(f"An error occurred while loading json ({path}):{e}")
                self.logger.exception(e)
                data = ""
            search = subp_pattern.search(file.path)
            data = value_pattern.sub(partial(repl, subp=search.group(1) if search else ""), data)
            new_dir = os.path.dirname(new_path := os.path.join(self.work_path, file.path))
            try:
                await async_mkdirs(new_dir)
                async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                    await f.write(data)
            except Exception as e:
                print(f"An error occurred while writing json ({new_path}):{e}")
                self.logger.exception(e)

            file.processed = True
            pbm.update()

    async def async_obf(self):
        await asyncio.gather(self.async_png(), self.async_tga())

    async def async_process_channel(self, path):
        img = await async_pil_load(path if os.path.isabs(path) else os.path.join(self.pack_path, path))
        if img.mode == "RGBA" and cfg.image_compress == 9 and img.getextrema()[3] == (255, 255):
            return img.convert("RGB")
        return img

    async def async_png(self):
        for i in self.pngs:
            (metadata := PngImagePlugin.PngInfo()).add_text(self.namespace, "")
            await async_pil_dump(
                os.path.join(self.work_path, i.path),
                await self.async_process_channel(i.path),
                "PNG",
                compress_level=6 if cfg.image_compress == -1 else cfg.image_compress,
                optimize=cfg.image_compress == 9,
                pnginfo=metadata if cfg.extrainfo else None,
            )

            pbm.update_n_file()
            pbm.update(sum((cfg.image_compress != -1, cfg.extrainfo)))

    async def async_tga(self):
        for i in self.tgas:
            compressing = cfg.image_compress > 6
            await async_pil_dump(
                os.path.join(self.work_path, i.path),
                await self.async_process_channel(i.path),
                "TGA",
                compression="tga_rle" if compressing else "",
                id_section=self.namespace.encode("utf-8") if cfg.extrainfo else b"",
            )

            pbm.update_n_file()
            pbm.update(sum((cfg.image_compress > 6, cfg.extrainfo)))

    async def _async_check_sub_ref(self, item: FileHandler, jsons: list[FileHandler]):
        for i in jsons:
            if item.subpack_path and item.subpack_path in i.path:
                real_path = os.path.join(self.pack_path, i.path)
                try:
                    async with aiofiles.open(real_path, "r", encoding="utf-8") as f:
                        data = await f.read()
                except Exception as e:
                    print(f"An error occurred while check file data ({real_path}):{e}")
                    self.logger.exception(e)
                if item.cut in data:
                    return True
