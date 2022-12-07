import copy
import hashlib
import tempfile
from typing import Optional, Dict, Union, Any

import pm4py
from graphviz import Digraph
from pydotplus import graphviz

import MyOperator
from pm4py.objects.process_tree.obj import Operator
from pm4py.util import exec_utils
from pm4py.visualization.process_tree.variants.wo_decoration import get_color, Parameters
from pm4py.utils import constants

from collaboration_graph import CollaborationGraph

pm4py.visualization.process_tree.variants.wo_decoration.operators_mapping = {"->": "seq", "X": "xor", "+": "and",
                                                                             "*": "xor loop", "O": "or",
                                                                             "<>": "interleaving",
                                                                             "receive_message": "receive_message",
                                                                             "send_message": "send_message"}


def my_apply(tree: CollaborationGraph,
             parameters: Optional[Dict[Union[str, Parameters], Any]] = None) -> graphviz.Graph:
    """
    Obtain a Process Tree representation through GraphViz

    Parameters
    -----------
    tree
        Process tree
    parameters
        Possible parameters of the algorithm

    Returns
    -----------
    gviz
        GraphViz object
    """
    if parameters is None:
        parameters = {}

    filename = tempfile.NamedTemporaryFile(suffix='.gv')

    bgcolor = exec_utils.get_param_value(Parameters.BGCOLOR, parameters, constants.DEFAULT_BGCOLOR)

    viz = Digraph("pt", filename=filename.name, engine='dot', graph_attr={'bgcolor': bgcolor})
    viz.attr('node', shape='ellipse', fixedsize='false')

    image_format = exec_utils.get_param_value(Parameters.FORMAT, parameters, "png")
    color_map = exec_utils.get_param_value(Parameters.COLOR_MAP, parameters, {})

    enable_deepcopy = exec_utils.get_param_value(Parameters.ENABLE_DEEPCOPY, parameters, True)

    if enable_deepcopy:
        # since the process tree object needs to be sorted in the visualization, make a deepcopy of it before
        # proceeding
        tree = copy.deepcopy(tree)
        my_tree_sort(tree)

    my_repr_tree_2(tree, viz, color_map, parameters)

    viz.attr(overlap='false')
    viz.attr(splines='false')
    viz.format = image_format

    return viz


# TODO fix this, it has to work with CollaborationGraph, aka list of nodes and edges
def my_tree_sort(tree):
    """
    Sort a tree in such way that the order of the nodes
    in AND/XOR children is always the same.
    This is a recursive function

    Parameters
    --------------
    tree
        Process tree
    """
    tree.labels_hash_sum = 0
    for child in tree.children:
        my_tree_sort(child)
        tree.labels_hash_sum += child.labels_hash_sum
    if tree.label is not None:
        # this assures that among different executions, the same string gets always the same hash
        this_hash = int(hashlib.md5(str(tree.label).encode(constants.DEFAULT_ENCODING)).hexdigest(), 16)
        tree.labels_hash_sum += this_hash
    if tree.operator is Operator.PARALLEL or tree.operator is Operator.XOR:
        tree.children = sorted(tree.children, key=lambda x: x.labels_hash_sum)


# TODO fix this, it has to work with CollaborationGraph, aka list of nodes and edges
def my_repr_tree_2(tree, viz, color_map, parameters):
    font_size = exec_utils.get_param_value(Parameters.FONT_SIZE, parameters, 15)
    font_size = str(font_size)

    this_node_id = str(id(tree))

    if tree.operator is None:
        if tree.label is None:
            viz.node(this_node_id, "tau", style='filled', fillcolor='black', shape='point', width="0.075",
                     fontsize=font_size)
        else:
            node_color = get_color(tree, color_map)
            viz.node(this_node_id, str(tree.label), color=node_color, fontcolor=node_color, fontsize=font_size)
    else:
        node_color = get_color(tree, color_map)
        viz.node(this_node_id,
                 pm4py.visualization.process_tree.variants.wo_decoration.operators_mapping[str(tree.operator)],
                 color=node_color, fontcolor=node_color, fontsize=font_size)

        for child in tree.children:
            my_repr_tree_2(child, viz, color_map, parameters)

    if tree.parent is not None:
        viz.edge(str(id(tree.parent)), this_node_id, dirType='none')


import pm4py.objects.process_tree.utils.generic

pm4py.objects.process_tree.utils.generic.tree_sort = my_tree_sort
pm4py.visualization.process_tree.variants.wo_decoration.apply = my_apply
pm4py.visualization.process_tree.variants.wo_decoration.repr_tree_2 = my_repr_tree_2
