import copy
import uuid

from lxml import etree
from pm4py.objects.process_tree.obj import Operator, ProcessTree
from pm4py.util import constants
from collaboration_graph import CollaborationGraph


def my_get_list_nodes_from_tree(_: CollaborationGraph, parameters) -> list:
    """
    Get list of nodes from a process tree

    Parameters
    -------------
    _
        Process tree
    parameters
        Parameters of the algorithm
    Returns
    -------------
    list_nodes
        List of nodes
    """
    if parameters is None:
        return []
    tmp_tree = parameters['graph']
    list_nodes = []

    for node in tmp_tree.nodes:
        list_nodes.append(node)
    return list_nodes


def export_ptree_tree(tree, parameters=None):
    """
    Exports the XML tree from a process tree

    Parameters
    -----------------
    tree
        Process tree
    parameters
        Parameters of the algorithm

    Returns
    -----------------
    xml_tree
        XML tree object
    """
    tree = copy.deepcopy(tree)
    if parameters is None:
        parameters = {}

    nodes = my_get_list_nodes_from_tree(tree, parameters=parameters)
    nodes_dict = {(id(x), x): str(uuid.uuid4()) for x in nodes}

    # make sure that in the exporting, loops have 3 children
    # (for ProM compatibility)
    # just add a skip as third child
    for node in nodes:
        if node.operator == Operator.LOOP and len(node.children) < 3:
            third_children = ProcessTree(operator=None, label=None)
            third_children.parent = node
            node.children.append(third_children)
            nodes_dict[(id(third_children), third_children)] = str(uuid.uuid4())

    # repeat twice (structure has changed)
    nodes = my_get_list_nodes_from_tree(tree, parameters=parameters)
    nodes_dict = {(id(x), x): str(uuid.uuid4()) for x in nodes}

    root = etree.Element("ptml")
    processtree = etree.SubElement(root, "processTree")
    processtree.set("name", str(uuid.uuid4()))
    tree_root_key = list(filter(lambda x: x[1] == tree, nodes_dict.keys()))[0]
    processtree.set("root", nodes_dict[tree_root_key])
    processtree.set("id", str(uuid.uuid4()))

    for node in nodes:
        nk = nodes_dict[(id(node), node)]
        child = None
        if node.operator is None:
            if node.label is None:
                child = etree.SubElement(processtree, "automaticTask")
                child.set("name", "")
            else:
                child = etree.SubElement(processtree, "manualTask")
                child.set("name", node.label)
        else:
            if node.operator is Operator.SEQUENCE:
                child = etree.SubElement(processtree, "sequence")
            elif node.operator is Operator.XOR:
                child = etree.SubElement(processtree, "xor")
            elif node.operator is Operator.PARALLEL:
                child = etree.SubElement(processtree, "and")
            elif node.operator is Operator.OR:
                child = etree.SubElement(processtree, "or")
            elif node.operator is Operator.LOOP:
                child = etree.SubElement(processtree, "xorLoop")
            child.set("name", "")
        child.set("id", nk)

    for edge_source, edge_target in parameters['graph'].edges:
        child = etree.SubElement(processtree, "parentsNode")
        source_key = list(filter(lambda x: x[1] == edge_source, nodes_dict.keys()))[0]
        target_key = list(filter(lambda x: x[1] == edge_target, nodes_dict.keys()))[0]
        child.set("sourceId", nodes_dict[source_key])
        child.set("targetId", nodes_dict[target_key])
        child.set("id", str(uuid.uuid4()))

    tree = etree.ElementTree(root)
    return tree


def apply(tree, output_path, parameters=None):
    """
    Exports the process tree to a XML (.PTML) file

    Parameters
    ----------------
    tree
        Process tree
    output_path
        Output path
    parameters
        Parameters
    """
    if parameters is None:
        parameters = {}

    # gets the XML tree
    tree = export_ptree_tree(tree, parameters=parameters)

    # exports the tree to a file
    tree.write(output_path, pretty_print=True, xml_declaration=True, encoding=constants.DEFAULT_ENCODING)

    return tree
