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
import binascii
import json
import os


def pause(str: str):
    print(str)
    if os.name == "nt":
        import msvcrt

        msvcrt.getch()


def str2bool(v: str | bool):
    if isinstance(v, bool):
        return v
    if (v := v.lower().strip()) in ("yes", "true", "t", "y", "1"):
        return True
    elif v in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


class CustomStrAction(argparse.Action):
    def __call__(self, _, namespace, values, *args):
        setattr(namespace, self.dest, False if values is None else values)


def default_dumps(d, *args, **kwargs):
    return json.dumps(d, *args, **kwargs, ensure_ascii=False)


def gen_crc(data):
    return format(binascii.crc32(data.encode()), "08x")
