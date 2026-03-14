from typing import Any, Protocol, TypeVar


class ITreeNode(Protocol):
    id: str | None
    pid: str | None
    children: list["ITreeNode"]


T = TypeVar("T", bound=ITreeNode)


def build_tree_generic(nodes: list[T], root_pid: Any = None) -> list[T]:
    node_dict: dict[str, T] = {node.id: node for node in nodes if node.id is not None}
    tree: list[T] = []

    for node in nodes:
        if node.pid == root_pid:
            tree.append(node)
        elif node.pid in node_dict:
            node_dict[node.pid].children.append(node)

    return tree
