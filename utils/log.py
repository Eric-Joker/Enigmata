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
import logging
import os
import sys
import time

from config import cfg


def create_log(
    fmt="\n[%(asctime)s][%(filename)s:%(lineno)d, %(thread)d][%(levelname)s]: %(message)s",
    datefmt="%H:%M:%S",
):
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter(fmt, datefmt)
    if cfg.log_path:
        log_file = os.path.join(cfg.log_path, time.strftime("ENIGMATA_%Y-%m-%d-%H-%M-%S.log"))
        print(f"Log file is saved to {log_file}")
        (file_handler := logging.FileHandler(log_file, encoding="utf-8", delay=True)).setFormatter(formatter)
        logger.addHandler(file_handler)
    if cfg.console:
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    return logger


create_log()
