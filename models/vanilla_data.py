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
import logging
import os
import pickle
import sys
import time
from datetime import datetime
from typing import Any, Callable

import regex as re
from wcmatch import glob

from config import cfg
from models import DAG
from utils import (
    ENTITY_CHARS,
    IGNORE_RC_KEYS,
    TraverseControls,
    TraverseJson,
    comment_pattern,
    default_read,
    get_ac_id,
    get_animation_id,
    get_model_id,
    get_rc_id,
    l10n_pattern,
    new_get_id,
    obf_list_fun,
    pause,
    str2bool,
    uivar_pattern,
)

molang_var_pattern = re.compile(
    r"(?<=(?:[!&|<>=*/+\-(){}?[\];',\s]|^)(?:v|t|c|variable|temp|context))\.(.+?)(?=[!&|<>=*/+\-(){}?[\];',\s.]|$)",
    flags=re.I,
)


class VanillaData:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pkl = {}

        if cfg.extract:
            asyncio.run(self.async_extract())
            sys.exit()
        self.reload()

    def reload(self):
        if not cfg.is_vanilla_data_needed:
            return
        elif not cfg.vanilla_data:
            if os.path.isdir(cfg.vanillas_path):
                if str2bool(input("Can't find the extracted vanilla data file, generate it? (y or n) ")):
                    asyncio.run(self.async_extract())
                    return
            else:
                print(
                    "Can't find the extracted vanilla data file, and can't generate it because can't read the original game resource packs directory."
                )
            pause(
                "This can cause serious problems with obfuscation. Press any key to start the obfuscation or Ctrl+C to terminate the process."
            )
        elif cfg.vanilla_data and (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cfg.vanilla_data))).days >= 60:
            if os.path.isdir(cfg.vanillas_path):
                if str2bool(input("The vanilla data file is too old, regenerate it? (y or n) ")):
                    asyncio.run(self.async_extract())
                    return
            else:
                pause(
                    "The vanilla data file is too old, and can't generate it because can't read the original game resource packs directory. Press any key to start the obfuscation."
                )
        else:
            try:
                with open(cfg.vanilla_data, "rb") as f:
                    self.pkl = pickle.load(f)
            except Exception as e:
                print(f"An error occurred while loading Vanilla Data file ({cfg.vanilla_data}):{e}")
                self.logger.exception(e)

    async def async_extract(self):
        dag = DAG()
        self.pkl = {
            "pngs": set(),
            "tgas": set(),
            "l10n": set(),
            "ui_variables": set(),
            "ui_bindings": set(),
            "ui_properties": set(),
            "ui_keywords": set(),
            "animation_controllers": set(),
            "animations": set(),
            "render_controllers": set(),
            "materials": set(),
            "models": set(),
            "particles": set(),
            "material_ids": set(),
            "dag": dag,
        }
        uibind_pattern = re.compile(r'(#.*?)(?=[\|\)\s"])')
        jsonuis = []
        ui_namespace = []
        property_discarded = set()
        entity_mapping = {
            "animation_controllers": ("animation_index", "animation"),
            "render_controllers": ("rc",),
            "materials": ("material_index",),
            "textures": ("texture_index",),
            "geometry": ("model_index", "model"),
            "animations": ("animation_index", "animation"),
            "animate": ("animation_index", "animation"),
            "particle_effects": ("particle_index", "particle"),
        }

        process_path = lambda rel_path, k: self.pkl[k].add("/".join(rel_path.split(os.sep)[1:]))

        def stats_jsonui(data: dict, is_control):
            for k, v in data.items():
                if not is_control and k not in property_discarded:
                    if isinstance(v, str):
                        if "#" in k or "$" in k or "_name" in k or "_control" in k or "@" in v:
                            self.pkl["ui_properties"].discard(k)
                            property_discarded.add(k)
                        else:
                            for ns in ui_namespace:
                                if f"{ns}." in v:
                                    self.pkl["ui_properties"].discard(k)
                                    property_discarded.add(k)
                                    break
                            if k not in property_discarded:
                                self.pkl["ui_properties"].add(k)
                    else:
                        self.pkl["ui_properties"].discard(k)
                        property_discarded.add(k)

                if (
                    isinstance(v, str)
                    and ("$" == k[0] or "#" == k[0])
                    and "$" not in v
                    and "#" not in v
                    and "@" not in v
                    and ")" not in v
                    and v not in self.l10n
                ):
                    self.pkl["ui_keywords"].add(v)
            return data, False

        def stats_es(path: str, key: str = None):
            with default_read(path) as f:
                data = f.read()
            data = json.loads(comment_pattern.sub("", data))
            instance = TraverseStats()
            match key:
                case "ac":
                    instance.traverse(data, "animation", get_ac_id, dag)
                case "animation":
                    instance.traverse(data, key, get_animation_id, dag)
                case "entity":
                    instance.traverse(
                        data,
                        key,
                        new_get_id,
                        dag,
                        stats_index,
                        stats_index_str,
                        entity_mapping,
                    )
                case "materials":
                    if controls := data.get(key):
                        return (k.partition(":")[0] for k in controls if k != "version")
                    else:
                        return ()  # TODO
                case "model":
                    instance.traverse(data, key, get_model_id, dag, process_bone)
                case "particle":
                    instance.traverse(data, key, new_get_id, dag)
                case "rc":
                    instance.traverse(data, key, get_rc_id, dag, ignore_keys=IGNORE_RC_KEYS)

        def stats_index(k, v, entity, tag):
            if tag in entity_mapping:
                dag.add_node(entity_mapping[tag][0], k, tag == "render_controllers")
                dag.add_edge("entity", entity, entity_mapping[tag][0], k)
                if len(entity_mapping[tag]) == 2:
                    dag.add_node(entity_mapping[tag][1], v)
                    dag.add_edge("entity", entity, entity_mapping[tag][1], v)
                    dag.add_edge(entity_mapping[tag][0], k, entity_mapping[tag][1], v)

        def stats_index_str(data, entity, tag):
            if tag in entity_mapping:
                dag.add_node(entity_mapping[tag][0], data, tag == "render_controllers")
                dag.add_edge("entity", entity, entity_mapping[tag][0], data)

        def process_bone(k, v, model, _):
            if k == "name":
                dag.add_node("bone", v)
                dag.add_edge("model", model, "bone", v)

        for root, _, files in os.walk(cfg.vanillas_path):
            for file in files:
                if (rel_path := os.path.relpath((path := os.path.join(root, file)), cfg.vanillas_path)).endswith(".png"):
                    process_path(rel_path, "pngs")
                elif rel_path.endswith(".tga"):
                    process_path(rel_path, "tgas")
                elif glob.globmatch(rel_path, "*/animation_controllers/*.json", flags=glob.D):
                    process_path(rel_path, "animation_controllers")
                    stats_es(path, "ac")
                elif glob.globmatch(rel_path, "*/animations/*.json", flags=glob.D):
                    process_path(rel_path, "animations")
                    stats_es(path, "animation")
                elif glob.globmatch(rel_path, "*/render_controllers/*.json", flags=glob.D):
                    process_path(rel_path, "render_controllers")
                    stats_es(path, "rc")
                elif glob.globmatch(rel_path, "*/entity/*.json", flags=glob.D):
                    stats_es(path, "entity")
                elif glob.globmatch(rel_path, "*/particles/*.json", flags=glob.D):
                    process_path(rel_path, "particles")
                    stats_es(path, "particle")
                elif glob.globmatch(rel_path, "*/materials/*.material", flags=glob.D):
                    process_path(rel_path, "materials")
                    self.pkl["material_ids"].update(stats_es(path, "materials"))
                elif glob.globmatch(rel_path, "*/models/**/*.json", flags=glob.D | glob.G):
                    process_path(rel_path, "models")
                    stats_es(path, "model")
                elif glob.globmatch(rel_path, "*/ui/**/*.json", flags=glob.D | glob.G):
                    with default_read(path) as f:
                        data = f.read()
                    self.pkl["ui_variables"].update(iter(uivar_pattern.findall(data)))
                    self.pkl["ui_bindings"].update(iter(uibind_pattern.findall(data)))
                    ui_namespace.append((j := json.loads(comment_pattern.sub("", data))).get("namespace"))
                    jsonuis.append(j)
                elif glob.globmatch(rel_path, "*/texts/en_US.lang", flags=glob.D):
                    with default_read(path) as f:
                        data = f.read()
                    self.pkl["l10n"].update(iter(l10n_pattern.findall(data)))

        for j in jsonuis:
            TraverseControls(stats_jsonui).traverse(j)

        cfg.vanilla_data = os.path.join(cfg.data_path, time.strftime("VanillaData_%Y-%m-%d-%H-%M-%S.pkl"))
        print(f"Vanilla Data file is saved to {cfg.vanilla_data}")
        try:
            with open(cfg.vanilla_data, "wb") as f:
                pickle.dump(self.pkl, f)
        except Exception as e:
            print(f"An error occurred while writing Vanilla Data file ({cfg.vanilla_data}):{e}")
            self.logger.exception(e)

    @property
    def pngs(self) -> set:
        return self.pkl.get("pngs", set())

    @property
    def tgas(self) -> set:
        return self.pkl.get("tgas", set())

    @property
    def l10n(self) -> set:
        return self.pkl.get("l10n", set())

    @property
    def ui_variables(self) -> set:
        return self.pkl.get("ui_variables", set())

    @property
    def ui_bindings(self) -> set:
        return self.pkl.get("ui_bindings", set())

    @property
    def ui_properties(self) -> set:
        return self.pkl.get("ui_properties", set())

    @property
    def ui_keywords(self) -> set:
        return self.pkl.get("ui_keywords", set())

    @property
    def animation_controllers(self) -> set:
        return self.pkl.get("animation_controllers", set())

    @property
    def animations(self) -> set:
        return self.pkl.get("animations", set())

    @property
    def render_controllers(self) -> set:
        return self.pkl.get("rc", set())

    @property
    def materials(self) -> set:
        return self.pkl.get("materials", set())

    @property
    def models(self) -> set:
        return self.pkl.get("models", set())

    @property
    def particles(self) -> set:
        return self.pkl.get("particles", set())

    @property
    def animation_ids(self) -> dict | set:
        return self.dag.label_map.get("animation", set())

    @property
    def rc_ids(self) -> dict | set:
        return self.dag.label_map.get("rc", set())

    @property
    def material_ids(self) -> set:
        return self.pkl.get("material_ids", set())

    @property
    def model_ids(self) -> dict | set:
        return self.dag.label_map.get("model", set())

    def get_bones(self, from_type, from_node):
        if from_type == "model":
            return set(self.dag.sppf("model", from_node, "bone"))
        return {
            b
            for e in self.dag.ppif(from_type, from_node, "entity")
            for m in self.dag.siif(e, "model")
            for b in self.dag.sipf(m, "bone")
        }

    @property
    def particle_ids(self) -> dict | set:
        if data := self.dag.label_map.get("particle"):
            data["minecraft"] = None
            return data
        return {"minecraft"}

    def _get_indexes(self, from_type, from_node, to_type):
        if from_type == "entity":
            return set(self.dag.sppf("entity", from_node, to_type))
        return {i for e in self.dag.ppif(from_type, from_node, "entity") for i in self.dag.sipf(e, to_type)}

    def get_animation_indexes(self, from_type, from_node):
        return self._get_indexes(from_type, from_node, "animation_index")

    def get_material_indexes(self, from_type, from_node):
        return self._get_indexes(from_type, from_node, "material_index")

    def get_model_indexes(self, from_type, from_node):
        return self._get_indexes(from_type, from_node, "model_index")

    def get_particle_indexes(self, from_type, from_node):
        return self._get_indexes(from_type, from_node, "particle_index")

    def get_texture_indexes(self, from_type, from_node):
        return self._get_indexes(from_type, from_node, "texture_index")

    def get_molang_vars(self, from_type, from_node):
        return {v for e in self.dag.ppif(from_type, from_node, "entity") for v in self.dag.sipf(e, "mv")} | set(
            self.dag.sppf(from_type, from_node, "mv")
        )

    @property
    def dag(self) -> DAG:
        return self.pkl["dag"]


class TraverseStats(TraverseJson):
    def __init__(self, list_fun: Callable[[list[Any]], tuple[list, set | bool]] = obf_list_fun):
        self.list_fun = list_fun

    def traverse(
        self,
        data,
        node_type: str,
        get_id: Callable,
        dag: DAG,
        k_extra: Callable = lambda *args: args,
        str_extra: Callable = lambda *args: args,
        tag_map: set | dict = set(),
        ignore_keys=set(),
        output_dict=None,
    ):
        self.node_type = node_type
        self.get_id = get_id
        self.k_extra = k_extra
        self.str_extra = str_extra
        self.dag = dag
        self.tag_map = tag_map
        self.ignore_keys = ignore_keys

        return super().traverse(data, output_dict)

    def process_id(self, identifier: str):
        if char := next((c for c in ENTITY_CHARS if identifier.lower().startswith(c)), ""):
            return identifier[len(char) :].partition(":")[0]
        return identifier.split(":")[-1]

    def dict_fun(self, data: dict, *args):
        return_extra = []
        identifier, tag = args or (None, None)
        if (identifier or (identifier := self.get_id(data))) and isinstance(identifier, str):
            self.dag.add_node(self.node_type, (identifier := self.process_id(identifier)))

        for k, v in data.items():
            if isinstance(v, str):
                self.k_extra(self.process_id(k), self.process_id(v), identifier, tag)
            return_extra.append(k if k in self.tag_map else None)

        return data, self.ignore_keys, identifier, return_extra

    def str_fun(self, data: str, *args):
        identifier, tag = args or (None, None)

        if identifier:
            for m in molang_var_pattern.findall(data):
                self.dag.add_node("mv", m)
                self.dag.add_edge(self.node_type, identifier, "mv", m)

        if isinstance(data, str):
            self.str_extra(self.process_id(data), identifier, tag)

        return data


vd = VanillaData()
