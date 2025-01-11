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
class BiMap:
    def __init__(self):
        self.forward = {}
        self.backward = {}

    def __getitem__(self, key):
        return self.forward[key]

    def __setitem__(self, key, value):
        if value == self.forward.get(key):
            return
        if value in self.backward:
            raise ValueError("Value cannot be an existing one.")
        if key in self.forward:
            self.replace_value(self.forward[key], value)
        else:
            self.forward[key] = value
            self.backward[value] = key

    def __contains__(self, item):
        return item in self.forward

    def __len__(self):
        return len(self.forward)

    def items(self):
        return self.forward.items()

    def get(self, *args, **kwargs):
        return self.forward.get(*args, **kwargs)

    def replace_value(self, old_value, new_value):
        key = self.backward.pop(old_value, None)
        if key is not None:
            self.forward[key] = new_value
            self.backward[new_value] = key
        else:
            self.__setitem__(old_value, new_value)
