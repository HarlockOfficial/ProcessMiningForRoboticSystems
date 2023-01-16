import tempfile
import uuid
from collections import Counter
from copy import deepcopy

from pm4py.objects.bpmn.layout.variants.graphviz import EndpointDirection, get_right_edge_coord, get_left_edge_coord, \
    get_top_edge_coord, get_bottom_edge_coord, Parameters
from pm4py.objects.bpmn.obj import BPMN
from pm4py.objects.bpmn.util.sorting import get_sorted_nodes_edges
from pm4py.util import exec_utils


def apply(bpmn_graph: BPMN) -> BPMN:
    from graphviz import Digraph
    from pm4py.visualization.common import save as gsave

    nodes = bpmn_graph.get_nodes()
    flows = bpmn_graph.get_flows()

    filename_gv = tempfile.NamedTemporaryFile(suffix='.gv')
    filename_gv.close()
    filename_svg = tempfile.NamedTemporaryFile(suffix='.svg')
    filename_svg.close()
    viz = Digraph(bpmn_graph.get_name(), filename=filename_gv.name, engine='dot')
    viz.format = "svg"
    viz.graph_attr['rankdir'] = 'LR'

    graph_nodes, graph_edges = get_sorted_nodes_edges(bpmn_graph)

    nodes_dict = {}
    inv_nodes_dict = {}
    subgraphs = dict()
    sub_graph_edges = dict()
    other_edges = []

    for n in graph_nodes:
        node_uuid = str(uuid.uuid4()).replace("-", "")
        nodes_dict[n] = node_uuid
        inv_nodes_dict[node_uuid] = n
        viz.node(node_uuid, label=" ", shape="box")

    for tup in graph_edges:
        if tup[0].process == tup[1].process:
            if tup[0].process not in sub_graph_edges:
                sub_graph_edges[tup[0].process] = []
            sub_graph_edges[tup[0].process].append((nodes_dict[tup[0]], nodes_dict[tup[1]]))
        else:
            other_edges.append((nodes_dict[tup[0]], nodes_dict[tup[1]]))

    for node in graph_nodes:
        if node.process not in subgraphs.keys():
            with viz.subgraph(name='cluster_' + node.process) as sub:
                sub.attr(label=node.process)
                sub.edges(sub_graph_edges[node.process])
                subgraphs[node.process] = sub

    for edge in other_edges:
        viz.edge(edge[0], edge[1])

    gsave.save(viz, filename_svg.name)

    nodes_pos = {}

    content = open(filename_svg.name, "r").read()
    viz_nodes = content.split("class=\"node\">")[1:]
    for node in viz_nodes:
        this_id = node.split("<title>")[1].split("</title>")[0]
        points = node.split("points=\"")[1].split("\"")[0]
        nodes_pos[inv_nodes_dict[this_id]] = points

    endpoints_wh = exec_utils.get_param_value(Parameters.TASK_WH, {}, 30)
    task_wh = exec_utils.get_param_value(Parameters.TASK_WH, {}, 60)

    # add node positions to BPMN nodes
    for n in graph_nodes:
        node_pos = nodes_pos[n].split(" ")[0].split(",")

        pos_x = float(node_pos[0])
        pos_y = float(node_pos[1])
        n.set_x(pos_x)
        n.set_y(pos_y)
        if isinstance(n, BPMN.Task):
            this_width = min(round(2 * task_wh), round(2 * (len(n.get_name()) + 7) * task_wh / 22.0))
            n.set_width(this_width)
            n.set_height(task_wh)
        elif isinstance(n, BPMN.StartEvent) or isinstance(n, BPMN.EndEvent):
            n.set_width(endpoints_wh)
            n.set_height(endpoints_wh)
        else:
            n.set_width(task_wh)
            n.set_height(task_wh)

    max_x = max(1, max(abs(node.get_x()) for node in nodes))
    max_y = max(1, max(abs(node.get_y()) for node in nodes))
    different_x = len(set(node.get_x() for node in nodes))
    different_y = len(set(node.get_y() for node in nodes))

    stretch_fact_x = 2.5 * 1.25 * 1920.0 / max_x
    stretch_fact_y = 2.5 * 1080.0 / max_y

    for node in nodes:
        node.set_x(round(node.get_x() * stretch_fact_x))
        node.set_y(round(node.get_y() * stretch_fact_y))

    outgoing_edges = dict()
    ingoing_edges = dict()
    sources_dict = dict()
    targets_dict = dict()

    for flow in flows:
        source = flow.get_source()
        target = flow.get_target()

        x_src = source.get_x()
        x_trg = target.get_x()
        y_src = source.get_y()
        y_trg = target.get_y()

        sources_dict[(x_src, y_src)] = source
        targets_dict[(x_trg, y_trg)] = target

        diff_x = abs(x_trg - x_src)
        diff_y = abs(y_src - y_trg)

        if not (x_src, y_src) in outgoing_edges:
            outgoing_edges[(x_src, y_src)] = {}
        outgoing_edges[(x_src, y_src)][(x_trg, y_trg)] = {EndpointDirection.RIGHT: 0.0, EndpointDirection.LEFT: 0.0,
                                                          EndpointDirection.TOP: 0.0, EndpointDirection.BOTTOM: 0.0}
        if not (x_trg, y_trg) in ingoing_edges:
            ingoing_edges[(x_trg, y_trg)] = {}
        ingoing_edges[(x_trg, y_trg)][(x_src, y_src)] = {EndpointDirection.RIGHT: 0.0, EndpointDirection.LEFT: 0.0,
                                                         EndpointDirection.TOP: 0.0, EndpointDirection.BOTTOM: 0.0}

        if x_trg > x_src:
            outgoing_edges[(x_src, y_src)][(x_trg, y_trg)][EndpointDirection.RIGHT] = diff_x / (diff_x + diff_y)
            ingoing_edges[(x_trg, y_trg)][(x_src, y_src)][EndpointDirection.LEFT] = diff_x / (diff_x + diff_y)
        else:
            outgoing_edges[(x_src, y_src)][(x_trg, y_trg)][EndpointDirection.LEFT] = diff_x / (diff_x + diff_y)
            ingoing_edges[(x_trg, y_trg)][(x_src, y_src)][EndpointDirection.RIGHT] = diff_x / (diff_x + diff_y)

        if y_src > y_trg:
            outgoing_edges[(x_src, y_src)][(x_trg, y_trg)][EndpointDirection.TOP] = diff_y / (diff_x + diff_y)
            ingoing_edges[(x_trg, y_trg)][(x_src, y_src)][EndpointDirection.BOTTOM] = diff_y / (diff_x + diff_y)
        else:
            outgoing_edges[(x_src, y_src)][(x_trg, y_trg)][EndpointDirection.BOTTOM] = diff_y / (diff_x + diff_y)
            ingoing_edges[(x_trg, y_trg)][(x_src, y_src)][EndpointDirection.TOP] = diff_y / (diff_x + diff_y)

    # normalization
    outgoing_edges0 = deepcopy(outgoing_edges)
    ingoing_edges0 = deepcopy(ingoing_edges)

    for p1 in outgoing_edges:
        sum_right = 0.0
        sum_left = 0.0
        sum_top = 0.0
        sum_bottom = 0.0
        for p2 in outgoing_edges[p1]:
            sum_right += outgoing_edges0[p1][p2][EndpointDirection.RIGHT]
            sum_left += outgoing_edges0[p1][p2][EndpointDirection.LEFT]
            sum_top += outgoing_edges0[p1][p2][EndpointDirection.TOP]
            sum_bottom += outgoing_edges0[p1][p2][EndpointDirection.BOTTOM]
        if p1 in ingoing_edges:
            for p2 in ingoing_edges[p1]:
                sum_right += ingoing_edges0[p1][p2][EndpointDirection.RIGHT]
                sum_left += ingoing_edges0[p1][p2][EndpointDirection.LEFT]
                sum_top += ingoing_edges0[p1][p2][EndpointDirection.TOP]
                sum_bottom += ingoing_edges0[p1][p2][EndpointDirection.BOTTOM]
        for p2 in outgoing_edges[p1]:
            if sum_right > 0:
                outgoing_edges[p1][p2][EndpointDirection.RIGHT] = outgoing_edges[p1][p2][
                                                                      EndpointDirection.RIGHT] ** 2 / sum_right
            if sum_left > 0:
                outgoing_edges[p1][p2][EndpointDirection.LEFT] = outgoing_edges[p1][p2][
                                                                     EndpointDirection.LEFT] ** 2 / sum_left
            if sum_top > 0:
                outgoing_edges[p1][p2][EndpointDirection.TOP] = outgoing_edges[p1][p2][
                                                                    EndpointDirection.TOP] ** 2 / sum_top
            if sum_bottom > 0:
                outgoing_edges[p1][p2][EndpointDirection.BOTTOM] = outgoing_edges[p1][p2][
                                                                       EndpointDirection.BOTTOM] ** 2 / sum_bottom
    for p1 in ingoing_edges:
        sum_right = 0.0
        sum_left = 0.0
        sum_top = 0.0
        sum_bottom = 0.0
        for p2 in ingoing_edges[p1]:
            sum_right += ingoing_edges0[p1][p2][EndpointDirection.RIGHT]
            sum_left += ingoing_edges0[p1][p2][EndpointDirection.LEFT]
            sum_top += ingoing_edges0[p1][p2][EndpointDirection.TOP]
            sum_bottom += ingoing_edges0[p1][p2][EndpointDirection.BOTTOM]
        if p1 in outgoing_edges:
            for p2 in outgoing_edges[p1]:
                sum_right += outgoing_edges0[p1][p2][EndpointDirection.RIGHT]
                sum_left += outgoing_edges0[p1][p2][EndpointDirection.LEFT]
                sum_top += outgoing_edges0[p1][p2][EndpointDirection.TOP]
                sum_bottom += outgoing_edges0[p1][p2][EndpointDirection.BOTTOM]
        for p2 in ingoing_edges[p1]:
            if sum_right > 0:
                ingoing_edges[p1][p2][EndpointDirection.RIGHT] = ingoing_edges[p1][p2][
                                                                     EndpointDirection.RIGHT] ** 2 / sum_right
            if sum_left > 0:
                ingoing_edges[p1][p2][EndpointDirection.LEFT] = ingoing_edges[p1][p2][
                                                                    EndpointDirection.LEFT] ** 2 / sum_left
            if sum_top > 0:
                ingoing_edges[p1][p2][EndpointDirection.TOP] = ingoing_edges[p1][p2][
                                                                   EndpointDirection.TOP] ** 2 / sum_top
            if sum_bottom > 0:
                ingoing_edges[p1][p2][EndpointDirection.BOTTOM] = ingoing_edges[p1][p2][
                                                                      EndpointDirection.BOTTOM] ** 2 / sum_bottom

    # keep best direction
    for p1 in outgoing_edges:
        for p2 in outgoing_edges[p1]:
            vals = sorted([(x, y) for x, y in outgoing_edges[p1][p2].items()], key=lambda x: x[1], reverse=True)
            outgoing_edges[p1][p2] = vals[0][0]
    for p1 in ingoing_edges:
        for p2 in ingoing_edges[p1]:
            vals = sorted([(x, y) for x, y in ingoing_edges[p1][p2].items()], key=lambda x: x[1], reverse=True)
            ingoing_edges[p1][p2] = vals[0][0]

    total_counter = dict()
    partial_counter = dict()
    for p1 in outgoing_edges:
        if p1 not in total_counter:
            total_counter[p1] = Counter()
        for p2 in outgoing_edges[p1]:
            dir = outgoing_edges[p1][p2]
            total_counter[p1][dir] += 1
    for p1 in ingoing_edges:
        if p1 not in total_counter:
            total_counter[p1] = Counter()
        for p2 in ingoing_edges[p1]:
            dir = ingoing_edges[p1][p2]
            total_counter[p1][dir] += 1

    outgoing_edges_dirs = deepcopy(outgoing_edges)
    ingoing_edges_dirs = deepcopy(ingoing_edges)

    # decide exiting/entering point for edges
    for p1 in outgoing_edges:
        node = sources_dict[p1]
        if p1 not in partial_counter:
            partial_counter[p1] = Counter()
        sorted_outgoing_edges = sorted(outgoing_edges[p1], key=lambda x: x, reverse=False)
        for p2 in sorted_outgoing_edges:
            dir = outgoing_edges[p1][p2]
            partial_counter[p1][dir] += 1
            if dir == EndpointDirection.RIGHT:
                outgoing_edges[p1][p2] = get_right_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
            elif dir == EndpointDirection.LEFT:
                outgoing_edges[p1][p2] = get_left_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
            elif dir == EndpointDirection.TOP:
                outgoing_edges[p1][p2] = get_top_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
            elif dir == EndpointDirection.BOTTOM:
                outgoing_edges[p1][p2] = get_bottom_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
    for p1 in ingoing_edges:
        node = targets_dict[p1]
        if p1 not in partial_counter:
            partial_counter[p1] = Counter()
        sorted_ingoing_edges = sorted(ingoing_edges[p1], key=lambda x: x, reverse=False)
        for p2 in sorted_ingoing_edges:
            dir = ingoing_edges[p1][p2]
            partial_counter[p1][dir] += 1
            if dir == EndpointDirection.RIGHT:
                ingoing_edges[p1][p2] = get_right_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
            elif dir == EndpointDirection.LEFT:
                ingoing_edges[p1][p2] = get_left_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
            elif dir == EndpointDirection.TOP:
                ingoing_edges[p1][p2] = get_top_edge_coord(node, p1, partial_counter[p1], total_counter[p1])
            elif dir == EndpointDirection.BOTTOM:
                ingoing_edges[p1][p2] = get_bottom_edge_coord(node, p1, partial_counter[p1], total_counter[p1])

    # order the left-entering ingoing edges better
    for p1 in ingoing_edges:
        vals = [(x, y) for x, y in ingoing_edges[p1].items() if y[0] == p1[0]]
        if len(vals) > 1:
            vals_x = [x[0] for x in vals]
            vals_y = [x[1] for x in vals]
            vals_x = sorted(vals_x)
            vals_y = sorted(vals_y)
            for i in range(len(vals_x)):
                ingoing_edges[p1][vals_x[i]] = vals_y[i]

    # set waypoints for edges
    for flow in flows:
        source = flow.get_source()
        target = flow.get_target()

        flow.del_waypoints()

        x_src = source.get_x()
        x_trg = target.get_x()
        y_src = source.get_y()
        y_trg = target.get_y()
        p1 = (x_src, y_src)
        p2 = (x_trg, y_trg)

        source_x = outgoing_edges[p1][p2][0]
        source_y = outgoing_edges[p1][p2][1]
        target_x = ingoing_edges[p2][p1][0]
        target_y = ingoing_edges[p2][p1][1]
        dir_source = outgoing_edges_dirs[p1][p2]
        dir_target = ingoing_edges_dirs[p2][p1]

        middle_x = (source_x + target_x) / 2.0
        middle_y = (source_y + target_y) / 2.0

        flow.add_waypoint((source_x, source_y))
        if dir_source in [EndpointDirection.LEFT, EndpointDirection.RIGHT]:
            if dir_target in [EndpointDirection.LEFT, EndpointDirection.RIGHT]:
                flow.add_waypoint((middle_x, source_y))
                flow.add_waypoint((middle_x, target_y))
            elif dir_target in [EndpointDirection.TOP, EndpointDirection.BOTTOM]:
                flow.add_waypoint((target_x, source_y))
        elif dir_source in [EndpointDirection.TOP, EndpointDirection.BOTTOM]:
            if dir_target in [EndpointDirection.TOP, EndpointDirection.BOTTOM]:
                flow.add_waypoint((source_x, middle_y))
                flow.add_waypoint((target_x, middle_y))
            elif dir_target in [EndpointDirection.LEFT, EndpointDirection.RIGHT]:
                flow.add_waypoint((source_x, target_y))

        flow.add_waypoint((target_x, target_y))

    return bpmn_graph
