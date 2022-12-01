import pm4py
from pm4py.algo.discovery.inductive.variants.im_f.algorithm import Parameters
from typing import List
import my_to_bpmn
import view_process_tree
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
    process_tree = apply_tree.pm4py.algo.discovery.inductive.variants.im_f.algorithm.apply(event_log, parameters=params)
    for tree in process_tree:
        view_process_tree.pm4py.view_process_tree(tree)
        res = my_to_bpmn.pm4py.convert_to_bpmn(tree)
        my_to_bpmn.pm4py.view_bpmn(res)
        print(tree)


if __name__ == "__main__":
    import_xes(['Logs/real/hospital.xes',
                'Logs/real/gynecologist.xes',
                'Logs/real/laboratory.xes',
                'Logs/real/patient.xes'])
