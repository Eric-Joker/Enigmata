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
from enum import Enum, auto

from . import BiMap


class OBFStrType(Enum):
    OBFFILE = auto()
    AC = "animation_controllers"
    ACS = "animation_controller_states"
    ANIMATION = "animations"
    MATERIAL = "materials"
    MODEL = "models"
    BONE = "bones"
    PARTICLE = "particles"
    RC = "render_controllers"
    RCARRAY = "render_controller_arrays"
    ANIMATIONINDEX = "animation_indexes"
    MATERIALINDEX = "material_indexes"
    MODELINDEX = "model_indexes"
    PARTICLEINDEX = "particle_indexes"
    TEXTUREINDEX = "texture_indexes"
    MOLANGVAR = "molang_variables"
    UICONTROL = "ui_controls"
    UIVARIABLE = "ui_variables"
    UIBINDIND = "ui_bindings"
    LOCALIZATION = "localizations"
    UIMERGE = "ui_merge_controls"
    FILENAME = "filenames"

    @property
    def bi_map(self):
        return obf_strs_dict[self]


obf_strs_dict = {e: BiMap() for e in OBFStrType}
