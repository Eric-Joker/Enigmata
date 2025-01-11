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
import rustworkx as rx


class DAG(rx.PyDiGraph):
    label_map = {}

    def __getstate__(self):
        state = super().__getstate__().copy()
        state["label_map"] = self.label_map
        return state

    def __setstate__(self, state):
        self.label_map = state["label_map"]
        super().__setstate__(state)

    def add_node(self, node_type, node_value, is_unique=True):
        if is_unique and node_value in self.label_map.get(node_type, {}):
            return
        self.label_map.setdefault(node_type, {}).setdefault(node_value, []).append(
            super().add_node(f"{node_type}#{node_value}")
        )

    def add_edge(self, from_type, from_value, to_type, to_value):
        if self.has_edge(self.label_map[from_type][from_value][-1], self.label_map[to_type][to_value][-1]):
            return
        if any(x == to_value for x in self.sppf(from_type, from_value, to_type)):
            self.remove_node(self.label_map[to_type][to_value].pop(-1))
            return
        super().add_edge(self.label_map[from_type][from_value][-1], self.label_map[to_type][to_value][-1], None)

    def siif(self, node, to_type):  # successors with filter; in => indice; out => indice
        return (s for s in self.successor_indices(node) if self[s].partition("#")[0] == to_type)

    def sipf(self, node, to_type):  # successors with filter; in => indice; out => payload
        return (splited[2] for s in self.successors(node) if (splited := s.partition("#"))[0] == to_type)

    def sppf(self, from_type, from_value, to_type):  # successors with filter; in => payload; out => payload
        if (indices := self.label_map[from_type].get(from_value)) is None:
            return ()
        return (splited[2] for s in self.successors(indices[-1]) if (splited := s.partition("#"))[0] == to_type)

    def ppif(self, from_type, from_value, to_type):  # predecessors; in => payload; out => indice
        if (indices := self.label_map[from_type].get(from_value)) is None:
            return ()
        return (v for v in self.predecessor_indices(indices[-1]) if self[v].partition("#")[0] == to_type)

    def test(self):
        import matplotlib.pyplot as plt
        from rustworkx.visualization import mpl_draw

        with open("test.txt", "w", encoding="utf-8") as f:
            f.write(str(self.nodes()))
        # mpl_draw(self, labels=lambda n: n, with_labels=True, font_size=10, node_size=50)
        # plt.show()
