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
import math
import random
from typing import Any, Callable

import regex as re

from models import OBFStrType
from utils import default_dumps

NOT_CONTROL_KEYS = {
    "requires",
    "binding_name",
    "binding_name_override",
    "binding_type",
    "source_control_name",
    "source_property_name",
    "target_property_name",
    "from_button_id",
    "to_button_id",
    "mapping_type",
}  # If any of these keys exist in the first-level dictionary of a list, then the dictionary is not a control.

ENTITY_CHARS = ("geometry.", "controller.animation.", "animation.", "controller.render.", "materials.", "texture.", "array.")

IGNORE_RC_KEYS = {"format_version", "on_fire_color", "is_hurt_color", "overlay_color", "ignore_lighting", "filter_lighting"}

comment_pattern = re.compile(r'(?<!:\s*"[^"]*?)(//.*?$|/\*[\s\S]*?\*/)', re.MULTILINE)
uivar_pattern = re.compile(r'(\$.+?)(?=[@\|\)\s"])')
l10n_pattern = re.compile(r"(^.+?)(?==.+?[\n#])", re.MULTILINE)

obf_dict_fun = lambda d, *args: (d, False, *args)
obf_list_fun = lambda l, *args: (l, False, *args)
obf_str_fun = lambda s, *_: s

new_get_id = lambda d: d.get("description", {}).get("identifier", "")
get_model_id = lambda d: new_get_id(d) or [k if k.startswith("geometry.") else None for k in d]
get_ac_id = lambda d: list(d.get("animation_controllers", {}))
get_animation_id = lambda d: list(d.get("animations", {}))
get_rc_id = lambda d: list(d.get("render_controllers", {}))


class TraverseJson:
    def __init__(
        self,
        dict_fun: Callable[[dict[str, Any]], tuple[dict[str, Any], set | bool]] = obf_dict_fun,
        list_fun: Callable[[list[Any]], tuple[list, set | bool]] = obf_list_fun,
        str_fun: Callable[[str], str] = obf_str_fun,
    ):
        self.dict_fun = dict_fun
        self.list_fun = list_fun
        self.str_fun = str_fun

    def traverse(self, data, output_dict=None):
        cache_data = self._traverse(json.loads(comment_pattern.sub("", data)) if isinstance(data, str) else data)
        return default_dumps(cache_data, indent=2) if isinstance(data, str) and not output_dict else cache_data

    def _traverse(self, data: Any, *args):
        if isinstance(data, dict):
            return self.process_dict(data, *args)

        elif isinstance(data, list):
            return self.process_list(data, *args)

        elif isinstance(data, str):
            return self.process_str(data, *args)

        return data

    def process_dict(self, data: dict[str, Any], *args):
        d, stop, *rest = self.dict_fun(data, *args)
        return {
            k: (
                v
                if stop and (stop == True or k in stop)
                else self._traverse(
                    v,
                    *(rest[li][i] if isinstance(a, list) and len(a) == len(data) else a for li, a in enumerate(rest)),
                )
            )
            for i, (k, v) in enumerate(d.items())
        }

    def process_list(self, data: list, *args):
        l, stop, *rest = self.list_fun(data, *args)
        return [
            (
                v
                if stop and (stop == True or i in stop)
                else self._traverse(
                    v,
                    *(rest[li][i] if isinstance(a, list) and len(a) == len(data) else a for li, a in enumerate(rest)),
                )
            )
            for i, v in enumerate(l)
        ]

    def process_str(self, data: str, *args):
        return self.str_fun(data, *args)


class TraverseControls(TraverseJson):
    def traverse(self, data, output_dict=None, exclude=True):
        self.exclude = exclude
        self.is_first_level = True
        from config import cfg

        self.cfg = cfg

        return super().traverse(data, output_dict)

    def process_dict(self, data: dict[str, Any], *args):
        is_control = args and args[0] or self.is_first_level
        self.is_first_level = False
        new_dict = {}

        # exclude some keys
        if ns := data.get("namespace"):
            new_dict["namespace"] = ns
        for k, v in data.items():
            if self.exclude and k.partition("@")[0] in self.cfg.excluded_jsonui_names:
                new_dict[k] = v
            if k in NOT_CONTROL_KEYS:
                is_control = False

        d, stop, *rest = self.dict_fun({k: v for k, v in data.items() if k not in new_dict}, is_control)
        new_dict |= {
            k: (
                v if stop and (stop == True or k in stop) else self._traverse(v, k == "value", *filter(None, rest))
            )  # second prarm (k == "value") => probably control, "value" => modifications;
            for k, v in d.items()
            if k not in new_dict
        }
        return new_dict

    def process_list(self, data: list, *args):
        l, stop, *rest = self.list_fun(data, *args)
        return [
            v if stop and (stop == True or i in stop) else self._traverse(v, True, *filter(None, rest)) for i, v in enumerate(l)
        ]

    def process_str(self, data: str, *args):
        from config import cfg

        return data if self.exclude and data.partition("@")[-1] in cfg.excluded_jsonui_names else self.str_fun(data, *args)


ENUM_LINKS = (
    (OBFStrType.UICONTROL, OBFStrType.UIVARIABLE, OBFStrType.UIBINDIND, OBFStrType.LOCALIZATION),
    (
        OBFStrType.ACS,
        OBFStrType.ANIMATION,
        OBFStrType.ANIMATIONINDEX,
        OBFStrType.BONE,
        OBFStrType.MATERIAL,
        OBFStrType.MATERIALINDEX,
        OBFStrType.MODEL,
        OBFStrType.MODELINDEX,
        OBFStrType.MOLANGVAR,
        OBFStrType.PARTICLE,
        OBFStrType.PARTICLEINDEX,
        OBFStrType.RC,
        OBFStrType.RCARRAY,
        OBFStrType.TEXTUREINDEX,
    ),
)


def gen_obfstr(data: str, enum: OBFStrType, link=0):
    from config import cfg

    if data in enum.bi_map:
        return enum.bi_map[data]

    (rd := random.Random()).seed(data)

    # Get one from other existing obfuscated string set to increase coupling.
    if available_items := (
        [v for e in ENUM_LINKS[link - 1] for v in e.bi_map.backward if v not in enum.bi_map.backward]
        if link
        else [v for et in ENUM_LINKS if enum in et for e in et for v in e.bi_map.backward if v not in enum.bi_map.backward]
    ):
        enum.bi_map[data] = (rdstr := rd.choice(available_items))
        return rdstr

    str_pool = cfg.obfuscate_ascll if enum in ENUM_LINKS[1] else cfg.obfuscate_strs
    long = 2
    times = 0
    strslen = sum(len(s) for s in str_pool)
    factor = min(2147483647, 10 ** math.ceil(math.log10(strslen))) / min(2147483647, strslen)
    computed = int(math.log(2147483647, factor))
    while True:
        if times > (factor - 1):
            long += 1
            times = 0
        long = long if factor == 1 else next(i for i in range(long, computed) if len(enum.bi_map) < factor**i)

        # gen
        rdstr = "".join(rd.choices(rd.choice(tuple(str_pool)), k=long)) * rd.randint(1, 3)
        if (rdstr in enum.bi_map.backward or ("0" <= rdstr[0] <= "9")) and long < computed:
            times += 1
            if all(c == data[0] for c in data):
                rd.seed(data * rd.randint(1, 3))
            else:
                rd.shuffle(listed_data := list(data))
                rd.seed("".join(listed_data))
            continue
        enum.bi_map[data] = rdstr
        return rdstr
