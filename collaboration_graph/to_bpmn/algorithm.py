from typing import Union

import pm4py
from pm4py.objects.bpmn.obj import BPMN

from collaboration_graph import CollaborationGraph, CollaborationGraphNode

import MyOperator
from pm4py.objects.process_tree.obj import Operator


def find_node(node: CollaborationGraphNode, bpmn: BPMN) -> Union[BPMN.BPMNNode, None]:
    for bpmn_node in bpmn.get_nodes():
        if id(node) == bpmn_node.get_id():
            return bpmn_node
    return None


def find_flow(source: BPMN.BPMNNode, target: BPMN.BPMNNode, bpmn: BPMN) -> Union[BPMN.Flow, None]:
    for flow in bpmn.get_flows():
        if flow.get_source() == source and flow.get_target() == target:
            return flow
    return None


def recursive_create_bpmn(node: CollaborationGraphNode, parent: Union[BPMN.BPMNNode, None], bpmn: BPMN):
    if parent is None and not str(node.label).endswith("Start"):
        raise ValueError("The root node must be a start event")
    if str(node.label).startswith("Start") or str(node.label).endswith("Start"):
        new_node = BPMN.StartEvent(id=id(node))
    else:
        new_node = BPMN.Task(id=id(node), name=node.label)
    node.children = sorted(node.children, key=lambda x: x.index)
    closing_node = None
    if node.operator is not None:
        if node.operator is Operator.XOR:
            new_node = BPMN.ExclusiveGateway(id=id(node), gateway_direction=BPMN.Gateway.Direction.CONVERGING)
            closing_node = BPMN.ExclusiveGateway(id=id(node)**32, gateway_direction=BPMN.Gateway.Direction.CONVERGING)
        elif node.operator is Operator.SEQUENCE:
            initial_parent = parent
            for child in node.children:
                first_node, last_node = recursive_create_bpmn(child, parent, bpmn)
                if last_node is None:
                    last_node = first_node
                new_flow = BPMN.Flow(source=parent, target=first_node, id=id(id(parent) ** 32 + id(child)))
                bpmn.add_flow(new_flow)
                parent = last_node
            return initial_parent, parent
        elif node.operator is Operator.PARALLEL:
            new_node = BPMN.ParallelGateway(id=id(node), gateway_direction=BPMN.Gateway.Direction.CONVERGING)
            closing_node = BPMN.ParallelGateway(id=id(node)**32, gateway_direction=BPMN.Gateway.Direction.CONVERGING)
        elif node.operator is Operator.LOOP:
            # TODO check which operator to use
            raise NotImplementedError("Loop operator is not implemented yet")
        elif node.operator is Operator.OR:
            new_node = BPMN.InclusiveGateway(id=id(node), gateway_direction=BPMN.Gateway.Direction.CONVERGING)
            closing_node = BPMN.InclusiveGateway(id=id(node)**32, gateway_direction=BPMN.Gateway.Direction.CONVERGING)
        elif node.operator is Operator.INTERLEAVING:
            # TODO check which operator to use
            raise NotImplementedError("Loop operator is not implemented yet")
        elif node.operator is Operator.RECEIVE_MESSAGE:
            raise NotImplementedError("Receive message not implemented")
        elif node.operator is Operator.SEND_MESSAGE:
            raise NotImplementedError("Send message not implemented")
        else:
            raise ValueError("Unknown operator")
    if parent is not None:
        bpmn.add_node(new_node)
    if node.operator is not None or isinstance(new_node, BPMN.StartEvent):
        for child in node.children:
            first_node = find_node(child, bpmn)
            last_node = None
            if first_node is None:
                first_node, last_node = recursive_create_bpmn(child, new_node, bpmn)
            if last_node is None:
                last_node = first_node
            if parent is not None:
                if new_node != first_node:
                    new_flow = BPMN.Flow(source=new_node, target=first_node, id=id(id(new_node) ** 32 + id(first_node)))
                    bpmn.add_flow(new_flow)
                if closing_node is not None:
                    if last_node != closing_node:
                        new_flow = BPMN.Flow(source=last_node, target=closing_node, id=id(id(last_node) ** 32 + id(closing_node)))
                        bpmn.add_flow(new_flow)
    return new_node, closing_node


def add_message_flows(graph: CollaborationGraph, bpmn: BPMN):
    for edge in graph.edges:
        source = find_node(edge[0], bpmn)
        target = find_node(edge[1], bpmn)
        if source is None or target is None:
            if edge[0].operator is not None or edge[1].operator is not None:
                continue
            raise ValueError("Node not found")
        if source == target:
            continue
        if find_flow(source, target, bpmn) is None:
            new_flow = BPMN.MessageFlow(source=source, target=target, id=id(id(source) ** 32 + id(target)))
            bpmn.add_flow(new_flow)


def my_convert_to_bpmn(graph: CollaborationGraph) -> BPMN:
    bpmn = BPMN()
    recursive_create_bpmn(graph.get_root(), None, bpmn)
    closing_nodes = list(bpmn.get_nodes())
    for node in bpmn.get_nodes():
        for flow in bpmn.get_flows():
            if flow.get_source() == node and node in closing_nodes:
                closing_nodes.remove(node)
    for node in closing_nodes:
        new_node = BPMN.EndEvent()
        bpmn.add_node(new_node)
        new_flow = BPMN.Flow(source=node, target=new_node, id=id(id(node) ** 32 + id(new_node)))
        bpmn.add_flow(new_flow)
    add_message_flows(graph, bpmn)
    return bpmn


pm4py.convert.convert_to_bpmn = my_convert_to_bpmn
