from typing import List, Tuple

import pm4py
from pm4py import util as pmutil
from pm4py.algo.discovery.dfg.variants import native as dfg_inst
from pm4py.algo.discovery.inductive.util import shared_constants
from pm4py.algo.discovery.inductive.util import tree_consistency
from pm4py.algo.discovery.inductive.util.petri_el_count import Counts
from pm4py.algo.discovery.inductive.variants.im.util.get_tree_repr_implain import get_transition
from pm4py.algo.discovery.inductive.variants.im_f.algorithm import Parameters
from pm4py.objects.log.obj import EventLog
from pm4py.objects.log.util import filtering_utils
from pm4py.objects.process_tree.obj import Operator
from pm4py.objects.process_tree.obj import ProcessTree
from pm4py.objects.process_tree.utils import generic
from pm4py.objects.process_tree.utils.generic import tree_sort
from pm4py.statistics.attributes.log import get as attributes_get
from pm4py.statistics.end_activities.log import get as end_activities_get
from pm4py.statistics.start_activities.log import get as start_activities_get
from pm4py.util import exec_utils, xes_constants

import my_subtree_infrequent


def discover_in_nodes(log: List[EventLog], dfg_list: List[List[Tuple[Tuple[str, str], int]]], activity_key: str) -> \
        Tuple[List[List[Tuple[Tuple[str, str], int]]], List[List[Tuple[Tuple[str, str], int]]]]:

    sender_nodes = [[] for _ in range(len(dfg_list))]
    receiver_nodes = [[] for _ in range(len(dfg_list))]

    # discover receiving nodes
    send_list = []
    send_receive_dict = {}
    for trace_list_1 in log:
        for trace_list_2 in log:
            for trace_1 in trace_list_1:
                for trace_2 in trace_list_2:
                    for event_1 in trace_1:
                        if 'msgType' in event_1.keys() and event_1['msgType'] == 'send' and event_1[
                                activity_key] not in send_receive_dict.keys():
                            for event_2 in trace_2:
                                if 'msgType' in event_2.keys() and event_2['msgType'] == 'receive' and event_2[
                                        activity_key] not in send_receive_dict.keys():
                                    if event_1['msgFlow'] == event_2['msgFlow']:
                                        send_list.append((event_1[activity_key], event_2[activity_key]))
                                        send_receive_dict[event_1[activity_key]] = True
                                        send_receive_dict[event_2[activity_key]] = True
    for elem in send_list:
        for index, dfg in enumerate(dfg_list):
            found_sender = -1
            found_receiver = -1
            for element in dfg:
                if element[0][1] == elem[0] or element[0][0] == elem[0]:
                    # found sender
                    found_sender = element[1]
                if element[0][0] == elem[1] or element[0][1] == elem[1]:
                    # found receiver
                    found_receiver = element[1]

            if found_sender != -1:
                dfg.append(((elem[0], elem[1]), found_sender))
                sender_nodes[index].append(((elem[0], elem[1]), found_sender))

            if found_receiver != -1:
                dfg.append(((elem[0], elem[1]), found_receiver))
                receiver_nodes[index].append(((elem[0], elem[1]), found_receiver))

    return sender_nodes, receiver_nodes


"""
def discover_in_nodes(log: EventLog, dfg: list[tuple[tuple[str, str], int]]) -> list[tuple[tuple[str, str], int]]:
    sender_nodes = [(('PIPPO', 'Receive patient results'), 50)]
    return sender_nodes
"""


def my_apply_tree(log: List[EventLog], parameters) -> List[ProcessTree]:
    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters,
                                              pmutil.xes_constants.DEFAULT_NAME_KEY)
    '''DFG INIT'''
    # Working with the first log
    # log = log[0]
    # dfg = [(k, v) for k, v in dfg_inst.apply(log, parameters=parameters).items() if v > 0]
    # sender_nodes = discover_in_nodes(log, dfg)
    # dfg.extend(sender_nodes)
    dfg = []
    for index, trace in enumerate(log):
        dfg.append([(k, v) for k, v in dfg_inst.apply(trace, parameters=parameters).items() if v > 0])
    receiver_nodes, sender_nodes = discover_in_nodes(log, dfg, activity_key)

    for index, trace in enumerate(log):
        # keep only the activity attribute (since the others are not used)
        log[index] = filtering_utils.keep_only_one_attribute_per_event(trace, activity_key)

    noise_threshold = exec_utils.get_param_value(Parameters.NOISE_THRESHOLD, parameters,
                                                 shared_constants.NOISE_THRESHOLD_IMF)

    process_tree = []
    for index, trace in enumerate(log):
        sender_nodes_t = sender_nodes[index]
        receiver_nodes_t = receiver_nodes[index]
        dfg_t = dfg[index]
        log_t = trace

        c = Counts()
        activities = attributes_get.get_attribute_values(log_t, activity_key)
        start_activities = list(start_activities_get.get_start_activities(log_t, parameters=parameters).keys())
        end_activities = list(end_activities_get.get_end_activities(log_t, parameters=parameters).keys())
        for x in sender_nodes_t:
            activities[x[0][0]] = x[1]
            start_activities.append(x[0][0])
        for x in receiver_nodes_t:
            activities[x[0][1]] = x[1]
            end_activities.append(x[0][1])
        
        contains_empty_traces = False
        traces_length = [len(trace) for trace in log_t]
        if traces_length:
            contains_empty_traces = min([len(trace) for trace in log_t]) == 0

        # set the threshold parameter based on f and the max value in the dfg:
        max_value = 0
        for key, value in dfg_t:
            if value > max_value:
                max_value = value
        threshold = noise_threshold * max_value

        recursion_depth = 0

        sub = my_subtree_infrequent.my_make_tree(sender_nodes_t, receiver_nodes_t, log_t, dfg_t, dfg_t, dfg_t, activities, c, recursion_depth,
                                                 noise_threshold, threshold,
                                                 start_activities, end_activities,
                                                 start_activities, end_activities, parameters=parameters)

        process_tree.append(get_tree_repr_implain_get_repr(sub, 0, contains_empty_traces=contains_empty_traces))
        # Ensures consistency to the parent pointers in the process tree
        tree_consistency.fix_parent_pointers(process_tree[index])
        # Fixes a 1 child XOR that is added when single-activities flowers are found
        tree_consistency.fix_one_child_xor_flower(process_tree[index])
        # folds the process tree (to simplify it in case fallthroughs/filtering is applied)
        process_tree[index] = generic.fold(process_tree[index])
        # sorts the process tree to ensure consistency in different executions of the algorithm
        tree_sort(process_tree[index])

    return process_tree


def get_tree_repr_implain_get_repr(spec_tree_struct, rec_depth, contains_empty_traces=False):
    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, spec_tree_struct.parameters,
                                              xes_constants.DEFAULT_NAME_KEY)

    base_cases = ('empty_log', 'single_activity')
    cut = ('concurrent', 'sequential', 'parallel', 'loopCut', 'receive_message_activity', 'send_message_activity')
    # note that the activity_once_per_trace is not included here, as it is can be dealt with as a parallel cut
    fall_throughs = ('empty_trace', 'strict_tau_loop', 'tau_loop', 'flower')

    # if a cut was detected in the current subtree:
    if spec_tree_struct.detected_cut in cut:
        if spec_tree_struct.detected_cut == "sequential":
            final_tree_repr = ProcessTree(operator=Operator.SEQUENCE)
        elif spec_tree_struct.detected_cut == "loopCut":
            final_tree_repr = ProcessTree(operator=Operator.LOOP)
        elif spec_tree_struct.detected_cut == "concurrent":
            final_tree_repr = ProcessTree(operator=Operator.XOR)
        elif spec_tree_struct.detected_cut == "parallel":
            final_tree_repr = ProcessTree(operator=Operator.PARALLEL)
        elif spec_tree_struct.detected_cut == "receive_message_activity":
            final_tree_repr = ProcessTree(operator=Operator.RECEIVE_MESSAGE)
        elif spec_tree_struct.detected_cut == "send_message_activity":
            final_tree_repr = ProcessTree(operator=Operator.SEND_MESSAGE)
        
        if not (spec_tree_struct.detected_cut == "loopCut" and len(spec_tree_struct.children) >= 3):
            for ch in spec_tree_struct.children:
                # get the representation of the current child (from children in the subtree-structure):
                child = get_tree_repr_implain_get_repr(ch, rec_depth + 1)
                # add connection from child_tree to child_final and the other way around:
                final_tree_repr.children.append(child)
                child.parent = final_tree_repr

        else:
            child = get_tree_repr_implain_get_repr(spec_tree_struct.children[0], rec_depth + 1)
            final_tree_repr.children.append(child)
            child.parent = final_tree_repr

            redo_child = ProcessTree(operator=Operator.XOR)
            for ch in spec_tree_struct.children[1:]:
                child = get_tree_repr_implain_get_repr(ch, rec_depth + 1)
                redo_child.children.append(child)
                child.parent = redo_child

            final_tree_repr.children.append(redo_child)
            redo_child.parent = final_tree_repr

        if spec_tree_struct.detected_cut == "loopCut" and len(spec_tree_struct.children) < 3:
            while len(spec_tree_struct.children) < 2:
                child = ProcessTree()
                final_tree_repr.children.append(child)
                child.parent = final_tree_repr
                spec_tree_struct.children.append(None)

    if spec_tree_struct.detected_cut in base_cases:
        # in the base case of an empty log, we only return a silent transition
        if spec_tree_struct.detected_cut == "empty_log":
            return ProcessTree(operator=None, label=None)
        # in the base case of a single activity, we return a tree consisting of the single activity
        elif spec_tree_struct.detected_cut == "single_activity":
            act_a = spec_tree_struct.log[0][0][activity_key]
            return ProcessTree(operator=None, label=act_a)

    if spec_tree_struct.detected_cut in fall_throughs:
        if spec_tree_struct.detected_cut == "empty_trace":
            # should return XOR(tau, IM(L') )
            final_tree_repr = ProcessTree(operator=Operator.XOR)
            final_tree_repr.children.append(ProcessTree(operator=None, label=None))
            # iterate through all children of the current node
            for ch in spec_tree_struct.children:
                child = get_tree_repr_implain_get_repr(ch, rec_depth + 1)
                final_tree_repr.children.append(child)
                child.parent = final_tree_repr

        elif spec_tree_struct.detected_cut == "strict_tau_loop" or spec_tree_struct.detected_cut == "tau_loop":
            # should return LOOP( IM(L'), tau)
            final_tree_repr = ProcessTree(operator=Operator.LOOP)
            # iterate through all children of the current node
            if spec_tree_struct.children:
                for ch in spec_tree_struct.children:
                    child = get_tree_repr_implain_get_repr(ch, rec_depth + 1)
                    final_tree_repr.children.append(child)
                    child.parent = final_tree_repr
            else:
                for ch in spec_tree_struct.activities:
                    child = get_transition(ch)
                    final_tree_repr.append(child)
                    child.parent = final_tree_repr

            # add a silent tau transition as last child of the current node
            final_tree_repr.children.append(ProcessTree(operator=None, label=None))

        elif spec_tree_struct.detected_cut == "flower":
            # should return something like LOOP(XOR(a,b,c,d,...), tau)
            final_tree_repr = ProcessTree(operator=Operator.LOOP)
            xor_child = ProcessTree(operator=Operator.XOR, parent=final_tree_repr)
            # append all the activities in the current subtree to the XOR part to allow for any behaviour
            for ch in spec_tree_struct.activities:
                child = get_transition(ch)
                xor_child.children.append(child)
                child.parent = xor_child
            final_tree_repr.children.append(xor_child)
            # now add the tau to the children to get the wanted output
            final_tree_repr.children.append(ProcessTree(operator=None, label=None))

    return final_tree_repr


def my_apply_im_f(log: List[EventLog], parameters):
    from pm4py.objects.conversion.log import converter
    for index, trace in enumerate(log):
        log[index] = converter.apply(trace, parameters=parameters)
    tree = my_apply_tree(log, parameters)
    return tree


pm4py.algo.discovery.inductive.variants.im_f.algorithm.get_tree_repr_implain.get_repr = get_tree_repr_implain_get_repr
pm4py.algo.discovery.inductive.variants.im_f.algorithm.apply_tree = my_apply_tree
pm4py.algo.discovery.inductive.variants.im_f.algorithm.apply = my_apply_im_f
