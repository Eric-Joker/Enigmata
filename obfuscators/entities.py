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
import copy
import json
import os
from typing import Any, Callable

import aiofiles
import aiofiles.os as aioos
import regex as re
from wcmatch import glob

from config import cfg
from models import DAG, EntityHandler, FileHandler, OBFStrType, ProcessMapping, pbm, pm_factory, vd
from utils import (
    ENTITY_CHARS,
    IGNORE_RC_KEYS,
    TraverseJson,
    async_mkdirs,
    gen_obfstr,
    get_ac_id,
    get_animation_id,
    get_model_id,
    get_rc_id,
    new_get_id,
    obf_list_fun,
)

from . import OBF

molang_var_pattern = re.compile(
    r"(?<=[!&|<>=*/+\-(){}?[\];',\s]|^)(v|t|c|q|variable|temp|context|query|array)\.(.+?)(?=[!&|<>=*/+\-(){}?[\];',\s.]|$)",
    flags=re.I,
)


class Entities(OBF):
    async def async_obf(
        self,
        acs: list[FileHandler],
        animations: list[FileHandler],
        entities: list[FileHandler],
        material_indexes: list[FileHandler],
        models: list[FileHandler],
        particles: list[FileHandler],
        rcs: list[FileHandler],
        materials: list[FileHandler],
    ):
        self.animation_controllers = acs
        self.animations = animations
        self.material_indexes = material_indexes
        self.models = models
        self.entity = entities
        self.particles = particles
        self.render_controllers = rcs
        self.materials = materials
        self.dag = copy.deepcopy(vd.dag) if cfg.is_vanilla_data_needed else None
        self.exclude_merge_files = set()

        await asyncio.gather(
            self.async_obf_ac(),
            self.async_obf_animation(),
            self.async_obf_materials(),
            self.async_obf_model(),
            self.async_obf_particles(),
            self.async_obf_rc(),
        )
        if cfg.obfuscate_entity:
            await self.async_obf_entity()
            await self.async_obf_bone_patterns()

        for k, v in self.processed.items():
            if "MERGED" in k:
                filetype = k.split("#")[1].lower() if "#" in k else next(i for i in self.__dict__.keys() if i + os.sep in k)
                merged_path = f"{os.path.join(filetype, "entity" if filetype == "models" else "", gen_obfstr(self.namespace+k, OBFStrType.OBFFILE))}.json"
                # merged_path = f"{os.path.join(filetype, "entity" if filetype == "models" else "", gen_obfstr(self.namespace+k, OBFStrType.OBFFILE, 2))}.json"
                getattr(self, filetype).append(FileHandler(merged_path, processed=True))

            new_path = os.path.join(self.work_path, (merged_path if "MERGED" in k else k))
            data = v if isinstance(v, str) else json.dumps(v)
            try:
                await async_mkdirs(os.path.dirname(new_path))
                async with aiofiles.open(new_path, "w", encoding="utf-8") as f:
                    await f.write(data)
            except Exception as e:
                print(f"An error occurred while writing json ({new_path}):{e}")
                self.logger.exception(e)

    def _merge_some_dict(self, data: dict, filetype: str, control_char: str, **merged_dicts):
        if controls := data.get(filetype):
            version: str = data.get("format_version")
            for k, v in controls.items():
                if k[len(control_char) :] not in cfg.exclude_entity_names:
                    merged_dicts[f"v{version.replace(".", "")}"].setdefault(filetype, {})[k] = v

    def _merge_model(self, data: dict, _: str, control_char: str, **merged_dicts):
        if (version := data.get("format_version", "1.8.0")) == "1.8.0" or version == "1.10.0":
            for k, v in data.items():
                if k != "format_version" and k[len(control_char) :] not in cfg.exclude_entity_names:
                    merged_dicts[f"v{version.replace(".", "")}"][k] = v
        else:
            for i in data.get("minecraft:geometry"):
                if (
                    i.get("description", {}).get("identifier", "").partition(":")[0][len(control_char) :][len(control_char) :]
                    not in cfg.exclude_entity_names
                ):
                    merged_dicts[f"v{version.replace(".", "")}"].setdefault("minecraft:geometry", []).append(i)

    async def _async_merge_common(self, fun: Callable, filetype: str, control_char="", **merged_dicts):
        exclude_paths = set()
        fh_list: list[FileHandler] = getattr(self, filetype)

        # TODO: Since I don't need it, the functionality of obfuscating materials has not been tested.
        if filetype == "materials" and self.material_indexes:
            can_merge = set.intersection(
                *[{v for d in json.loads(j) for v in d.values()} for j in self.material_indexes if "fancy" in j or "sad" in j]
            ) + {
                v
                for j in self.material_indexes
                if "fancy" not in j and "sad" not in j
                for d in json.loads(j)
                for v in d.values()
            }

        # exclude some files
        for j in fh_list:
            if cfg.merge_entity and (
                j.subpack_path
                or self.material_indexes
                and filetype == "materials"
                and j.cut not in can_merge
                or any(os.path.basename(j.cut).split("/")[-1].startswith(e) for e in cfg.exclude_entity_names)
                or j.cut in getattr(vd, filetype)
            ):
                self.processed[j.path] = await self.async_get_json_data(j)
                exclude_paths.add(j.cut)

        for j in fh_list.copy():
            splited = os.path.basename(j.path).partition(".")
            # obfuscate the filenames of files that cannot be merged
            if (is_exclude := j.cut in exclude_paths) or not cfg.merge_entity or j.subpack_path:
                if cfg.obfuscate_entity and not is_exclude:
                    j.path = os.path.join(os.path.dirname(j.path), gen_obfstr(splited[0], OBFStrType.OBFFILE) + splited[2])
                    # j.path = os.path.join(os.path.dirname(j.path), gen_obfstr(splited[0], OBFStrType.OBFFILE, 2) + splited[2])
                self.processed[j.path] = await self.async_get_json_data(j)
                j.processed = True
                if cfg.merge_entity:
                    self.exclude_merge_files.add(j.path)
                    pbm.revert_t_item()
            # start merge
            else:
                fun(
                    json.loads(await self.async_get_json_data(j)),
                    filetype,
                    control_char,
                    **merged_dicts,
                )
                if j.processed:
                    await aioos.remove(os.path.join(self.work_path, j.path))

                fh_list.remove(j)
                pbm.revert_t_item(sum((cfg.comment, cfg.empty_dict, cfg.sort, cfg.unicode, cfg.obfuscate_entity)))
                pbm.update_n_file()
                pbm.update()

        for k, v in merged_dicts.items():
            if len(v) > 1:
                self.processed[f"MERGED#{filetype.upper()}#{k[1:]}"] = v

        # TODO: NOT TESTED
        # process material index json
        if filetype == "materials":
            instance = TraverseJson(
                str_fun=lambda data, *_: (
                    f"{"/".join(splited[:-1])}/{OBFStrType.OBFFILE.bi_map[splited[-1]]}"
                    if (splited := data.split("/"))[-1] in can_merge
                    else data
                )
            )
            for j in self.material_indexes:
                self.processed[j.path] = instance.traverse(await self.async_get_json_data(j))
                pbm.update()

    async def _async_obf_common(
        self, filetype: str, mapping=None, eh=EntityHandler(), versions: tuple[str] = (), get_id: Callable = None
    ):
        if mapping is None:
            mapping = {}
        if cfg.merge_entity:
            for v in versions:
                if (j := f"MERGED#{filetype.upper()}#{v}") in self.processed:
                    self.processed[j] = TraverseEntities().traverse(self.processed[j], mapping, eh, self.dag, get_id)
        for j in getattr(self, filetype):
            if filetype == "entity" or j.cut not in getattr(vd, filetype):
                self.processed[j.path] = TraverseEntities().traverse(
                    await self.async_get_json_data(j), mapping, eh, self.dag, get_id
                )

                pbm.update()
                j.processed = True
            else:
                pbm.revert_t_item()

    async def async_obf_ac(self):
        merged_1_10 = {"format_version": "1.10.0"}
        await self._async_merge_common(
            self._merge_some_dict, "animation_controllers", "controller.animation.", v1100=merged_1_10
        )

        if cfg.obfuscate_entity:
            mapping = {
                "states": (acs := ProcessMapping(key=(acseh := EntityHandler(obf_set=OBFStrType.ACS)))),
                "transitions": acs,
                "particle_effects": pm_factory(v_vd=vd.get_particle_indexes, v_type=OBFStrType.PARTICLEINDEX),
                "animations": pm_factory(vd.get_animation_indexes, OBFStrType.ANIMATIONINDEX),
                "initial_state": ProcessMapping(value=acseh),
            }
            await self._async_obf_common(
                "animation_controllers",
                mapping,
                EntityHandler(vd.animation_ids, OBFStrType.ANIMATION, "animation"),
                (1100,),
                get_ac_id,
            )

    async def async_obf_animation(self):
        merged_1_8 = {"format_version": "1.8.0"}
        merged_1_10 = {"format_version": "1.10.0"}
        await self._async_merge_common(self._merge_some_dict, "animations", "animation.", v180=merged_1_8, v1100=merged_1_10)

        if cfg.obfuscate_entity:
            mapping = {"bones": pm_factory(vd.get_animation_indexes, OBFStrType.BONE)}
            await self._async_obf_common(
                "animations",
                mapping,
                EntityHandler(vd.animation_ids, OBFStrType.ANIMATION, "animation"),
                (180, 1100),
                get_animation_id,
            )

    async def async_obf_entity(self):
        mapping = {
            "materials": pm_factory(vd.get_material_indexes, OBFStrType.MATERIALINDEX, vd.material_ids, OBFStrType.MATERIAL),
            "textures": pm_factory(vd.get_texture_indexes, OBFStrType.TEXTUREINDEX),
            "geometry": pm_factory(
                vd.get_model_indexes,
                OBFStrType.MODELINDEX,
                vd.model_ids,
                OBFStrType.MODEL,
                "model_index",
                False,
                "model",
            ),
            "animate": pm_factory(vd.get_animation_indexes, OBFStrType.ANIMATIONINDEX),
            "animations": pm_factory(
                vd.get_animation_indexes, OBFStrType.ANIMATIONINDEX, vd.animation_ids, OBFStrType.ANIMATION
            ),
            "animation_controllers": pm_factory(
                vd.get_animation_indexes, OBFStrType.ANIMATIONINDEX, vd.animation_ids, OBFStrType.ANIMATION
            ),
            "render_controllers": pm_factory(vd.rc_ids, OBFStrType.RC, k_dag_type="rc"),
            "particle_effects": pm_factory(
                vd.get_particle_indexes, OBFStrType.PARTICLEINDEX, vd.particle_ids, OBFStrType.PARTICLE
            ),
        }

        await self._async_obf_common("entity", mapping, EntityHandler(dag_type="entity"), get_id=new_get_id)

    async def async_obf_materials(self):
        await self._async_merge_common(
            lambda data, *_, **merged_dicts: merged_dicts["v100"]["materials"].update(data["materials"]),
            # TODO: NOT TESTED
            "materials",
            "",
            v100={"materials": {}},
        )

        if cfg.obfuscate_entity:
            mapping = {"materials": pm_factory(vd.material_ids, OBFStrType.MATERIAL)}
            await self._async_obf_common("materials", mapping)

    async def async_obf_model(self):
        merged_1_8 = {"format_version": "1.8.0"}
        merged_1_10 = {"format_version": "1.10.0"}
        merged_1_12 = {"format_version": "1.12.0"}
        merged_1_16 = {"format_version": "1.16.0"}
        await self._async_merge_common(
            self._merge_model, "models", "geometry.", v180=merged_1_8, v1100=merged_1_10, v1120=merged_1_12, v1160=merged_1_16
        )

        if cfg.obfuscate_entity:
            mapping = {
                "name": pm_factory(v_vd=vd.get_bones, v_type=OBFStrType.BONE, v_dag_type="bone", v_dag_unique=False),
                "parent": pm_factory(v_vd=vd.get_bones, v_type=OBFStrType.BONE),
                "identifier": ProcessMapping(value=EntityHandler(vd.model_ids, OBFStrType.MODEL)),
                # TODO: Geometry inheritance for format_version 1.12.0 and above.
            }
            await self._async_obf_common(
                "models",
                mapping,
                EntityHandler(vd.model_ids, OBFStrType.MODEL, "model"),
                (180, 1100, 1120, 1160),
                get_model_id,
            )

    async def async_obf_particles(self):
        if cfg.obfuscate_entity:
            mapping = {
                "identifier": pm_factory(v_vd=vd.particle_ids, v_type=OBFStrType.PARTICLE),
                "material": pm_factory(v_vd=vd.material_ids, v_type=OBFStrType.MATERIAL),
            }

            await self._async_obf_common("particles", mapping, EntityHandler(dag_type="particle"), get_id=new_get_id)

    async def async_obf_rc(self):
        merged_1_8 = {"format_version": "1.8.0"}
        merged_1_10 = {"format_version": "1.10.0"}
        await self._async_merge_common(
            self._merge_some_dict, "render_controllers", "controller.render.", v180=merged_1_8, v1100=merged_1_10
        )

        if cfg.obfuscate_entity:
            mapping = {
                "geometry": ProcessMapping((eh := EntityHandler(vd.get_model_indexes, OBFStrType.MODELINDEX)), eh),
                "material": ProcessMapping((eh := EntityHandler(vd.material_ids, OBFStrType.MATERIAL)), eh),
                "textures": ProcessMapping((eh := EntityHandler(vd.get_texture_indexes, OBFStrType.TEXTUREINDEX)), eh),
            }
            await self._async_obf_common(
                "render_controllers",
                mapping,
                EntityHandler(vd.rc_ids, OBFStrType.RC, "rc"),
                (180, 1100),
                get_rc_id,
            )

    async def async_obf_bone_patterns(self):
        # TODO: NOT TESTED
        wildcard = {"materials", "part_visibility"}

        def process_dict(data: dict, *args):
            return_extra = []
            rc = args[1] if args else []
            mi_patterns = args[2] if args else set()

            for k, v in data.items():
                if k == "render_controllers":
                    rc = list(v)
                    continue
                elif isinstance(v, dict) and "geometry" in v:
                    TraverseJson(
                        str_fun=lambda data, *_: (
                            mi_patterns.add(data.partition("geometry.")[2]) if data.startswith("geometry.") else None,
                            data,
                        )[1]
                    ).traverse(v)
                return_extra.append(k if k in wildcard else None)

            return (
                data,
                IGNORE_RC_KEYS
                | {
                    "geometry",
                    "geometries",
                },
                return_extra,
                rc,
                mi_patterns,
            )

        def process_list(data: list, *args):
            new_list = []
            for i in data:
                if args and args[0] in wildcard:
                    for k, v in i.items():
                        if "*" != k and "*" in k:
                            processed = [
                                {
                                    OBFStrType.BONE.bi_map.get(
                                        fin := self.dag[bone].split(":")[1], fin
                                    ): f"{(splited := v.partition('.'))[0]}.{OBFStrType.MATERIALINDEX.bi_map.get(splited[2], splited[2])}"
                                }
                                # Find all entity that reference this render controller
                                for entity in tuple(self.dag.ppif("rc", args[1], "entity"))[-1]
                                # Find all model indexes referenced by entities and filter them
                                for mi in self.dag.successor_indices(entity)
                                if (splited := self.dag[mi].partition("#"))[0] == "model_index" and splited[2] in args[2]
                                # Find the model corresponding to the model index
                                for model in self.dag.siif(mi, "model")
                                # Find all bones from the model
                                for bone in self.dag.successors(model)
                                if glob.globmatch(bone, k)
                            ]
                        else:
                            processed = [
                                {
                                    OBFStrType.BONE.bi_map.get(
                                        k, k
                                    ): f"{(splited := v.partition('.'))[0]}.{OBFStrType.MATERIALINDEX.bi_map.get(splited[2], splited[2])}"
                                }
                            ]

                        if any(k in OBFStrType.BONE.bi_map for d in processed for k in d):
                            new_list += processed
                        else:
                            new_list.append(i)
                else:
                    new_list.append(i)

            return new_list, True

        for j in self.render_controllers:
            self.processed[j.path] = TraverseJson(process_dict, process_list).traverse(await self.async_get_json_data(j))


class TraverseEntities(TraverseJson):
    def __init__(self, list_fun: Callable[[list[Any]], tuple[list, set | bool]] = obf_list_fun):
        self.list_fun = list_fun

    def traverse(
        self,
        data,
        mapping: dict[str, ProcessMapping],
        handler: EntityHandler,
        dag: DAG,
        get_id: Callable = None,
        output_dict={},
    ):
        self.handler = handler
        self.mapping = mapping
        self.dag = dag
        self.get_id = get_id

        from config import cfg
        from models import vd

        self.vd = vd
        self.cfg = cfg

        return super().traverse(data, output_dict)

    def get_truly_id(self, identifier: str):
        if char := next((c for c in ENTITY_CHARS if identifier.lower().startswith(c)), ""):
            return identifier[len(char) :].partition(":")[0], char
        return identifier.split(":")[-1], ""

    def is_exclude(self, data: str, vd: set | dict | tuple | Callable, identifier: str = None):
        return (
            (splited := self.get_truly_id(data))[0] in self.cfg.exclude_entity_names
            or splited[0] in (vd if isinstance(vd, (set, dict, tuple)) else vd(self.handler.dag_type, identifier)),
            splited[0],
            splited[1],
        )

    def gen_metadata(self, data, args: str, handler: EntityHandler, identifier: str = None, exclude=False):
        if not isinstance(data, str) or exclude or args and not handler:
            return True, data, ""
        if len(splited := data.split(":")) == 2:
            return zip(*(self.is_exclude(i, handler.vd if handler else self.handler.vd, identifier) for i in splited))
        return self.is_exclude(data, handler.vd if handler else self.handler.vd, identifier)

    def obf_value(
        self, data: str, is_exclude: bool | tuple, splited: str | tuple, char: str, handler: EntityHandler, identifier: str
    ):
        if handler.dag_type:
            self.dag.add_node(handler.dag_type, data, handler.dag_unique)
            if handler is not self.handler:
                self.dag.add_node(self.handler.dag_type, identifier, self.handler.dag_unique)
                self.dag.add_edge(self.handler.dag_type, identifier, handler.dag_type, data)
        if isinstance(splited, tuple):
            return f"{char[0]}{splited[0] if is_exclude[0] else gen_obfstr(splited[0], handler.obf_set)}:{char[1]}{splited[1] if is_exclude[1] else gen_obfstr(splited[1], handler.obf_set)}"
        return data if is_exclude else char + gen_obfstr(splited, handler.obf_set)

    def dict_fun(self, data: dict[str, Any], *args):
        new_dict = {}
        stop = set()
        return_extra = []
        arg_key, identifier = args or (None, None)
        if self.get_id and (identifier or (identifier := self.get_id(data))) and isinstance(identifier, str):
            identifier = self.get_truly_id(identifier)[0]

        for k, v in data.items():
            m = self.mapping.get(
                arg_key, (by_key := self.mapping.get(k)) or (ProcessMapping(self.handler) if "." in k else None)
            )
            if is_array := isinstance(v, list) and k.lower().startswith("array."):
                m = pm_factory(k_type=OBFStrType.RCARRAY)

            if m:
                k_is_exclude, k_id, k_char = self.gen_metadata(k, arg_key, m.key, identifier, by_key)
                v_is_exclude, v_id, v_char = self.gen_metadata(v, arg_key, m.value, identifier)

                v_is_str = isinstance(v, str)
                new_v = self.obf_value(v, v_is_exclude, v_id, v_char, m.value, identifier) if v_is_str and not is_array else v
                new_dict[new_k := self.obf_value(k, k_is_exclude, k_id, k_char, m.key, identifier)] = new_v

                if v_is_str and v_is_exclude or new_v != v:
                    stop.add(new_k)
            else:
                new_dict[k] = v
            return_extra.append(k if k in self.mapping else None)

        return new_dict, stop, return_extra, identifier

    def str_fun(self, data: str, *args):
        is_matched = False

        def repl(match: re.Match):
            nonlocal is_matched
            is_matched = True

            if (
                (char := match.group(1))[0] == "q"
                or char != "array"
                and match.group(2) in self.vd.get_molang_vars(self.handler.dag_type, identifier)
                or match.group(2) in self.cfg.exclude_entity_names
            ):
                return f"{char}.{match.group(2)}"
            if char == "array":
                return f"{char}.{gen_obfstr(match.group(2), OBFStrType.RCARRAY)}"
            return f"{char[0]}.{gen_obfstr(match.group(2), OBFStrType.MOLANGVAR)}"

        arg_key, identifier = args or (None, None)

        if (data := molang_var_pattern.sub(repl, data)) and not is_matched and (m := self.mapping.get(arg_key)):
            return self.obf_value(data, *self.gen_metadata(data, arg_key, m.key, identifier), m.key, identifier)
        else:
            return data
