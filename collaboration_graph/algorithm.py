import uuid

from pm4py.objects.bpmn.obj import BPMN

import MyOperator
from pm4py.objects.process_tree.obj import Operator

from typing import List

from pm4py.objects.process_tree.obj import ProcessTree

from CollaborationGraph.data_structure import CollaborationGraph, CollaborationGraphNode


def to_collaboration_graph(node: ProcessTree, graph: CollaborationGraph = CollaborationGraph(), depth: int = 0) -> CollaborationGraph:
    if node.parent is None:
        start_node = CollaborationGraphNode(label="Start" + uuid.uuid4().hex)
        graph.add_node(start_node)
    else:
        start_node = graph.get_node(node.parent)
    if node.operator in [Operator.SEQUENCE, Operator.XOR, Operator.PARALLEL, Operator.LOOP, Operator.OR, Operator.INTERLEAVING]:
        node.label = node.operator.name + uuid.uuid4().hex
        graph_node = CollaborationGraphNode(node=node)
        graph.add_node(graph_node)
        graph.add_edge(start_node, graph_node)
        for child in node.children:
            graph = to_collaboration_graph(child, graph, depth=depth + 1)
    elif node.operator == Operator.RECEIVE_MESSAGE:
        graph_node = node.children[-1]
        graph_node.parent = node.parent
        graph = to_collaboration_graph(graph_node, graph, depth=depth + 1)
        graph_node = graph.get_node(graph_node)
        for child in node.children[:-1]:
            try:
                tmp_graph_node = graph.get_node(child.label)
            except Exception:
                tmp_graph_node = CollaborationGraphNode(node=child)
            graph.add_node(tmp_graph_node)
            graph.add_edge(tmp_graph_node, graph_node)
    elif node.operator == Operator.SEND_MESSAGE:
        graph_node = node.children[0]
        graph_node.parent = node.parent
        graph = to_collaboration_graph(graph_node, graph, depth=depth + 1)
        graph_node = graph.get_node(graph_node)
        for child in node.children[1:]:
            try:
                tmp_graph_node = graph.get_node(child.label)
            except Exception:
                tmp_graph_node = CollaborationGraphNode(node=child)
            graph.add_node(tmp_graph_node)
            graph.add_edge(graph_node, tmp_graph_node)
    elif node.operator is None and node.label is not None:
        graph_node = CollaborationGraphNode(node=node)
        graph.add_node(graph_node)
        graph.add_edge(start_node, graph_node)
    if depth == 0:
        end_node = CollaborationGraphNode(label="End" + uuid.uuid4().hex)
        graph.add_node(end_node)
        for node in graph.nodes:
            if len(graph.get_successors(node)) == 0:
                graph.add_edge(node, end_node)
    return graph


def merge_collaboration_trees(collaboration_tree_list: List[CollaborationGraph]) -> CollaborationGraph:
    collaboration_graph = CollaborationGraph()
    for collaboration_tree in collaboration_tree_list:
        for node in collaboration_tree.nodes:
            try:
                collaboration_graph.get_node(node)
            except Exception:
                collaboration_graph.add_node(node)
        for edge in collaboration_tree.edges:
            collaboration_graph.add_edge(edge=edge)
    return collaboration_graph


def apply_collaboration_graph(process_tree_list: List[ProcessTree]) -> CollaborationGraph:
    collaboration_tree_list = []
    for process_tree in process_tree_list:
        graph = to_collaboration_graph(process_tree, CollaborationGraph())
        collaboration_tree_list.append(graph)
    return merge_collaboration_trees(collaboration_tree_list)
