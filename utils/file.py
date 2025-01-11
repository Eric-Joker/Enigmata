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
import io
import logging
import os

import aiofiles
import aiofiles.os as aioos
from PIL import Image

logger = logging.getLogger(__name__)


def mkdirs(path: str):
    try:
        return os.makedirs(path, exist_ok=True)
    except Exception as e:
        print(f"An error occurred while create directory ({path}):{e}")
        logger.exception(e)


def default_open(file, mode, encoding="utf-8", **kwargs):
    return open(file, mode, encoding=encoding, **kwargs)


def default_read(file, **kwargs):
    return default_open(file, "r", **kwargs)


def default_write(file, newline="\n", **kwargs):
    return default_open(file, "w", newline=newline, **kwargs)


async def async_mkdirs(path: str):
    return await aioos.makedirs(path, exist_ok=True)


async def async_pil_load(path: str):
    try:
        async with aiofiles.open(path, "rb") as f:
            return Image.open(io.BytesIO(await f.read()))
    except Exception as e:
        print(f"An error occurred while loading image ({path}):{e}")
        logger.exception(e)


async def async_pil_dump(path: str, img: Image, format: str, **kwargs):
    img.save((byte_arr := io.BytesIO()), format=format, **kwargs)
    try:
        await async_mkdirs(os.path.dirname(path))
        async with aiofiles.open(path, "wb") as f:
            return await f.write(byte_arr.getvalue())
    except Exception as e:
        print(f"An error occurred while writing image ({path}):{e}")
        logger.exception(e)
