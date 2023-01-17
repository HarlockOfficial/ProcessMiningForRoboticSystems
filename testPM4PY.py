from typing import List
import pm4py
from pm4py.algo.discovery.inductive.variants.im_f.algorithm import Parameters

import apply_tree


def import_xes(file_path: List[str], process_names: List[str], output_file_path_process_tree: str,
               output_file_path_bpmn: str):
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

    process_tree_dict = apply_tree.my_apply_im_f(event_log, process_names, parameters=params)
    import collaboration_graph
    collaboration_graph_ = collaboration_graph.algorithm.apply_collaboration_graph(process_tree_dict)
    # viz = collaboration_graph.view_graph.my_apply(collaboration_graph_)
    # from pm4py.visualization.process_tree import visualizer as pt_visualizer
    # pt_visualizer.view(viz)
    collaboration_graph.exporter.apply(
        collaboration_graph_.get_root(), output_file_path_process_tree, parameters={'graph': collaboration_graph_})
    bpmn = collaboration_graph.to_bpmn.algorithm.my_convert_to_bpmn(collaboration_graph_)
    collaboration_graph.to_bpmn.exporter.write_bpmn(bpmn, output_file_path_bpmn)


if __name__ == "__main__":
    import_xes(['Logs/healthcare/hospital.xes',
                'Logs/healthcare/gynecologist.xes',
                'Logs/healthcare/laboratory.xes',
                'Logs/healthcare/patient.xes'], ['hospital', 'gynecologist', 'laboratory', 'patient'],
               './process_tree.ptml', './test.bpmn')
