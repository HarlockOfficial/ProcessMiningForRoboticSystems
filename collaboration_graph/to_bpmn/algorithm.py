from typing import Union, Callable, Type, Tuple, List

import networkx
import pm4py
from pm4py.objects.bpmn.obj import BPMN

from collaboration_graph import CollaborationGraph, CollaborationGraphNode

import MyOperator
from pm4py.objects.process_tree.obj import Operator

from collaboration_graph.to_bpmn.data_structure import EventBasedGateway, ReceiveMessageActivity, SendMessageActivity


def find_node(node: CollaborationGraphNode, bpmn: BPMN) -> Union[BPMN.BPMNNode, None]:
    for bpmn_node in bpmn.get_nodes():
        if str(id(node)) == bpmn_node.get_id():
            return bpmn_node
    return None


def find_flow(source: BPMN.BPMNNode, target: BPMN.BPMNNode, bpmn: BPMN) -> Union[BPMN.Flow, None]:
    for flow in bpmn.get_flows():
        if flow.get_source() == source and flow.get_target() == target:
            return flow
    return None


def build_sequence(node: CollaborationGraphNode, parent: BPMN.BPMNNode, bpmn: BPMN):
    initial_parent = parent
    for child in node.children:
        first_node, last_node = recursive_create_bpmn(child, parent, bpmn)
        if last_node is None:
            last_node = first_node
        new_flow = BPMN.Flow(source=parent, target=first_node, id=str(id(parent) ** 32 + id(child)),
                             process=parent.process)
        bpmn.add_flow(new_flow)
        parent = last_node
    return initial_parent, parent


def recursive_create_bpmn(node: CollaborationGraphNode, parent: Union[BPMN.BPMNNode, None], bpmn: BPMN):
    if parent is None and not str(node.label).endswith("Start"):
        raise ValueError("The root node must be a start event")
    if str(node.label).startswith("Start") or str(node.label).endswith("Start"):
        new_node = BPMN.NormalStartEvent(id=str(id(node)), process=node.process)
    else:
        new_node = BPMN.Task(id=str(id(node)), name=node.label, process=node.process)
    node.children = sorted(node.children, key=lambda x: x.index)
    closing_node = None
    if node.operator is not None:
        if node.operator in (Operator.XOR, Operator.LOOP):
            new_node = BPMN.ExclusiveGateway(id=str(id(node)), gateway_direction=BPMN.Gateway.Direction.CONVERGING, process=node.process)
            closing_node = BPMN.ExclusiveGateway(id=str(id(node)**32), gateway_direction=BPMN.Gateway.Direction.CONVERGING, process=node.process)
            if node.operator is Operator.LOOP:
                new_flow = BPMN.Flow(source=closing_node, target=new_node,
                                     id=str(id(closing_node) ** 32 + id(new_node)), process=closing_node.process)
                bpmn.add_flow(new_flow)
                new_node, _ = build_sequence(node, new_node, bpmn)
        elif node.operator is Operator.SEQUENCE:
            return build_sequence(node, parent, bpmn)
        elif node.operator in (Operator.PARALLEL, Operator.INTERLEAVING):
            new_node = BPMN.ParallelGateway(id=str(id(node)), gateway_direction=BPMN.Gateway.Direction.CONVERGING, process=node.process)
            closing_node = BPMN.ParallelGateway(id=str(id(node)**32), gateway_direction=BPMN.Gateway.Direction.CONVERGING, process=node.process)
        elif node.operator is Operator.OR:
            new_node = BPMN.InclusiveGateway(id=str(id(node)), gateway_direction=BPMN.Gateway.Direction.CONVERGING, process=node.process)
            closing_node = BPMN.InclusiveGateway(id=str(id(node)**32), gateway_direction=BPMN.Gateway.Direction.CONVERGING, process=node.process)
        elif node.operator is Operator.RECEIVE_MESSAGE:
            raise NotImplementedError("Receive message can never be implemented")
        elif node.operator is Operator.SEND_MESSAGE:
            raise NotImplementedError("Send message can never be implemented")
        else:
            raise ValueError("Unknown operator")
    if parent is not None:
        bpmn.add_node(new_node)
    if closing_node is not None:
        bpmn.add_node(closing_node)
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
                    new_flow = BPMN.Flow(source=new_node, target=first_node, id=str(id(new_node) ** 32 + id(first_node)), process=new_node.process)
                    bpmn.add_flow(new_flow)
                if closing_node is not None:
                    if last_node != closing_node:
                        new_flow = BPMN.Flow(source=last_node, target=closing_node, id=str(id(last_node) ** 32 + id(closing_node)), process=last_node.process)
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
            new_flow = BPMN.MessageFlow(source=source, target=target, id=str(id(source) ** 32 + id(target)), process=source.process)
            bpmn.add_flow(new_flow)


def check_start_event(node: BPMN.BPMNNode) -> bool:
    if len(node.in_arcs) <= 1:
        return True
    for incoming_flow in node.in_arcs:
        if not isinstance(incoming_flow.source, BPMN.NormalStartEvent) and not isinstance(incoming_flow,
                                                                                          BPMN.MessageFlow):
            return True


def check_receive_message_activities(node: BPMN.BPMNNode) -> bool:
    if isinstance(node, BPMN.MessageStartEvent):
        return True
    for incoming_flow in node.in_arcs:
        if incoming_flow.source.get_process() != incoming_flow.target.get_process():
            return False
    return True


def check_event_based_gateway(node: BPMN.BPMNNode) -> bool:
    if len(node.out_arcs) <= 1:
        return True
    for outgoing_flow in node.out_arcs:
        if not isinstance(outgoing_flow.target, ReceiveMessageActivity):
            return True
    return not isinstance(node, BPMN.ExclusiveGateway) and not isinstance(node, BPMN.InclusiveGateway)


def check_send_message_activities(node: BPMN.BPMNNode) -> bool:
    if isinstance(node, BPMN.MessageStartEvent):
        return True
    for incoming_flow in node.out_arcs:
        if incoming_flow.source.get_process() != incoming_flow.target.get_process():
            return False
    return True


def create_nodes(bpmn: BPMN, selector_function: Callable[[BPMN.BPMNNode], bool], node_type: Type[BPMN.BPMNNode]):
    nodes_to_remove = []
    nodes_to_add = []
    flows_to_remove = []
    flows_to_add = []
    for node in bpmn.get_nodes():
        if selector_function(node):
            continue
        new_node = node_type(id=str(id(node) ** 32), name=node.name, process=node.process)
        nodes_to_add.append(new_node)
        for flow in node.in_arcs:
            flows_to_remove.append(flow)
            new_flow = BPMN.MessageFlow(source=flow.source, target=new_node, id=str(id(flow.source) ** 32 + id(new_node)), process=flow.get_process(), name=flow.get_name())
            flows_to_add.append(new_flow)
        for flow in node.out_arcs:
            flows_to_remove.append(flow)
            new_flow = BPMN.MessageFlow(source=new_node, target=flow.target, id=str(id(new_node) ** 32 + id(flow.target)), process=flow.get_process(), name=flow.get_name())
            flows_to_add.append(new_flow)
        nodes_to_remove.append(node)

    tmp_flows_to_remove = flows_to_remove
    for flow in tmp_flows_to_remove:
        if isinstance(flow.source, node_type):
            flows_to_remove.remove(flow)
            tmp_edge_list = flow.target.get_in_arcs()
            for edge in tmp_edge_list:
                if edge.source.get_name() == flow.source.get_name() and edge.source != flow.source:
                    flows_to_remove.append(edge)
        elif isinstance(flow.target, node_type):
            flows_to_remove.remove(flow)
            tmp_edge_list = flow.source.get_out_arcs()
            for edge in tmp_edge_list:
                if edge.target.get_name() == flow.target.get_name() and edge.target != flow.target:
                    flows_to_remove.append(edge)
    del tmp_flows_to_remove

    tmp_nodes_to_remove = nodes_to_remove
    for node in tmp_nodes_to_remove:
        if isinstance(node, node_type):
            nodes_to_remove.remove(node)
            tmp_nodes_list = bpmn.get_nodes()
            for tmp_node in tmp_nodes_list:
                if tmp_node.get_name() == node.get_name() and tmp_node != node:
                    nodes_to_remove.append(tmp_node)
    del tmp_nodes_to_remove

    flows_to_remove = list(set(flows_to_remove))
    nodes_to_remove = list(set(nodes_to_remove))
    nodes_to_add = list(set(nodes_to_add))
    flows_to_add = list(set(flows_to_add))

    for flow in flows_to_remove:
        bpmn.remove_flow(flow)
    for node in nodes_to_remove:
        bpmn.remove_node(node)
    for node in nodes_to_add:
        bpmn.add_node(node)
    for flow in flows_to_add:
        bpmn.add_flow(flow)


def remove_double_start_events(bpmn: BPMN):
    nodes_to_remove = []

    for node in bpmn.get_nodes():
        if isinstance(node, BPMN.NormalStartEvent):
            if len(node.out_arcs) == 1 and isinstance(node.out_arcs[0].target, BPMN.MessageStartEvent):
                nodes_to_remove.append(node)

    nodes_to_remove = list(set(nodes_to_remove))

    for node in nodes_to_remove:
        bpmn.remove_node(node)


def remove_nodes_without_outgoing_flows(bpmn: BPMN):
    nodes_to_remove = []
    flows_to_remove = []

    for node in bpmn.get_nodes():
        if node.get_process() == "Global":
            nodes_to_remove.append(node)
            flows_to_remove.extend(node.get_in_arcs())
            flows_to_remove.extend(node.get_out_arcs())

    nodes_to_remove = list(set(nodes_to_remove))
    flows_to_remove = list(set(flows_to_remove))

    for flow in flows_to_remove:
        bpmn.remove_flow(flow)
    for node in nodes_to_remove:
        bpmn.remove_node(node)


def find_clones(bpmn: BPMN) -> List[Tuple[BPMN.BPMNNode, BPMN.BPMNNode]]:
    lst = []
    for node in bpmn.get_nodes():
        for other_node in bpmn.get_nodes():
            if node.get_id() == other_node.get_id():
                continue
            if node.get_name() == other_node.get_name():
                lst.append((node, other_node))
    return lst


def find_orphan_edges(bpmn: BPMN) -> List[BPMN.MessageFlow]:
    lst = []
    for edge in bpmn.get_flows():
        if edge.source not in bpmn.get_nodes() or edge.target not in bpmn.get_nodes():
            lst.append(edge)
    return lst


def clean_up(bpmn: BPMN):
    clones_list = find_clones(bpmn)
    for clone in clones_list:
        if isinstance(clone[0], (SendMessageActivity, ReceiveMessageActivity, BPMN.MessageStartEvent)):
            bpmn.remove_node(clone[1])
        elif isinstance(clone[1], (SendMessageActivity, ReceiveMessageActivity, BPMN.MessageStartEvent)):
            bpmn.remove_node(clone[0])

    orphan_edges = find_orphan_edges(bpmn)
    for edge in orphan_edges:
        try:
            bpmn.remove_flow(edge)
        except networkx.exception.NetworkXError:
            pass


def my_convert_to_bpmn(graph: CollaborationGraph) -> BPMN:
    bpmn = BPMN()
    recursive_create_bpmn(graph.get_root(), None, bpmn)
    closing_nodes = list(bpmn.get_nodes())
    for node in bpmn.get_nodes():
        for flow in bpmn.get_flows():
            if flow.get_source() == node and node in closing_nodes:
                closing_nodes.remove(node)
    for node in closing_nodes:
        new_node = BPMN.EndEvent(process=node.process)
        bpmn.add_node(new_node)
        new_flow = BPMN.Flow(source=node, target=new_node, id=str(id(node) ** 32 + id(new_node)), process=node.process)
        bpmn.add_flow(new_flow)
    add_message_flows(graph, bpmn)
    create_nodes(bpmn, check_start_event, BPMN.MessageStartEvent)
    remove_double_start_events(bpmn)
    remove_nodes_without_outgoing_flows(bpmn)
    create_nodes(bpmn, check_receive_message_activities, ReceiveMessageActivity)
    create_nodes(bpmn, check_send_message_activities, SendMessageActivity)
    create_nodes(bpmn, check_event_based_gateway, EventBasedGateway)
    clean_up(bpmn)
    return bpmn


pm4py.convert.convert_to_bpmn = my_convert_to_bpmn
