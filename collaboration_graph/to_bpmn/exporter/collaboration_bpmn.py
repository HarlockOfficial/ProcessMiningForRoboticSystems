import uuid
import xml.etree.ElementTree as ElementTree
from typing import Dict

from pm4py.objects.bpmn.obj import BPMN
from pm4py.util import constants

from collaboration_graph.to_bpmn.data_structure import EventBasedGateway, ReceiveMessageActivity, SendMessageActivity


def apply(bpmn_graph, target_path, _=None):
    """
    Exports the BPMN diagram to a file

    Parameters
    -------------
    bpmn_graph
        BPMN diagram
    target_path
        Target path
    _
        Possible parameters of the algorithm
    """
    xml_string = get_xml_string(bpmn_graph)
    f = open(target_path, "wb")
    f.write(xml_string)
    f.close()


def add_participants(definitions: ElementTree.SubElement, process_set: set):
    """
    Adds the participants to the collaboration

    Parameters
    -------------
    definitions
        ElementTree.SubElement element
    process_set
        Set of processes
    """
    for participant in process_set:
        participant_element = ElementTree.SubElement(definitions, "bpmn:participant")
        participant_element.set("id", "Participant_" + str(uuid.uuid4()))
        participant_element.set("processRef", "Process_" + participant)
        participant_element.set("name", participant)


def add_message_flows(graph: BPMN, definitions: ElementTree.SubElement, nodes_map: Dict[str, Dict[int, str]], flows_map: Dict[int, Dict[int, str]]):
    """
    Adds the message flows to the collaboration

    Parameters
    -------------
    graph
        BPMN diagram
    definitions
        ElementTree.SubElement element
    nodes_map
        Dictionary that maps the nodes to the nodes id
    flows_map
        Dictionary that maps the flows to the flows id
    """
    for edge in graph.get_flows():
        source = edge.source
        target = edge.target
        if source.process == target.process:
            continue
        message_flow_id = "MessageFlow_" + str(uuid.uuid4())

        if source.id not in flows_map.keys():
            flows_map[source.id] = dict()

        flows_map[source.id][target.id] = message_flow_id

        source_id = nodes_map[source.process][source.id]
        target_id = nodes_map[target.process][target.id]

        message_flow = ElementTree.SubElement(definitions, "bpmn:messageFlow")

        message_flow.set("id", message_flow_id)
        message_flow.set("sourceRef", source_id)
        message_flow.set("targetRef", target_id)
        if edge.source.name is not None:
            message_flow.set("name", edge.source.name)


def add_processes(graph: BPMN, definitions: ElementTree.SubElement, process_set: set, nodes_map: Dict[str, Dict[int, str]], flows_map: Dict[int, Dict[int, str]]):
    """
    Adds the processes to the collaboration

    Parameters
    -------------
    graph
        BPMN diagram
    definitions
        ElementTree.SubElement element
    process_set
        Set of processes
    nodes_map
        Dictionary that maps the nodes to the nodes id
    flows_map
        Dictionary that maps the flows to the flows id
    """
    process_process = dict()
    for process_name in process_set:
        p = ElementTree.SubElement(definitions, "bpmn:process")
        p.set("id", "Process_" + process_name)
        p.set("isClosed", "false")
        p.set("isExecutable", "false")
        p.set("processType", "None")
        process_process[process_name] = p

    task_map = dict()
    for node in graph.get_nodes():
        process = process_process[node.process]

        task_id = "Activity_" + str(node.id)
        task = ElementTree.SubElement(process, "bpmn:task")

        if isinstance(node, BPMN.StartEvent):
            is_interrupting = "true" if node.get_isInterrupting() else "false"
            parallel_multiple = "true" if node.get_parallelMultiple() else "false"
            task = ElementTree.SubElement(process, "bpmn:startEvent")
            task.set("isInterrupting", is_interrupting)
            task.set("parallelMultiple", parallel_multiple)
            task_id = "StartEvent_" + str(node.id)
        elif isinstance(node, BPMN.EndEvent):
            task = ElementTree.SubElement(process, "bpmn:endEvent")
            task_id = "Event_" + str(node.id)
        elif isinstance(node, BPMN.IntermediateCatchEvent):
            task = ElementTree.SubElement(process, "bpmn:intermediateCatchEvent")
        elif isinstance(node, BPMN.IntermediateThrowEvent):
            task = ElementTree.SubElement(process, "bpmn:intermediateThrowEvent")
        elif isinstance(node, BPMN.BoundaryEvent):
            task = ElementTree.SubElement(process, "bpmn:boundaryEvent")
        elif isinstance(node, ReceiveMessageActivity):
            task = ElementTree.SubElement(process, "bpmn:receiveTask")
            task_id = "Activity_" + str(node.id)
        elif isinstance(node, SendMessageActivity):
            task = ElementTree.SubElement(process, "bpmn:sendTask")
            task_id = "Activity_" + str(node.id)
        elif isinstance(node, BPMN.Activity):
            task_id = "Activity_" + str(node.id)
        elif isinstance(node, BPMN.Task):
            task_id = "Task_" + str(node.id)
        elif isinstance(node, BPMN.SubProcess):
            task = ElementTree.SubElement(process, "bpmn:subProcess")
        elif isinstance(node, EventBasedGateway):
            task = ElementTree.SubElement(process, "bpmn:eventBasedGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
            task_id = "Gateway_" + str(node.id)
        elif isinstance(node, BPMN.ExclusiveGateway):
            task = ElementTree.SubElement(process, "bpmn:exclusiveGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
            task_id = "ExclusiveGateway_" + str(node.id)
        elif isinstance(node, BPMN.ParallelGateway):
            task = ElementTree.SubElement(process, "bpmn:parallelGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
            task_id = "ParallelGateway_" + str(node.id)
        elif isinstance(node, BPMN.InclusiveGateway):
            task = ElementTree.SubElement(process, "bpmn:inclusiveGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
            task_id = "InclusiveGateway_" + str(node.id)
        else:
            raise Exception("Unexpected node type.")

        task.set("id", task_id)
        if node.name is not None:
            task.set("name", node.name)
        else:
            task.set("name", "")

        if node.process not in nodes_map.keys():
            nodes_map[node.process] = dict()

        nodes_map[node.process][node.id] = task_id
        task_map[node.id] = task

    for flow in graph.get_flows():
        source = flow.get_source()
        target = flow.get_target()
        if source.process != target.process:
            continue
        process = process_process[source.process]

        flow_id = "SequenceFlow_" + str(uuid.uuid4())

        if source.id not in flows_map.keys():
            flows_map[source.id] = dict()

        if target.id not in flows_map.keys():
            flows_map[target.id] = dict()

        flows_map[source.id][target.id] = flow_id

        source_id = nodes_map[source.process][source.id]
        target_id = nodes_map[target.process][target.id]

        flow_xml = ElementTree.SubElement(process, "bpmn:sequenceFlow")
        flow_xml.set("id", flow_id)
        flow_xml.set("sourceRef", source_id)
        flow_xml.set("targetRef", target_id)
        if flow.get_source().name is not None:
            flow_xml.set("name", flow.get_source().name)

    for node in graph.get_nodes():
        task = task_map[node.id]
        for sender_node_id in flows_map.keys():
            for receiver_node_id in flows_map[sender_node_id].keys():
                if receiver_node_id == node.id:
                    flow_id = flows_map[sender_node_id][receiver_node_id]
                    arc_xml = ElementTree.SubElement(task, "bpmn:incoming")
                    arc_xml.text = flow_id

        for out_node_id in flows_map[node.id]:
            flow_id = flows_map[node.id][out_node_id]
            arc_xml = ElementTree.SubElement(task, "bpmn:outgoing")
            arc_xml.text = flow_id


def add_diagram(graph: BPMN, process_plane: ElementTree.SubElement, nodes_map: Dict[str, Dict[int, str]], flows_map: Dict[int, Dict[int, str]]):
    for node in graph.get_nodes():
        node_shape = ElementTree.SubElement(process_plane, "bpmndi:BPMNShape")
        node_id = nodes_map[node.process][node.id]
        node_shape.set("bpmnElement", node_id)
        node_shape.set("id", "BPMNShape_" + node_id + "_shape")

        node_shape_layout = ElementTree.SubElement(node_shape, "dc:Bounds")
        node_shape_layout.set("height", str(node.get_height()))
        node_shape_layout.set("width", str(node.get_width()))
        node_shape_layout.set("x", str(node.get_x()))
        node_shape_layout.set("y", str(node.get_y()))

    for flow in graph.get_flows():
        source = flow.source
        target = flow.target
        flow_id = flows_map[source.id][target.id]
        flow_shape = ElementTree.SubElement(process_plane, "bpmndi:BPMNEdge")
        flow_shape.set("bpmnElement", flow_id)
        flow_shape.set("id", flow_id + "_edge")

        for x, y in flow.get_waypoints():
            waypoint = ElementTree.SubElement(flow_shape, "di:waypoint")
            waypoint.set("x", str(x))
            waypoint.set("y", str(y))


def get_xml_string(bpmn_graph, _=None):
    from xml.dom import minidom

    definitions = ElementTree.Element("bpmn:definitions")
    definitions.set("xmlns:bpmn", "http://www.omg.org/spec/BPMN/20100524/MODEL")
    definitions.set("xmlns:bpmndi", "http://www.omg.org/spec/BPMN/20100524/DI")
    definitions.set("xmlns:omgdc", "http://www.omg.org/spec/DD/20100524/DC")
    definitions.set("xmlns:dc", "http://www.omg.org/spec/DD/20100524/DC")
    definitions.set("xmlns:omgdi", "http://www.omg.org/spec/DD/20100524/DI")
    definitions.set("xmlns:di", "http://www.omg.org/spec/DD/20100524/DI")
    definitions.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    definitions.set("targetNamespace", "http://bpmn.io/schema/bpmn")
    definitions.set("typeLanguage", "http://www.w3.org/2001/XMLSchema")
    definitions.set("expressionLanguage", "http://www.w3.org/1999/XPath")
    definitions.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")

    flows_map = dict()
    nodes_map = dict()
    process_set = set()
    for node in bpmn_graph.get_nodes():
        process_set.add(node.process)

    collaboration = ElementTree.SubElement(definitions, "bpmn:collaboration")
    collaboration_id = "Collaboration_" + str(uuid.uuid4())
    collaboration.set("id", collaboration_id)
    collaboration.set("name", "collaboration")

    add_participants(collaboration, process_set)

    add_processes(bpmn_graph, definitions, process_set, nodes_map, flows_map)
    add_message_flows(bpmn_graph, collaboration, nodes_map, flows_map)

    diagram = ElementTree.SubElement(definitions, "bpmndi:BPMNDiagram")
    diagram.set("id", "BPMNDiagram_" + str(uuid.uuid4()))
    diagram.set("name", "diagram")

    plane = ElementTree.SubElement(diagram, "bpmndi:BPMNPlane")
    plane.set("bpmnElement", collaboration_id)
    plane.set("id", "BPMNPlane_" + str(uuid.uuid4()) + "_plane")

    add_diagram(bpmn_graph, plane, nodes_map, flows_map)

    return minidom.parseString(ElementTree.tostring(definitions)).toprettyxml(encoding=constants.DEFAULT_ENCODING)
