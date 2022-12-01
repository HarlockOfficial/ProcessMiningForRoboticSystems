import pm4py
import MyOperator
from pm4py.objects.process_tree.obj import Operator


def my_recursively_add_tree(parent_tree, tree, bpmn, initial_event, final_event, counts, rec_depth):
    from pm4py.objects.bpmn.obj import BPMN
    tree_childs = [child for child in tree.children]
    initial_connector = None
    final_connector = None

    if tree.operator is None:
        trans = tree
        if trans.label is None:
            bpmn, task, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_tau_task(bpmn, counts)
            bpmn.add_flow(BPMN.Flow(initial_event, task))
            bpmn.add_flow(BPMN.Flow(task, final_event))
            initial_connector = task
            final_connector = task
        else:
            bpmn, task, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_task(bpmn, counts,
                                                                                                 trans.label)
            bpmn.add_flow(BPMN.Flow(initial_event, task))
            bpmn.add_flow(BPMN.Flow(task, final_event))
            initial_connector = task
            final_connector = task

    elif tree.operator == Operator.XOR:
        bpmn, split_gateway, join_gateway, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_xor_gateway(
            bpmn, counts)
        for subtree in tree_childs:
            bpmn, counts, x, y = my_recursively_add_tree(tree, subtree, bpmn, split_gateway, join_gateway,
                                                         counts,
                                                         rec_depth + 1)
        bpmn.add_flow(BPMN.Flow(initial_event, split_gateway))
        bpmn.add_flow(BPMN.Flow(join_gateway, final_event))
        initial_connector = split_gateway
        final_connector = join_gateway

    elif tree.operator == Operator.PARALLEL:
        bpmn, split_gateway, join_gateway, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_parallel_gateway(
            bpmn, counts)
        for subtree in tree_childs:
            bpmn, counts, x, y = my_recursively_add_tree(tree, subtree, bpmn, split_gateway, join_gateway,
                                                         counts,
                                                         rec_depth + 1)
        bpmn.add_flow(BPMN.Flow(initial_event, split_gateway))
        bpmn.add_flow(BPMN.Flow(join_gateway, final_event))
        initial_connector = split_gateway
        final_connector = join_gateway

    elif tree.operator == Operator.OR:
        bpmn, split_gateway, join_gateway, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_inclusive_gateway(
            bpmn, counts)
        for subtree in tree_childs:
            bpmn, counts, x, y = my_recursively_add_tree(tree, subtree, bpmn, split_gateway, join_gateway,
                                                         counts,
                                                         rec_depth + 1)
        bpmn.add_flow(BPMN.Flow(initial_event, split_gateway))
        bpmn.add_flow(BPMN.Flow(join_gateway, final_event))
        initial_connector = split_gateway
        final_connector = join_gateway

    elif tree.operator == Operator.SEQUENCE:
        initial_intermediate_task = initial_event
        bpmn, final_intermediate_task, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_tau_task(
            bpmn, counts)
        for i in range(len(tree_childs)):
            bpmn, counts, initial_connect, final_connect = my_recursively_add_tree(tree, tree_childs[i], bpmn,
                                                                                   initial_intermediate_task,
                                                                                   final_intermediate_task, counts,
                                                                                   rec_depth + 1)
            initial_intermediate_task = final_connect
            if i == 0:
                initial_connector = initial_connect
            if i == len(tree_childs) - 2:
                final_intermediate_task = final_event
            else:
                bpmn, final_intermediate_task, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_tau_task(
                    bpmn, counts)
            final_connector = final_connect

    elif tree.operator == Operator.LOOP:
        if len(tree_childs) != 2:
            raise Exception("Loop doesn't have 2 childs")
        else:
            do = tree_childs[0]
            redo = tree_childs[1]
            bpmn, split, join, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_xor_gateway(bpmn,
                                                                                                               counts)
            bpmn, counts, i, y = my_recursively_add_tree(tree, do, bpmn, join, split, counts, rec_depth + 1)
            bpmn, counts, x, y = my_recursively_add_tree(tree, redo, bpmn, split, join, counts, rec_depth + 1)
            bpmn.add_flow(BPMN.Flow(initial_event, join))
            bpmn.add_flow(BPMN.Flow(split, final_event))
            initial_connector = join
            final_connector = split
    elif tree.operator == Operator.RECEIVE_MESSAGE:
        receive_message_node = tree_childs[len(tree_childs)-1]

        bpmn, task, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_task(bpmn, counts, label=receive_message_node.label)
        bpmn.add_flow(BPMN.Flow(initial_event, task))
        bpmn.add_flow(BPMN.Flow(task, final_event))
        receive_message_task = task
        for child in tree_childs:
            if child == receive_message_node:
                continue
            # add task
            task = BPMN.Task(name=child.label)
            bpmn.add_node(task)

            # add flow
            bpmn.add_flow(BPMN.Flow(task, receive_message_task))
        initial_connector = receive_message_task
        final_connector = receive_message_task
    elif tree.operator == Operator.SEND_MESSAGE:
        send_message_node = tree_childs[0]

        bpmn, task, counts = pm4py.objects.conversion.process_tree.variants.to_bpmn.add_task(bpmn, counts, label=send_message_node.label)
        bpmn.add_flow(BPMN.Flow(initial_event, task))
        bpmn.add_flow(BPMN.Flow(task, final_event))
        send_message_task = task
        for child in tree_childs:
            if child == send_message_node:
                continue
            # add task
            task = BPMN.Task(name=child.label)
            bpmn.add_node(task)

            # add flow
            bpmn.add_flow(BPMN.Flow(send_message_task, task))
        initial_connector = send_message_task
        final_connector = send_message_task
    return bpmn, counts, initial_connector, final_connector


pm4py.objects.conversion.process_tree.variants.to_bpmn.recursively_add_tree = my_recursively_add_tree
