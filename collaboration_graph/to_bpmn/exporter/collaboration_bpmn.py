import uuid
import xml.etree.ElementTree as ElementTree

from pm4py.objects.bpmn.obj import BPMN
from pm4py.util import constants


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


def add_participants(graph: BPMN, definitions: ElementTree.SubElement):
    """
    Adds the participants to the collaboration

    Parameters
    -------------
    graph
        BPMN diagram
    definitions
        ElementTree.SubElement element
    """
    participants = set()
    for node in graph.get_nodes():
        participants.add(node.process)
    for participant in participants:
        participant_element = ElementTree.SubElement(definitions, "bpmn:participant")
        participant_element.set("id", "Participant_" + str(uuid.uuid4()))
        participant_element.set("processRef", "Process_" + participant)
        participant_element.set("name", participant)


def add_message_flows(graph: BPMN, definitions: ElementTree.SubElement):
    """
    Adds the message flows to the collaboration

    Parameters
    -------------
    graph
        BPMN diagram
    definitions
        ElementTree.SubElement element
    """
    for edge in graph.get_flows():
        if edge.source.process == edge.target.process:
            continue
        message_flow = ElementTree.SubElement(definitions, "bpmn:messageFlow")
        message_flow.set("id", "MessageFlow_" + str(uuid.uuid4()))
        message_flow.set("name", edge.source.name)
        message_flow.set("sourceRef", "Activity_" + str(edge.source.id))
        message_flow.set("targetRef", "Activity_" + str(edge.target.id))
        if edge.source.name is not None:
            message_flow.set("name", edge.source.name)


def add_processes(graph: BPMN, definitions: ElementTree.SubElement):
    """
    Adds the processes to the collaboration

    Parameters
    -------------
    graph
        BPMN diagram
    definitions
        ElementTree.SubElement element
    """
    all_processes = set()
    for node in graph.get_nodes():
        all_processes.add(node.process)
    process_process = dict()
    for process_name in all_processes:
        p = ElementTree.SubElement(definitions, "bpmn:process")
        p.set("id", "Process_" + process_name)
        p.set("isClosed", "false")
        p.set("isExecutable", "false")
        p.set("processType", "None")
        process_process[process_name] = p

    for node in graph.get_nodes():
        process = process_process[node.process]

        if isinstance(node, BPMN.StartEvent):
            is_interrupting = "true" if node.get_isInterrupting() else "false"
            parallel_multiple = "true" if node.get_parallelMultiple() else "false"
            task = ElementTree.SubElement(process, "bpmn:startEvent")
            task.set("isInterrupting", is_interrupting)
            task.set("parallelMultiple", parallel_multiple)
        elif isinstance(node, BPMN.EndEvent):
            task = ElementTree.SubElement(process, "bpmn:endEvent")
        elif isinstance(node, BPMN.IntermediateCatchEvent):
            task = ElementTree.SubElement(process, "bpmn:intermediateCatchEvent")
        elif isinstance(node, BPMN.IntermediateThrowEvent):
            task = ElementTree.SubElement(process, "bpmn:intermediateThrowEvent")
        elif isinstance(node, BPMN.BoundaryEvent):
            task = ElementTree.SubElement(process, "bpmn:boundaryEvent")
        elif isinstance(node, BPMN.Task):
            task = ElementTree.SubElement(process, "bpmn:task")
        elif isinstance(node, BPMN.SubProcess):
            task = ElementTree.SubElement(process, "bpmn:subProcess")
        elif isinstance(node, BPMN.ExclusiveGateway):
            task = ElementTree.SubElement(process, "bpmn:exclusiveGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
        elif isinstance(node, BPMN.ParallelGateway):
            task = ElementTree.SubElement(process, "bpmn:parallelGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
        elif isinstance(node, BPMN.InclusiveGateway):
            task = ElementTree.SubElement(process, "bpmn:inclusiveGateway")
            task.set("gatewayDirection", node.get_gateway_direction().value.lower())
        else:
            raise Exception("Unexpected node type.")

        task.set("id", "Activity_" + str(node.id))
        if node.name is not None:
            task.set("name", node.name)
        else:
            task.set("name", "")

        for in_arc in node.get_in_arcs():
            arc_xml = ElementTree.SubElement(task, "bpmn:incoming")
            arc_xml.text = "Flow_" + str(in_arc.get_id())

        for out_arc in node.get_out_arcs():
            arc_xml = ElementTree.SubElement(task, "bpmn:outgoing")
            arc_xml.text = "Flow_" + str(out_arc.get_id())

    for flow in graph.get_flows():
        process = process_process[flow.get_process()]

        source = flow.get_source()
        target = flow.get_target()
        flow_xml = ElementTree.SubElement(process, "bpmn:sequenceFlow")
        flow_xml.set("id", "Flow_" + str(flow.get_id()))
        flow_xml.set("sourceRef", "Activity_" + str(source.id))
        flow_xml.set("targetRef", "Activity_" + str(target.id))
        if flow.get_source().name is not None:
            flow_xml.set("name", flow.get_source().name)


def add_diagram(graph: BPMN, diagram: ElementTree.SubElement, collaboration_id: str):
    all_processes = set()
    for node in graph.get_nodes():
        all_processes.add(node.process)

    process_planes = dict()
    for process in all_processes:
        plane = ElementTree.SubElement(diagram, "bpmndi:BPMNPlane")
        plane.set("bpmnElement", collaboration_id)
        plane.set("id", "BPMNPlane_" + process + "_plane")
        process_planes[process] = plane

    for node in graph.get_nodes():
        process = node.get_process()

        node_shape = ElementTree.SubElement(process_planes[process], "bpmndi:BPMNShape")
        node_shape.set("bpmnElement", "Activity_" + str(node.id))
        node_shape.set("id", "BPMNShape_" + str(node.id) + "_shape")

        node_shape_layout = ElementTree.SubElement(node_shape, "dc:Bounds")
        node_shape_layout.set("height", str(node.get_height()))
        node_shape_layout.set("width", str(node.get_width()))
        node_shape_layout.set("x", str(node.get_x()))
        node_shape_layout.set("y", str(node.get_y()))

    for flow in graph.get_flows():
        process = flow.get_process()

        flow_shape = ElementTree.SubElement(process_planes[process], "bpmndi:BPMNEdge")
        flow_shape.set("bpmnElement", "Flow_" + str(flow.get_id()))
        flow_shape.set("id", "Flow_" + str(flow.get_id()) + "_edge")

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

    diagram = ElementTree.SubElement(definitions, "bpmndi:BPMNDiagram")
    diagram.set("id", "BPMNDiagram_" + str(uuid.uuid4()))
    diagram.set("name", "diagram")

    collaboration = ElementTree.SubElement(definitions, "bpmn:collaboration")
    collaboration_id = "Collaboration_" + str(uuid.uuid4())
    collaboration.set("id", collaboration_id)
    collaboration.set("name", "collaboration")

    add_participants(bpmn_graph, collaboration)
    add_message_flows(bpmn_graph, collaboration)
    add_processes(bpmn_graph, definitions)
    add_diagram(bpmn_graph, diagram, collaboration_id)

    return minidom.parseString(ElementTree.tostring(definitions)).toprettyxml(encoding=constants.DEFAULT_ENCODING)
