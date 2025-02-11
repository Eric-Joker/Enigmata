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
import itertools
import logging
import os
import shutil
import time
import zipfile

import aiofiles
from tqdm import tqdm
from wcmatch import glob

import obfuscators as obfs
from config.base import EnigmataConfig
from models import FileHandler, OBFStrType, obf_strs_dict, pbm, vd
from utils import default_dumps, default_write, mkdirs

__VERSION__ = "0.1.0"


def print_banner():
    print(
        rf"""----------Enigmata - MCBERP obfuscation Toolkit----------
 _____       _                        _       
|____ | __ _(_)_ __   ___ __ _ _ __ _| |_ __  
  |_  |/ _` | | '_ \ / _ ' _` | '_ |__ | '_ \ 
 ___| | | | | | |_) | | | | | | |_) _| | |_) |
|_____|_| |_|_| .__/|_| |_| |_|_.__|__/|_.__/ 
               \___|                            V{__VERSION__}
MCBE资源包混淆工具 - An obfuscator for Minecraft Bedrock Editon resource packs.
This project is under the GPL-3.0 license. By Eric_J0ker.
Source code: https://github.com/Eric-Joker/Enigmata, 
License: https://github.com/Eric-Joker/Enigmata?tab=GPL-3.0-1-ov-file

# 📄Note:
We do not want this script to be used too frequently, as it goes against the spirit of collaboration and sharing within the community. If you are willing to contribute to the community, please do not release only obfuscated resource packs.
"""
    )


logger = logging.getLogger(__name__)


def main():
    print_banner()
    from config import cfg

    if os.path.isdir(cfg.work_path):
        cfg.work_path = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), cfg.work_path))
    else:
        raise ValueError("Cannot read the work directory.")
    if not cfg.path:
        raise ValueError("At least one path to the obfuscated resource package must be specified")
    if cfg.zip_name and len(cfg.zip_name) != len(cfg.path):
        raise ValueError("The zip file name needs to correspond to the resource package.")

    if (
        (
            cfg.merged_ui_path
            or cfg.merge_entity
            or cfg.obfuscate_jsonui
            or cfg.obfuscate_entity
            or cfg.watermark_paths
            or cfg.extrainfo
            or cfg.header_uuid
        )
        and not cfg.namespace
        or (len(cfg.namespace) if isinstance(cfg.namespace, list) else 1)
        != (len(cfg.path) if isinstance(cfg.path, list) else 1)
    ):
        raise ValueError("The namespace needs to correspond to the resource package.")
    if (cfg.obfuscate_jsonui or cfg.obfuscate_entity):
        if len(cfg.obfuscate_strs) < 1:
            raise ValueError("At least one set of obfuscated strings.")
        if not any(any(s.isascii() for s in p) for p in cfg.obfuscate_strs):
            raise ValueError("No ASCII characters present in obfuscate_strs.")
        if any(any(not s.isascii() for s in p) for p in cfg.obfuscate_ascll):
            raise ValueError("obfuscate_ascll must be full of ascll characters.")

    try:
        asyncio.run(async_start_obf(cfg))
    except Exception as e:
        logger.exception(e)
    finally:
        if cfg.tmp_dir in cfg.data_path:
            input("Press any key to clean up temp files and exit.")
            shutil.rmtree(cfg.data_path)


async def async_start_obf(cfg: EnigmataConfig):
    for (
        root_path,
        namespace,
        zip_name,
        pack_name,
        header_uuid,
        header_version,
        modules_uuid,
        modules_version,
    ) in itertools.zip_longest(
        cfg.path,
        cfg.namespace,
        cfg.zip_name,
        cfg.pack_name,
        cfg.header_uuid,
        cfg.header_version,
        cfg.modules_uuid,
        cfg.modules_version,
        fillvalue=None,
    ):
        manifest = None
        pngs = []
        tgas = []
        renames = []
        obf_names = []
        jsonuis = []
        langs = []
        uniqueuis = []
        acs = []
        animations = []
        entities = []
        models = []
        particles = []
        rcs = []
        materials = []
        material_indexes = []
        std_jsons = []
        texture_jsons = []
        texture_jsons_2 = []
        image_jsons = []
        ui_global_vars = []
        ui_defs = []
        mkdirs(work_path := os.path.join(cfg.work_path, namespace + time.strftime("_%Y-%m-%d-%H-%M-%S")))
        pbm.pbar = tqdm(
            total=0,
            nrows=0,
            disable=not cfg.console,
            unit="items",
            desc=f"{namespace} Statisticing: ",
            bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}{unit} {elapsed}",
        )

        def process_image(fh: FileHandler, vd: set, l: list):
            splited = fh.path.split(os.sep)
            if fh.path.replace("\\", "/") not in vd and (
                not (insub := "subpacks" in fh.path) or (cut := "/".join(splited[2:])) not in vd
            ):
                fh.subpack_path = os.sep.join(splited[:2]) if insub else ""
                fh.cut = os.path.splitext(cut)[0] if insub else fh.path
                if glob.globmatch(fh.path, cfg.watermark_paths, flags=glob.D | glob.G | glob.N):
                    renames.append(fh)
                    pbm.update_t_item()
                    return
                elif glob.globmatch(fh.path, cfg.obfuscate_paths, flags=glob.D | glob.G | glob.N):
                    obf_names.append(fh)
                    pbm.update_t_item()
                    return
            if cfg.image_compress != -1 or cfg.extrainfo:
                l.append(fh)

        for root, _, files in os.walk(root_path):
            for file in files:
                rel_path = os.path.relpath((path := os.path.join(root, file)), root_path)
                if glob.globmatch(
                    rel_path,
                    itertools.chain(("!manifest.json"), cfg.exclude_files) if cfg.mod_manifest else cfg.exclude_files,
                    flags=glob.D | glob.G | glob.N,
                ):
                    continue
                pbm.update_t_file()

                fh = FileHandler(rel_path)
                if (rel_path).endswith(".png"):
                    process_image(fh, vd.pngs, pngs)
                    pbm.update_t_item(sum((cfg.image_compress != -1, cfg.extrainfo)))
                elif rel_path.endswith(".tga"):
                    process_image(fh, vd.tgas, tgas)
                    pbm.update_t_item(sum((cfg.image_compress > 6, cfg.extrainfo)))
                elif rel_path.endswith(".lang"):
                    if cfg.obfuscate_jsonui:
                        pbm.update_t_item()
                    langs.append(fh)
                elif rel_path == "manifest.json":
                    manifest = fh
                    pbm.update_t_item()
                elif glob.globmatch(rel_path, ("materials/*.material", "subpacks/*/materials/*.material"), flags=glob.D):
                    splited = fh.path.split(os.sep)
                    fh.subpack_path = os.sep.join(splited[:2]) if "subpacks" in fh.path else ""
                    fh.cut = "/".join(splited[2:] if "subpacks" in fh.path else splited)
                    pbm.update_t_item(
                        sum((cfg.comment, cfg.empty_dict, cfg.sort, cfg.unicode, cfg.obfuscate_entity, cfg.merge_entity))
                    )
                    materials.append(fh)
                elif rel_path.endswith(".json"):
                    splited = fh.path.split(os.sep)
                    fh.subpack_path = os.sep.join(splited[:2]) if "subpacks" in fh.path else ""
                    fh.cut = "/".join(splited[2:] if "subpacks" in fh.path else splited)
                    pbm.update_t_item(sum((cfg.comment, cfg.empty_dict, cfg.sort, cfg.unicode)))

                    if glob.globmatch(rel_path, cfg.wm_references, flags=glob.D | glob.G | glob.N):
                        texture_jsons.append(fh)
                        pbm.update_t_item()
                    elif glob.globmatch(rel_path, cfg.obf_references, flags=glob.D | glob.G | glob.N):
                        texture_jsons_2.append(fh)
                        pbm.update_t_item()
                    if cfg.merged_ui_path and rel_path.endswith("_global_variables.json"):
                        ui_global_vars.append(fh)
                    elif cfg.merged_ui_path and rel_path.endswith("_ui_defs.json"):
                        pbm.update_t_item()
                        ui_defs.append(fh)
                    elif glob.globmatch(
                        rel_path,
                        (f"ui/{namespace}/**/*", f"subpacks/*/ui/{namespace}/**/*", "!**/_*"),
                        flags=glob.D | glob.G | glob.N,
                    ):
                        pbm.update_t_item(sum(bool(i) for i in (cfg.merged_ui_path, cfg.obfuscate_jsonui)))
                        uniqueuis.append(fh)
                    elif glob.globmatch(
                        rel_path,
                        itertools.chain(("ui/**/*", "subpacks/*/ui/**/*", "!**/_*"), cfg.additional_jsonui),
                        flags=glob.D | glob.G | glob.N,
                    ):
                        pbm.update_t_item(sum(bool(i) for i in (cfg.merged_ui_path, cfg.obfuscate_jsonui)))
                        jsonuis.append(fh)
                    elif glob.globmatch(rel_path, ("entity/**/*", "subpacks/*/entity/**/*"), flags=glob.D | glob.G):
                        if cfg.obfuscate_entity:
                            pbm.update_t_item()
                        entities.append(fh)
                    elif glob.globmatch(
                        rel_path,
                        ("animation_controllers/**/*", "subpacks/*/animation_controllers/**/*"),
                        flags=glob.D | glob.G,
                    ):
                        pbm.update_t_item(sum((cfg.obfuscate_entity, cfg.merge_entity)))
                        acs.append(fh)
                    elif glob.globmatch(rel_path, ("animations/**/*", "subpacks/*/animations/**/*"), flags=glob.D | glob.G):
                        pbm.update_t_item(sum((cfg.obfuscate_entity, cfg.merge_entity)))
                        animations.append(fh)
                    elif glob.globmatch(rel_path, ("models/**/*", "subpacks/*/models/**/*"), flags=glob.D | glob.G):
                        pbm.update_t_item(sum((cfg.obfuscate_entity, cfg.merge_entity)))
                        models.append(fh)
                    elif glob.globmatch(
                        rel_path, ("render_controllers/**/*", "subpacks/*/render_controllers/**/*"), flags=glob.D | glob.G
                    ):
                        pbm.update_t_item(sum((cfg.obfuscate_entity, cfg.merge_entity)))
                        rcs.append(fh)
                    elif glob.globmatch(rel_path, ("particles/**/*", "subpacks/*/particles/**/*"), flags=glob.D | glob.G):
                        if cfg.obfuscate_entity:
                            pbm.update_t_item()
                        particles.append(fh)
                    elif glob.globmatch(rel_path, ("materials/*", "subpacks/*/materials/*"), flags=glob.D):
                        if cfg.merge_entity:
                            pbm.update_t_item()
                        material_indexes.append(fh)
                    elif glob.globmatch(
                        rel_path,
                        ("**/*", f"!{cfg.merged_ui_path}"),
                        flags=glob.D | glob.G | glob.N,
                    ):
                        std_jsons.append(fh)
                else:
                    mkdirs(new_path := os.path.join(work_path, os.path.dirname(rel_path)))
                    shutil.copy2(path, new_path)
                    pbm.update_n_file()
        # stats texture json
        if cfg.watermark_paths or cfg.obfuscate_paths:
            for file in renames + obf_names:
                if os.path.exists(os.path.join(root_path, rel_path := f"{os.path.splitext(file.path)[0]}.json")):
                    for j in std_jsons:
                        if rel_path == j:
                            image_jsons.append(j)
                    pbm.update_t_item()

        if cfg.nomedia:
            with default_write(os.path.join(work_path, ".nomedia")):
                pass

        pbm.set_description(f"{namespace} Processing")
        images = obfs.Images(root_path, work_path, namespace)
        json_common = obfs.Jsons(root_path, work_path, namespace)
        if manifest:
            manifest_task = asyncio.create_task(
                json_common.async_manifest(manifest, pack_name, header_uuid, header_version, modules_uuid, modules_version)
            )
        await images.async_rename(pngs, tgas, renames, obf_names, texture_jsons, texture_jsons_2, image_jsons)
        await asyncio.gather(
            images.async_obf(),
            json_common.async_obf(std_jsons),
            obfs.UIs(root_path, work_path, namespace).async_obf(jsonuis, uniqueuis, langs, ui_global_vars, ui_defs),
            obfs.Entities(root_path, work_path, namespace).async_obf(
                acs,
                animations,
                entities,
                material_indexes,
                models,
                particles,
                rcs,
                materials,
            ),
        )
        await json_common.async_obf(
            acs,
            animations,
            entities,
            uniqueuis,
            jsonuis,
            material_indexes,
            models,
            particles,
            rcs,
            materials,
            ui_global_vars,
            ui_defs,
        )
        if manifest:
            await manifest_task

        # output obfuscation table
        del obf_strs_dict[OBFStrType.OBFFILE]
        obf_ref = {k.value: v.forward for k, v in obf_strs_dict.items()}
        # obf_ref = default_dumps({k: obf_ref[k] for k in sorted(obf_ref.keys())}, indent=2)
        obf_ref = default_dumps(obf_ref, indent=2)
        async with aiofiles.open(os.path.join(work_path, "obfuscation_reference.json"), "w", encoding="utf-8") as f:
            await f.write(obf_ref)

        if zip_name != "":
            pbm.set_description(f"{namespace} Compressing")
            if not all(isinstance(i, int) for i in cfg.mtime) or cfg.mtime[0] < 1980:
                logger.error("The mtime format is incorrect.")
                cfg.mtime = ()
            with zipfile.ZipFile(
                os.path.join(work_path, zip_name), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=cfg.pack_compress
            ) as zipf:
                for path in [
                    os.path.join(dirpath, file)
                    for dirpath, _, files in os.walk(work_path)
                    for file in files
                    if file not in [zip_name, "obfuscation_reference.json"]
                ]:
                    zip_info = zipfile.ZipInfo(os.path.relpath(path, work_path))
                    if len(cfg.mtime) == 6:
                        zip_info.date_time = cfg.mtime
                    with open(path, "rb") as d:
                        zipf.writestr(zip_info, d.read(), compress_type=zipfile.ZIP_DEFLATED)

        pbm.set_description(f"{namespace} Completed")
        pbm.pbar.close()


if __name__ == "__main__":
    import utils.log

    main()
