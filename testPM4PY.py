from typing import List
import pm4py
from pm4py.algo.discovery.inductive.variants.im_f.algorithm import Parameters

import collaboration_graph.algorithm
import my_to_bpmn
from pm4py.objects.bpmn.layout import layouter
import apply_tree


def import_xes(file_path: List[str]):
    event_log = []
    for file_name in file_path:
        event_log.append(pm4py.read_xes(file_name))
    params = {
        Parameters.ACTIVITY_KEY: 'concept:name',
        Parameters.TIMESTAMP_KEY: 'time:timestamp',
        Parameters.CASE_ID_KEY: 'case:concept:name',
        # im_f_algorithm.Parameters.START_TIMESTAMP_KEY: 'time:timestamp:start',
        # im_f_algorithm.Parameters.NOISE_THRESHOLD: "noiseThreshold",
        # im_f_algorithm.Parameters.EMPTY_TRACE_KEY: "empty_trace",
        # im_f_algorithm.Parameters.ONCE_PER_TRACE_KEY: "once_per_trace",
        # im_f_algorithm.Parameters.CONCURRENT_KEY: "concurrent",
        # im_f_algorithm.Parameters.STRICT_TAU_LOOP_KEY: "strict_tau_loop",
        # im_f_algorithm.Parameters.TAU_LOOP_KEY: "tau_loop",
    }

    process_tree_list = apply_tree.pm4py.algo.discovery.inductive.variants.im_f.algorithm.apply(event_log, parameters=params)
    import collaboration_graph
    collaboration_graph_ = collaboration_graph.algorithm.apply_collaboration_graph(process_tree_list)
    # print(collaboration_graph_)
    collaboration_graph.view_graph.pm4py.view_process_tree(collaboration_graph_)
    bpmn = collaboration_graph.to_bpmn.algorithm.my_convert_to_bpmn(collaboration_graph_)
    pm4py.view_bpmn(bpmn)
    """
    import graphviz
    for tree in process_tree_list:
        try:
            view_process_tree.pm4py.view_process_tree(tree)
            res = my_to_bpmn.pm4py.convert_to_bpmn(tree)
            res = layouter.apply(res)
            pm4py.write_bpmn(res, "ru.bpmn")
            my_to_bpmn.pm4py.view_bpmn(res)
        except graphviz.backend.execute.ExecutableNotFound:
            print(tree)
    """


def tmp_import_xes(log_name):
    import pm4py
    event_log = pm4py.read_xes(log_name)
    single_process_tree = pm4py.discover_process_tree_inductive(event_log)
    pm4py.view_process_tree(single_process_tree)


if __name__ == "__main__":
    import_xes(['Logs/real/hospital.xes',
                'Logs/real/gynecologist.xes',
                'Logs/real/laboratory.xes',
                'Logs/real/patient.xes'])
    # tmp_import_xes('Logs/real/patient.xes')