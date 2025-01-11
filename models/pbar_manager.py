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
from tqdm import tqdm

from config import cfg


class PbarManager:
    def __init__(self):
        self.n_file = 0
        self.t_file = 0
        self.pbar: tqdm = None

    def check_console(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs) if cfg.console else None

        return wrapper

    @check_console
    def set_description(self, desc):
        self.pbar.set_description(desc)

    @check_console
    def update_t_file(self):
        self.t_file += 1
        self.pbar.unit = f"items {self.n_file}/{self.t_file}files"
        # self.pbar.refresh()

    @check_console
    def revert_t_item(self, increment):
        self.pbar.total -= increment
        # self.pbar.refresh()

    @check_console
    def update_t_item(self, increment):
        self.pbar.total += increment
        # self.pbar.refresh()

    @check_console
    def update_n_file(self, increment):
        self.n_file += increment
        self.pbar.unit = f"items {self.n_file}/{self.t_file}files"
        # self.pbar.refresh()

    @check_console
    def update(self, increment):
        self.pbar.unit = f"items {self.n_file}/{self.t_file}files"
        self.pbar.update(increment)


pbm = PbarManager()
