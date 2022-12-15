import uuid

import MyOperator
from pm4py.objects.process_tree.obj import Operator

from typing import List, Tuple

from pm4py.objects.process_tree.obj import ProcessTree

from collaboration_graph.data_structure import CollaborationGraph, CollaborationGraphNode


def to_collaboration_graph(node: ProcessTree, child_index: int = -1, parent: CollaborationGraphNode = None,
                           graph: CollaborationGraph = CollaborationGraph(), to_add_edges: List[Tuple[str, str]] = []) \
        -> Tuple[CollaborationGraph, List[Tuple[str, str]]]:
    if parent is None:
        start_node = CollaborationGraphNode(label="Start" + uuid.uuid4().hex, index=0)
        graph.add_node(start_node)
        child_index = 1
    else:
        start_node = parent
    if node.operator in [Operator.SEQUENCE, Operator.XOR, Operator.PARALLEL, Operator.LOOP, Operator.OR,
                         Operator.INTERLEAVING]:
        try:
            graph_node = graph.get_node(node.label)
            graph_node.index = child_index
        except Exception:
            node.label = node.operator.name + uuid.uuid4().hex
            graph_node = CollaborationGraphNode(node=node, index=child_index)
            graph.add_node(graph_node)
        graph.add_edge(start_node, graph_node)
        for index, child in enumerate(node.children):
            graph, new_lst = to_collaboration_graph(child, child_index=index, parent=graph_node, graph=graph,
                                                    to_add_edges=to_add_edges)
            to_add_edges.extend(new_lst)
    elif node.operator == Operator.RECEIVE_MESSAGE:
        graph_node = node.children[-1]
        graph_node.parent = node.parent
        graph, new_lst = to_collaboration_graph(graph_node, child_index=child_index, parent=graph_node.parent,
                                                graph=graph, to_add_edges=to_add_edges)
        to_add_edges.extend(new_lst)
        graph_node = graph.get_node(graph_node)
        for child in node.children[:-1]:
            try:
                tmp_graph_node = graph.get_node(child.label)
                graph.add_node(tmp_graph_node)
                graph.add_edge(tmp_graph_node, graph_node)
            except Exception:
                to_add_edges.append((child.label, graph_node.label))
    elif node.operator == Operator.SEND_MESSAGE:
        graph_node = node.children[0]
        graph_node.parent = node.parent
        graph, new_lst = to_collaboration_graph(graph_node, child_index=child_index, parent=graph_node.parent,
                                                graph=graph, to_add_edges=to_add_edges)
        to_add_edges.extend(new_lst)
        graph_node = graph.get_node(graph_node)
        for child in node.children[1:]:
            try:
                tmp_graph_node = graph.get_node(child.label)
                graph.add_node(tmp_graph_node)
                graph.add_edge(graph_node, tmp_graph_node)
            except Exception:
                to_add_edges.append((graph_node.label, child.label))
    elif node.operator is None and node.label is not None:
        graph_node = CollaborationGraphNode(node=node, index=child_index)
        if start_node.label != graph_node.label:
            graph.add_node(graph_node)
            graph.add_edge(start_node, graph_node)
    return graph, to_add_edges


def fix_child_nodes_indexes(graph: CollaborationGraph) -> CollaborationGraph:
    def fix_child_nodes_indexes_helper(node: CollaborationGraphNode, _graph: CollaborationGraph) -> CollaborationGraph:
        for _index, _child in enumerate(node.children):
            _child.index = _index
            _graph = fix_child_nodes_indexes_helper(_child, _graph)
        return _graph

    root = graph.get_root()
    root.index = 0
    for index, child in enumerate(root.children):
        child.index = index
        graph = fix_child_nodes_indexes_helper(child, graph)
    return graph


def merge_collaboration_trees(collaboration_tree_list: List[CollaborationGraph]) -> CollaborationGraph:
    collaboration_graph = CollaborationGraph()
    roots = []
    for collaboration_tree in collaboration_tree_list:
        root = collaboration_tree.get_root()
        roots.append(root)
        for node in collaboration_tree.nodes:
            try:
                collaboration_graph.get_node(node)
            except Exception:
                collaboration_graph.add_node(node)
        for edge in collaboration_tree.edges:
            collaboration_graph.add_edge(edge=edge)
    global_root = CollaborationGraphNode(label="GlobalStart")
    global_root.operator = Operator.PARALLEL
    collaboration_graph.add_node(global_root)
    for root in roots:
        collaboration_graph.add_edge(global_root, root)
    return collaboration_graph


def apply_collaboration_graph(process_tree_list: List[ProcessTree]) -> CollaborationGraph:
    collaboration_tree_list = []
    all_edges_list = []
    for process_tree in process_tree_list:
        # import collaboration_graph.view_graph
        # collaboration_graph.view_graph.pm4py.view_process_tree(process_tree)
        graph, to_add_edges = to_collaboration_graph(process_tree, graph=CollaborationGraph(), to_add_edges=[])
        all_edges_list.extend(to_add_edges)
        graph = fix_child_nodes_indexes(graph)
        collaboration_tree_list.append(graph)
    collaboration_graph_ = merge_collaboration_trees(collaboration_tree_list)
    for edge in all_edges_list:
        node_0 = collaboration_graph_.get_node(edge[0])
        node_1 = collaboration_graph_.get_node(edge[1])
        if (node_0, node_1) not in collaboration_graph_.edges:
            collaboration_graph_.add_edge(node_0, node_1)
    return collaboration_graph_
