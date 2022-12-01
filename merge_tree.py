from typing import List, Union

from pm4py.objects.process_tree.obj import ProcessTree
import MyOperator
from pm4py.objects.process_tree.obj import Operator


def __find_node_iterative(tree_node: ProcessTree, lst: list, operator: Operator, depth: int = 0):
    # using iterative, because recursive might be too heavy in case of large trees
    queue = [tree_node]
    while len(queue) > 0:
        node = queue.pop(0)
        if node not in lst:
            if node.operator == operator:
                lst.append(node)
            queue.extend(node.children)


def find_send_node_list(tree) -> List[ProcessTree]:
    list = []
    __find_node_iterative(tree, list, Operator.SEND_MESSAGE)
    return list


def find_receive_node_list(tree) -> List[ProcessTree]:
    list = []
    __find_node_iterative(tree, list, Operator.RECEIVE_MESSAGE)
    return list


def merge_two_trees(tree1: ProcessTree, tree2: ProcessTree) -> ProcessTree:
    send_node_list = find_send_node_list(tree1)
    receive_node_list = find_receive_node_list(tree2)
    for send_node in send_node_list:
        true_sender_node = send_node.children[0]
        for receive_node in receive_node_list:
            senders_of_receive_node = receive_node.children[:-1]
            if true_sender_node in senders_of_receive_node:
                send_node.children.append(receive_node.children[-1])
    tree1.children.append(tree2)
    return tree1


def merge_tree(tree_list: List[ProcessTree]) -> Union[ProcessTree, None]:
    if len(tree_list) <= 0:
        return None
    final_tree = ProcessTree(operator=Operator.PARALLEL, children=[tree_list[0]])

    for tree in tree_list[1:]:
        final_tree = merge_two_trees(final_tree, tree)

    return final_tree