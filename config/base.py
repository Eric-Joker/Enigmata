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
import argparse
import itertools
import logging
import os
import time

import regex as re
import yaml

from utils import CustomStrAction, default_read, mkdirs, str2bool

CONFIG_FILE = "./config.yaml"


class EnigmataConfig:
    tmp_dir = os.getenv("TEMP" if os.name == "nt" else "TMPDIR", "/tmp")
    DATA_PATH = os.path.join(tmp_dir, "Enigmata")
    WORK_PATH = os.path.join(DATA_PATH, "output")
    VANILLAS_PATH = ""
    LOG_PATH = ""
    CONSOLE = True
    PATH = []
    PACK_NAME = []
    HEADER_UUID = []
    HEADER_VERSION = []
    MODULES_UUID = []
    MODULES_VERSION = []
    EXCLUDED_FILES = (".git*/**", ".mc*", "LICENSE", "README.md")
    NOMEDIA = True
    ZIP_NAME = []
    NAMESPACE = []
    VANILLA_DATA = ""
    OBFUSCATE_STRS = ("IlＩｌ｜", "0Oo°Οο⁰₀○。〇︒０Ｏｏ")
    OBFUSCATE_ASCLL = "abcdefghijklmnopqrstuvwxyz"
    SORT = True
    UNICODE = True
    EMPTY_DICT = True
    UNFORMAT = True
    COMMENT = True
    MERGED_UI_PATH = r"\font\.test.png"
    DEFS_CONFUSED = r'{"test_assets_defs":[0]}'
    MERGE_ENTITY = True
    OBFUSCATE_JSONUI = True
    OBFUSCATE_ENTITY = True
    ADDITIONAL_JSONUI = set()
    WATERMARK_PATHS = ("**/textures/blocks/**", "**/textures/items/**")
    OBFUSCATE_PATHS = "**/textures/ui/**"
    WM_REFERENCES = ("**/textures/item_texture.json", "**/textures/terrain_texture.json", "**/textures/flipbook_textures.json")
    OBF_REFERENCES = ("**/ui/**/*.json", "**/entity/*.json", "**/particles/*.json", "!**/textures/**")
    EXTRAINFO = True
    IMAGE_COMPRESS = 9
    PACK_COMPRESS = 9
    MTIME = (1989, 8, 10, 11, 45, 14)
    DEBUG = False
    EXCLUDED_JSONS = (
        "manifest.json",
        "**/loading_messages.json",
        "**/blocks.json",
        "**/item_texture.json",
        "**/flipbook_textures.json",
        "**/terrain_texture.json",
        "**/sound_definitions.json",
        "**/_global_variables.json",
        "**/language_names.json",
        "**/languages.json",
        "**/splashes.json",
    )
    EXCLUDED_JSONUI_NAMES = set()
    EXCLUDED_ENTITY_NAMES = set()

    def __init__(self):
        self._add_arguments()
        self.logger = logging.getLogger(__name__)
        self.reload(self.args.config.strip("'"))

    def __getattr__(self, key: str):
        def traverse(d: dict):
            for k in list(d.keys()):
                if k == key:
                    setattr(self, k, d[k])
                    return d[k]
                if isinstance(d[k], dict) and (result := traverse(d[k])) != None:
                    return result
            return None

        return traverse(vars(self))

    def _add_arguments(self):
        parser = argparse.ArgumentParser(description="Console parameters will take precedence over configuration files.")
        argsGroup1 = parser.add_argument_group("Common Parameters")
        argsGroup1.add_argument("--path", "-p", nargs="*", type=str, help="Path to the resource pack to obfuscate.")
        argsGroup1.add_argument(
            "--namespace",
            "-n",
            nargs="*",
            type=str,
            help="Namespace to be used when obfuscating each resource pack. It needs to correspond to the pack.",
        )
        argsGroup1.add_argument(
            "--zip-name",
            "-z",
            nargs="*",
            type=str,
            help="The zip file name of the zip archive that is automatically packed after obfuscation.",
        )
        argsGroup1.add_argument(
            "--extract", "-e", action="store_true", default=None, help="Extracting data from vanillas path."
        )
        argsGroup1.add_argument("--config", "-c", type=str, default=CONFIG_FILE, help="Path to yaml configuration file.")
        argsGroup1.add_argument("--pack-name", nargs="*", type=str, help="For manifest.json.")
        argsGroup1.add_argument("--header-uuid", nargs="*", type=str, help="For manifest.json.")
        argsGroup1.add_argument("--header-version", nargs="*", type=str, help="For manifest.json.")
        argsGroup1.add_argument("--modules-uuid", nargs="*", type=str, help="For manifest.json.")
        argsGroup1.add_argument("--modules-version", nargs="*", type=str, help="For manifest.json.")
        argsGroup2 = parser.add_argument_group("Script Parameters")
        argsGroup2.add_argument(
            "--excluded-files",
            nargs="*",
            type=str,
            help="Files in the resource pack directory but not part of the resource pack.",
        )
        argsGroup1.add_argument(
            "--nomedia",
            action="store_true",
            default=None,
            help="Create .nomedia file in the root directory of the resource pack",
        )
        argsGroup2.add_argument("--work-path", "-w", type=str, help="Path to output directory.")
        argsGroup2.add_argument("--data-path", "-d", type=str, help="Path to data directory.")
        argsGroup2.add_argument("--vanillas-path", "-v", type=str, help="Path to the game's original resource pack.")
        argsGroup2.add_argument("--vanilla-data", type=str, help="Specify the path to the extracted vanilla data file.")
        argsGroup2.add_argument(
            "--log-path",
            "-l",
            action=CustomStrAction,
            nargs="?",
            type=str,
            help="The directory of the log file. If no parameter is passed, the log file will not be written.",
        )
        argsGroup2.add_argument("--console", type=str2bool, help="Console log.")
        argsGroup2.add_argument("--debug", type=str2bool)
        argsGroup3 = parser.add_argument_group("Function Options")
        argsGroup3.add_argument(
            "--obfuscate-strs", "-s", nargs="*", type=str, help="Character pool for generating obfuscated strings."
        )
        argsGroup3.add_argument(
            "--obfuscate-ascll", "-a", nargs="*", type=str, help="Character pool for generating obfuscated strings."
        )
        argsGroup3.add_argument("--sort", type=str2bool, help="Sort JSON keys in natural order.")
        argsGroup3.add_argument(
            "--unicode", type=str2bool, help="Convert characters in Json files to Unicode whenever possible."
        )
        argsGroup3.add_argument(
            "--empty-dict", type=str2bool, help="Add meaningless empty dictionary “{}” at the end of the json."
        )
        argsGroup3.add_argument("--unformat", type=str2bool, help="Remove JSON formatting.")
        argsGroup3.add_argument(
            "--comment", type=str2bool, help="Adding CRC32 annotations to JsonUI files to split obfuscated strings with “:”."
        )
        argsGroup3.add_argument(
            "--merged-ui-path",
            action=CustomStrAction,
            nargs="?",
            type=str,
            help="Merge JsonUI files under /ui/namespace into one file with relative path. If no parameter is passed, it will not be merged.",
        )
        argsGroup3.add_argument(
            "--defs-confused",
            action=CustomStrAction,
            nargs="?",
            type=str,
            help="Add key values for obfuscation to _ui_defs.json.",
        )
        argsGroup3.add_argument(
            "--merge-entity",
            type=str2bool,
            help="Combine entity series files into one file each.",
        )
        argsGroup3.add_argument("--obfuscate-jsonui", type=str2bool, help="Obfuscate JsonUI.")
        argsGroup3.add_argument(
            "--obfuscate-entity",
            type=str2bool,
            help="Obfuscate entity series.",
        )
        argsGroup3.add_argument(
            "--additional-jsonui", nargs="*", type=str, help="JsonUI files that are not in the (subpacks/*/)ui/ folder."
        )
        argsGroup3.add_argument(
            "--watermark-paths",
            nargs="*",
            type=str,
            help="Adds a string randomly split by namespace to all mapping filenames.",
        )
        argsGroup3.add_argument(
            "--wm-references",
            nargs="*",
            type=str,
            help="JSON of files referencing those to be watermarked.",
        )
        argsGroup3.add_argument(
            "--obfuscate-paths",
            nargs="*",
            type=str,
            help="Renames all mapping filenames to a string randomly generated by obfuscate_strs.",
        )
        argsGroup3.add_argument(
            "--obf-references",
            nargs="*",
            type=str,
            help="JSON of files referencing those to be obfuscated.",
        )
        argsGroup3.add_argument(
            "--extrainfo", type=str2bool, help="Add the namespace to the tEXt section of all PNG and the ID section of all TGA."
        )
        argsGroup3.add_argument(
            "--image-compress", type=int, help="Compression level for all PNG, enable TGA compression when >6."
        )
        argsGroup3.add_argument(
            "--pack-compress",
            type=int,
            help="The compression level of the zip archive after obfuscation. ",
        )
        argsGroup3.add_argument(
            "--mtime",
            nargs="*",
            type=int,
            help="Modify the mtime of each file during packaging.",
        )
        argsGroup3.add_argument(
            "--excluded-jsons",
            nargs="*",
            type=str,
            help="Json without any processing.",
        )
        argsGroup3.add_argument(
            "--excluded-jsonui-names",
            nargs="*",
            type=str,
            help="JsonUI first-level control names, variable names, hard-bound names without obfuscation, annotation, escaping, de-formatting, and order advancement.",
        )
        argsGroup3.add_argument(
            "--excluded-entity-names",
            nargs="*",
            type=str,
            help="Key names and names of entity series ID, and molang variable names in them that are not obfuscated, escaped, or de-formatted in files.",
        )
        self.args = parser.parse_args()

    def reload(self, file: str):
        try:
            with default_read(file) as f:
                cfg = yaml.safe_load(f)
        except Exception as e:
            print(f"An error occurred while loading config file ({file}):{e}")
            self.logger.exception(e)

        # Convert user-friendly to program-friendly.
        if "cfg" in locals():
            self.path = (pack := cfg.get("packs", {})).get("path", self.PATH)
            self.pack_name = (manifest := pack.get("manifest")).get("name", self.PACK_NAME)
            self.header_uuid = manifest.get("header_uuid", self.HEADER_UUID)
            self.header_version = manifest.get("header_version", self.HEADER_VERSION)
            self.modules_uuid = manifest.get("modules_uuid", self.MODULES_UUID)
            self.modules_version = manifest.get("modules_version", self.MODULES_VERSION)
            self.log_path = cfg.get("log", {}).get("path", self.LOG_PATH) if cfg.get("log", {}).get("file", True) else ""
            obfuscator = cfg.get("obfuscator", {})
            self.merged_ui_path = (
                json_funs.get("merge_jsonui", {}).get("path", self.MERGED_UI_PATH)
                if (json_funs := obfuscator.get("json_funs", {})).get("merge_jsonui", {}).get("enable", True)
                else ""
            )
            wm_enable = (file_funs := obfuscator.get("file_funs", {}))
            wm = file_funs.get("filename_watermark", {})
            self.watermark_paths = (
                wm.get("paths", self.WATERMARK_PATHS) if (wm_enable.get("filename_watermark", {}).get("enable", True)) else []
            )
            self.wm_references = wm.get("references", self.WM_REFERENCES) if wm_enable else []
            obf_enable = (file_funs := obfuscator.get("file_funs", {}))
            obf = file_funs.get("filename_obfuscation", {})
            self.obfuscate_paths = (
                obf.get("paths", self.OBFUSCATE_PATHS)
                if (obf_enable.get("filename_obfuscation", {}).get("enable", True))
                else []
            )
            self.obf_references = obf.get("references", self.OBF_REFERENCES) if obf_enable else []

            for key, value in cfg.items():
                if value is not None:
                    setattr(self, key, value)
        # Flags have a higher priority than configuration files
        for key, value in vars(self.args).items():
            if value is not None:
                setattr(self, key, value)

        # default var
        self.data_path = self.DATA_PATH if self.data_path is None else self.data_path
        self.work_path = self.WORK_PATH if self.work_path is None else self.work_path
        self.log_path = self.LOG_PATH if self.log_path is None else self.log_path
        self.obfuscate_jsonui = self.OBFUSCATE_JSONUI if self.obfuscate_jsonui is None else self.obfuscate_jsonui
        self.obfuscate_entity = self.OBFUSCATE_ENTITY if self.obfuscate_entity is None else self.obfuscate_entity
        self.merge_entity = self.MERGE_ENTITY if self.merge_entity is None else self.merge_entity
        self.extrainfo = self.EXTRAINFO if self.extrainfo is None else self.extrainfo
        self.console = self.CONSOLE if self.console is None else self.console
        self.image_compress = self.IMAGE_COMPRESS if self.image_compress is None else self.image_compress
        self.pack_compress = self.PACK_COMPRESS if self.pack_compress is None else self.pack_compress
        self.sort = self.SORT if self.sort is None else self.sort
        self.merged_ui_path = self.MERGED_UI_PATH if self.merged_ui_path is None else self.merged_ui_path
        self.nomedia = self.NOMEDIA if self.nomedia is None else self.nomedia
        self.extract = False if self.extract is None else self.extract
        self.vanillas_path = self.VANILLAS_PATH if self.vanillas_path is None else self.vanillas_path
        self.defs_confused = self.DEFS_CONFUSED if self.defs_confused is None else self.defs_confused

        # typecasting and supplementary attrs
        self.mtime = tuple(self.mtime) if self.mtime else self.MTIME
        self.excluded_files = tuple(self.excluded_files) if self.excluded_files else self.EXCLUDED_FILES
        self.obfuscate_strs = tuple(self.obfuscate_strs) if self.obfuscate_strs else self.OBFUSCATE_STRS
        self.obfuscate_ascll = tuple(self.obfuscate_ascll) if self.obfuscate_ascll else self.OBFUSCATE_ASCLL
        self.watermark_paths = tuple(self.watermark_paths)
        self.wm_references = tuple(self.wm_references)
        self.obfuscate_paths = tuple(self.obfuscate_paths)
        self.obf_references = tuple(self.obf_references)
        self.excluded_jsons = tuple(self.excluded_jsons) if self.excluded_jsons else self.EXCLUDED_JSONS
        self.excluded_jsonui_names = (
            set(self.excluded_jsonui_names) if self.excluded_jsonui_names else self.EXCLUDED_JSONUI_NAMES
        )
        self.excluded_entity_names = (
            set(self.excluded_entity_names) if self.excluded_entity_names else self.EXCLUDED_ENTITY_NAMES
        )
        self.additional_jsonui = tuple(self.additional_jsonui) if self.additional_jsonui else self.ADDITIONAL_JSONUI
        self.path = self.path if isinstance(self.path, list) else (self.path,)
        self.pack_name = self.pack_name if isinstance(self.pack_name, list) else (self.pack_name,)
        self.header_uuid = self.header_uuid if isinstance(self.header_uuid, list) else (self.header_uuid,)
        self.header_version = self.header_version if isinstance(self.header_version, list) else (self.header_version,)
        self.modules_uuid = self.modules_uuid if isinstance(self.modules_uuid, list) else (self.modules_uuid,)
        self.modules_version = self.modules_version if isinstance(self.modules_version, list) else (self.modules_version,)
        self.zip_name = self.zip_name if isinstance(self.zip_name, list) else (self.zip_name,)
        self.namespace = self.namespace if isinstance(self.namespace, list) else (self.namespace,)
        if self.debug:
            self.comment = False
            self.unformat = False
            self.empty_dict = False
            self.unicode = False
            self.sort = False
        self.is_vanilla_data_needed = (self.obfuscate_jsonui or self.obfuscate_entity) and not self.extract
        self.excluded_jsonui_names.add("namespace")
        self.excluded_entity_names.update(("player.base", "format_version", "version"))
        self.excluded_names = self.excluded_jsonui_names | self.excluded_entity_names
        uuid_pattern = re.compile("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
        if self.pack_name and len(self.path) != len(self.pack_name):
            raise ValueError("The pack name needs to correspond to the resource package.")
        if self.header_uuid:
            if len(self.path) != len(self.header_uuid):
                raise ValueError("The header uuid name needs to correspond to the resource package.")
            if not all(not isinstance(u, str) or uuid_pattern.match(u) for u in self.header_uuid):
                raise ValueError("header/uuid format error")
        if self.header_version and len(self.path) != len(self.header_version):
            raise ValueError("The header version name needs to correspond to the resource package.")
        if self.modules_uuid:
            if len(self.path) != len(self.modules_uuid):
                raise ValueError("The modules uuid name needs to correspond to the resource package.")
            if any(
                isinstance(h, str) and isinstance(m, str) and h == m
                for h, m in itertools.zip_longest(self.header_uuid, self.modules_uuid, fillvalue=None)
            ):
                raise ValueError("header/uuid cannot be the same as modules/uuid")
            if not all(not isinstance(u, str) or uuid_pattern.match(u) for u in self.modules_uuid):
                raise ValueError("modules/uuid format error")
        if self.modules_version and len(self.path) != len(self.modules_version):
            raise ValueError("The modules version name needs to correspond to the resource package.")
        self.mod_manifest = (
            self.pack_name or self.header_uuid or self.header_version or self.modules_uuid or self.modules_version
        )

        mkdirs(self.data_path)
        mkdirs(self.work_path)
        mkdirs(self.log_path) if self.log_path else None

        if not os.path.isdir(self.data_path):
            if os.path.isdir(file_dir := os.path.dirname(self.vanilla_data)):
                self.data_path = file_dir
            else:
                self.data_path = ""
                self.logger.error("Cannot read the data directory.")
                return
        # Select Vanilla Data, prioritizing files with the specified format in their filenames, with newer files taking precedence.
        if not self.vanilla_data and self.is_vanilla_data_needed:
            latest_version = 0  # datetime filename => str; mtime => int
            datetime_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})")
            time_format = "%Y-%m-%d-%H-%M-%S"

            with os.scandir(self.data_path) as entries:
                for entry in entries:
                    if entry.is_file() and (
                        (version := match.group(1) if (match := datetime_pattern.search(entry.name)) else None)
                        and time.strptime(version, time_format)
                        > (time.strptime(latest_version, time_format) if isinstance(latest_version, str) else time.gmtime(0))
                        or not isinstance(latest_version, str)
                        and entry.name.endswith(".pkl")
                        and (version := entry.stat().st_mtime) > latest_version
                    ):
                        self.vanilla_data = entry.path
                        latest_version = version
            print(f"Reading Vanilla Data by {self.vanilla_data}")


cfg = EnigmataConfig()
