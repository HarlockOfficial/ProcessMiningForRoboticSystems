import copy
from typing import Union, Tuple

from pm4py.objects.process_tree.obj import ProcessTree


class CollaborationGraphNode(object):
    def __init__(self, process: str = None, label: str = None, node: ProcessTree = None, index: int = -1):
        self.label = label
        if node is not None:
            self.operator = node.operator
            self.label = node.label
        else:
            self.operator = None
        self.incoming_edges = []
        self.outgoing_edges = []
        self.parent = []
        self.children = []
        self.index = index
        self.process = process

    def __copy__(self):
        new_node = CollaborationGraphNode()
        new_node.label = self.label
        new_node.operator = self.operator
        new_node.index = self.index
        new_node.process = self.process
        return new_node

    def __deepcopy__(self, memodict={}):
        new_node = CollaborationGraphNode()
        new_node.label = copy.copy(self.label)
        new_node.operator = copy.copy(self.operator)
        new_node.index = copy.copy(self.index)
        new_node.process = copy.copy(self.process)
        return new_node

    def __eq__(self, other):
        return self.label == other.label and self.operator == other.operator and self.process == other.process

    def __hash__(self):
        return hash(self.label) + hash(self.operator) ** 64 + hash(self.process) ** 128

    def __get_repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.index) + " " + self.label # if self.operator is None else self.operator.name

    def get_name(self):
        return str(self.index) + " " + self.label


class CollaborationGraph(object):
    def __init__(self):
        self.nodes = []
        self.edges = []

    def __copy__(self):
        new_graph = CollaborationGraph()
        new_graph.nodes = copy.copy(self.nodes)
        new_graph.edges = copy.copy(self.edges)
        return new_graph

    def __deepcopy__(self, memodict={}):
        new_graph = CollaborationGraph()
        new_graph.nodes = copy.deepcopy(self.nodes)
        new_graph.edges = copy.deepcopy(self.edges)
        return new_graph

    def __eq__(self, other):
        for node in self.nodes:
            if node not in other.nodes:
                return False
        for edge in self.edges:
            if edge not in other.edges:
                return False
        for node in other.nodes:
            if node not in self.nodes:
                return False
        for edge in other.edges:
            if edge not in self.edges:
                return False
        return True

    def __hash__(self):
        hash_val = 0
        for index, node in enumerate(self.nodes):
            hash_val += hash(node) * (index + 1)
        for index, edge in enumerate(self.edges):
            hash_val += hash(edge) * (index + 1)
        return hash_val

    def get_node(self, node: Union[ProcessTree, str, CollaborationGraphNode]) -> CollaborationGraphNode:
        if isinstance(node, ProcessTree) or isinstance(node, CollaborationGraphNode):
            for my_node in self.nodes:
                if node.label is None and node.operator is not None and node.operator == my_node.operator:
                    return my_node
                elif my_node.label == node.label:
                    return my_node
            raise Exception('Node not found')
        elif isinstance(node, str):
            for my_node in self.nodes:
                if my_node.label == node:
                    return my_node
            for my_node in self.nodes:
                if my_node.operator is not None and my_node.operator.name == node:
                    return my_node
            raise Exception('Node not found')
        raise Exception('Node not valid')

    def __get__repr__(self):
        return self.__str__()

    def __str__(self):
        string = "nodes:\n["
        for node in self.nodes:
            string += str(node) + ", "
        string += "]\nedges:\n"
        for edge in self.edges:
            string += '(' + str(edge[0]) + " -> " + str(edge[1]) + ")\n"
        return string

    def add_node(self, node: CollaborationGraphNode):
        self.nodes.append(node)

    def add_edge(self, node_1: CollaborationGraphNode = None, node_2: CollaborationGraphNode = None,
                 edge: Tuple[CollaborationGraphNode, CollaborationGraphNode] = None):
        node_1, node_2 = self.__get_nodes_from_edge(node_1, node_2, edge)
        node_1.outgoing_edges.append(node_2)
        node_2.incoming_edges.append(node_1)
        node_1.children.append(node_2)
        node_2.parent.append(node_1)
        self.edges.append((node_1, node_2))

    def get_graph(self):
        import networkx as nx
        graph = nx.DiGraph()
        graph.add_nodes_from(self.nodes)
        graph.add_edges_from(self.edges)
        return graph

    def get_successors(self, node: CollaborationGraphNode):
        node = self.get_node(node)
        return node.outgoing_edges

    def remove_edge(self, node_1: CollaborationGraphNode = None, node_2: CollaborationGraphNode = None,
                    edge: Tuple[CollaborationGraphNode, CollaborationGraphNode] = None):
        node_1, node_2 = self.__get_nodes_from_edge(node_1, node_2, edge)
        node_1.outgoing_edges.remove(node_2)
        node_2.incoming_edges.remove(node_1)
        node_1.children.remove(node_2)
        node_2.parent.remove(node_1)
        self.edges.remove((node_1, node_2))

    def __get_nodes_from_edge(self, node_1: Union[CollaborationGraphNode],
                              node_2: Union[CollaborationGraphNode],
                              edge: Tuple[CollaborationGraphNode, CollaborationGraphNode]):
        if node_1 is not None and node_2 is not None:
            node_1 = self.get_node(node_1)
            node_2 = self.get_node(node_2)
        elif edge is not None:
            node_1 = self.get_node(edge[0])
            node_2 = self.get_node(edge[1])
        else:
            raise Exception("Invalid params")
        return node_1, node_2

    def get_root(self) -> CollaborationGraphNode:
        node = self.nodes[0]
        while len(node.incoming_edges) > 0:
            node = node.incoming_edges[0]
        return node
