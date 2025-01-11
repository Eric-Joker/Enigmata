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
from dataclasses import dataclass, field
from typing import Callable

from .obf_strs import OBFStrType


@dataclass
class EntityHandler:
    vd: set | tuple | Callable = field(default_factory=tuple)
    obf_set: OBFStrType = OBFStrType.OBFFILE
    dag_type: str = None
    dag_unique: bool = True

    def __bool__(self):
        return bool(self.vd or self.obf_set is not OBFStrType.OBFFILE)


@dataclass
class ProcessMapping:
    key: EntityHandler = field(default_factory=EntityHandler)
    value: EntityHandler = field(default_factory=EntityHandler)


def pm_factory(
    k_vd: set | Callable = (),
    k_type: OBFStrType = OBFStrType.OBFFILE,
    v_vd: set | Callable = (),
    v_type: OBFStrType = OBFStrType.OBFFILE,
    k_dag_type: str = None,
    k_dag_unique=True,
    v_dag_type: str = None,
    v_dag_unique=True,
):
    return ProcessMapping(
        EntityHandler(k_vd, k_type, k_dag_type, k_dag_unique),
        EntityHandler(v_vd, v_type, v_dag_type, v_dag_unique),
    )
