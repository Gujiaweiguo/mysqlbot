from dataclasses import dataclass, field
from typing import Any, cast

from common.utils.tree_utils import build_tree_generic


@dataclass
class Node:
    id: str | None
    pid: str | None
    children: list["Node"] = field(default_factory=list)


class TestBuildTreeGeneric:
    def test_builds_nested_tree(self) -> None:
        root = Node(id="1", pid=None)
        child = Node(id="2", pid="1")
        grandchild = Node(id="3", pid="2")

        tree = build_tree_generic(cast(Any, [root, child, grandchild]))

        assert tree == [root]
        assert root.children == [child]
        assert child.children == [grandchild]

    def test_ignores_missing_parent(self) -> None:
        orphan = Node(id="2", pid="missing")

        tree = build_tree_generic(cast(Any, [orphan]))

        assert tree == []
        assert orphan.children == []

    def test_supports_custom_root_pid(self) -> None:
        root = Node(id="10", pid="root")

        tree = build_tree_generic(cast(Any, [root]), root_pid="root")

        assert tree == [root]
