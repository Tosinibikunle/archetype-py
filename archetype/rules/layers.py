"""Built-in layering rule for enforcing top-down architectural dependencies."""

from __future__ import annotations

import archetype.dsl.query as query_module
from archetype.analysis.models import Violation
from archetype.analysis.pattern import find_matching_nodes


class LayerOrderRule:
    """Rule object that validates import directions across declared layers."""

    def __init__(self, layer_patterns: list[str]) -> None:
        self.layer_patterns = layer_patterns

    def are_ordered(self) -> None:
        """Assert that lower layers do not import upper layers."""
        graph = query_module._current_graph
        if graph is None:
            raise RuntimeError(
                "Archetype has not loaded a project yet.\n\n"
                "This usually means one of the following:\n"
                "  - You are calling imports() or module() outside of a @rule function\n"
                "  - You are running architecture.py directly with python architecture.py\n"
                "    instead of through archetype check or pytest\n\n"
                "To fix this, run your rules using one of these commands:\n"
                "  archetype check .\n"
                "  pytest\n\n"
                "If you need to load a project programmatically use:\n"
                "  from archetype import load_project\n"
                "  from pathlib import Path\n"
                "  load_project(Path(\".\"))"
            )

        violations: list[Violation] = []
        all_nodes = list(graph.nodes)
        for upper_index, upper_pattern in enumerate(self.layer_patterns):
            for lower_pattern in self.layer_patterns[upper_index + 1 :]:
                lower_nodes = find_matching_nodes(lower_pattern, all_nodes)
                upper_nodes = set(find_matching_nodes(upper_pattern, all_nodes))
                if not lower_nodes:
                    query_module._record_unmatched_pattern(
                        lower_pattern,
                        all_nodes,
                        role="Layer",
                    )
                if not upper_nodes:
                    query_module._record_unmatched_pattern(
                        upper_pattern,
                        all_nodes,
                        role="Layer",
                    )

                for source in lower_nodes:
                    for target in graph.successors(source):
                        if target in upper_nodes:
                            violation_file, violation_line = (
                                query_module._edge_violation_location(
                                    graph,
                                    source,
                                    target,
                                )
                            )
                            violations.append(
                                Violation(
                                    module=source,
                                    file=violation_file,
                                    line=violation_line,
                                    message=(
                                        f"Layering violation (upward dependency): lower layer "
                                        f"'{lower_pattern}' module '{source}' imports upper layer "
                                        f"'{upper_pattern}' module '{target}'."
                                    ),
                                )
                            )

        if violations:
            exc = AssertionError(
                f"Layer ordering violated by {len(violations)} upward import(s)."
            )
            setattr(exc, "violations", violations)
            raise exc


def layers(layer_patterns: list[str]) -> LayerOrderRule:
    """Create a layer-order rule for modules listed top-to-bottom."""
    return LayerOrderRule(layer_patterns)
