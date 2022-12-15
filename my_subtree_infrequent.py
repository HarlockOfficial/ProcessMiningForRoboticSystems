import logging
import pkgutil
from copy import copy

import pm4py
from pm4py import util as pmutil
from pm4py.algo.discovery.dfg.utils.dfg_utils import get_activities_from_dfg, \
    infer_start_activities, infer_end_activities
from pm4py.algo.discovery.dfg.utils.dfg_utils import get_ingoing_edges, get_outgoing_edges
from pm4py.algo.discovery.dfg.utils.dfg_utils import negate, get_activities_self_loop
from pm4py.algo.discovery.dfg.variants import native as dfg_inst
from pm4py.algo.discovery.inductive.util import detection_utils, cut_detection
from pm4py.algo.discovery.inductive.variants.im.util import base_case
from pm4py.algo.discovery.inductive.variants.im.util import fall_through
from pm4py.algo.discovery.inductive.variants.im.util import splitting as split
from pm4py.algo.discovery.inductive.variants.im_f import splitting_infrequent, fall_through_infrequent
from pm4py.algo.discovery.inductive.variants.im_f.algorithm import Parameters
from pm4py.algo.filtering.dfg.dfg_filtering import clean_dfg_based_on_noise_thresh
from pm4py.objects.dfg.utils.dfg_utils import transform_dfg_to_directed_nx_graph
from pm4py.statistics.attributes.log import get as attributes_get
from pm4py.statistics.end_activities.log import get as end_activities_get
from pm4py.statistics.start_activities.log import get as start_activities_get
from pm4py.util import exec_utils
from pm4py.algo.discovery.inductive.variants.im_f.data_structures.subtree_infrequent import SubtreeInfrequent


class MySubtreeInfrequent(SubtreeInfrequent):
    def __init__(self, sender_nodes, receiver_nodes, log, initial_log, dfg, master_dfg, initial_dfg, activities, counts, rec_depth, f=0, noise_threshold=0,
                 start_activities=None, end_activities=None, initial_start_activities=None,
                 initial_end_activities=None, parameters=None, real_init=True):
        """
        Constructor

        Parameters
        -----------
        dfg
            Directly follows graph of this subtree
        master_dfg
            Original DFG
        initial_dfg
            Referral directly follows graph that should be taken in account adding hidden/loop transitions
        activities
            Activities of this subtree
        counts
            Shared variable
        rec_depth
            Current recursion depth
        """
        if real_init:
            self.master_dfg = copy(master_dfg)
            self.initial_dfg = copy(initial_dfg)
            self.counts = counts
            self.rec_depth = rec_depth
            self.noise_threshold = noise_threshold
            self.start_activities = start_activities
            self.f = f
            if self.start_activities is None:
                self.start_activities = []
            self.end_activities = end_activities
            if self.end_activities is None:
                self.end_activities = []
            self.initial_start_activities = initial_start_activities
            if self.initial_start_activities is None:
                self.initial_start_activities = infer_start_activities(master_dfg)
            self.initial_end_activities = initial_end_activities
            if self.initial_end_activities is None:
                self.initial_end_activities = infer_end_activities(master_dfg)

            self.second_iteration = None
            self.activities = None
            self.dfg = None
            self.outgoing = None
            self.ingoing = None
            self.self_loop_activities = None
            self.initial_ingoing = None
            self.initial_outgoing = None
            self.activities_direction = None
            self.activities_dir_list = None
            self.negated_dfg = None
            self.negated_activities = None
            self.negated_outgoing = None
            self.negated_ingoing = None
            self.detected_cut = None
            self.children = None
            self.must_insert_skip = False
            self.log = log
            self.initial_log = initial_log
            self.inverted_dfg = None
            self.parameters = parameters
            self.sender_nodes = sender_nodes
            self.receiver_nodes = receiver_nodes

            self.initialize_tree(sender_nodes, receiver_nodes, dfg, log, initial_dfg, activities)

    def __deepcopy__(self, memodict={}):
        """
            def __init__(self, log, dfg, master_dfg, initial_dfg, activities, counts, rec_depth, noise_threshold=0,
                 start_activities=None, end_activities=None, initial_start_activities=None,
                 initial_end_activities=None, parameters=None, real_init=False):
        :param memodict:
        :return:
        """
        S = MySubtreeInfrequent(None, None, None, None, None, None, None, None, None, None, real_init=False)
        S.master_dfg = self.master_dfg
        S.initial_dfg = self.initial_dfg
        S.counts = self.counts
        S.rec_depth = self.rec_depth
        S.noise_threshold = self.noise_threshold
        S.start_activities = self.start_activities
        S.end_activities = self.end_activities
        S.initial_start_activities = self.initial_start_activities
        S.initial_end_activities = self.initial_end_activities
        S.second_iteration = self.second_iteration
        S.activities = self.activities
        S.dfg = self.dfg
        S.outgoing = self.outgoing
        S.ingoing = self.ingoing
        S.self_loop_activities = self.self_loop_activities
        S.initial_ingoing = self.initial_ingoing
        S.initial_outgoing = self.initial_outgoing
        S.activities_direction = self.activities_direction
        S.activities_dir_list = self.activities_dir_list
        S.negated_dfg = self.negated_dfg
        S.negated_activities = self.negated_activities
        S.negated_outgoing = self.negated_outgoing
        S.negated_ingoing = self.negated_ingoing
        S.detected_cut = self.detected_cut
        S.children = self.children
        S.must_insert_skip = self.must_insert_skip
        S.log = self.log
        S.initial_log = self.initial_log
        S.inverted_dfg = self.inverted_dfg
        S.sender_nodes = self.sender_nodes
        S.receiver_nodes = self.receiver_nodes
        try:
            S.parameters = self.parameters
        except:
            pass
        return S

    def initialize_tree(self, sender_nodes, receiver_nodes, dfg, log, initial_dfg, activities, second_iteration=False, end_call=True):
        self.second_iteration = second_iteration

        if activities is None:
            self.activities = get_activities_from_dfg(dfg)
        else:
            self.activities = copy(activities)

        if second_iteration:
            self.dfg = clean_dfg_based_on_noise_thresh(self.dfg, self.activities, self.noise_threshold)
        else:
            self.dfg = copy(dfg)

        self.initial_dfg = initial_dfg

        self.outgoing = get_outgoing_edges(self.dfg)
        self.ingoing = get_ingoing_edges(self.dfg)
        self.self_loop_activities = get_activities_self_loop(self.dfg)
        self.initial_outgoing = get_outgoing_edges(self.initial_dfg)
        self.initial_ingoing = get_ingoing_edges(self.initial_dfg)
        # self.activities_direction = get_activities_direction(self.dfg, self.activities)
        # self.activities_dir_list = get_activities_dirlist(self.activities_direction)
        self.negated_dfg = negate(self.dfg)
        self.negated_activities = get_activities_from_dfg(self.negated_dfg)
        self.negated_outgoing = get_outgoing_edges(self.negated_dfg)
        self.negated_ingoing = get_ingoing_edges(self.negated_dfg)
        self.detected_cut = None
        self.children = []
        self.log = log
        self.sender_nodes = sender_nodes
        self.receiver_nodes = receiver_nodes

        self.detect_cut_if(second_iteration=False, parameters=self.parameters)

    #TODO; da modificare rimuovendo log
    def apply_cut_im_plain(self, type_of_cut, cut, activity_key):
        if type_of_cut == 'concurrent':
            self.detected_cut = 'concurrent'
            new_logs = split.split_xor(cut[1], self.log, activity_key)
            for l in new_logs:
                new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=self.parameters).items() if v > 0]
                activities = attributes_get.get_attribute_values(l, activity_key)
                start_activities = list(
                    start_activities_get.get_start_activities(l, parameters=self.parameters).keys())
                end_activities = list(
                    end_activities_get.get_end_activities(l, parameters=self.parameters).keys())
                self.children.append(
                    MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities, self.counts,
                                      self.rec_depth + 1, self.f,
                                      noise_threshold=self.noise_threshold, start_activities=start_activities,
                                      end_activities=end_activities,
                                      initial_start_activities=self.initial_start_activities,
                                      initial_end_activities=self.initial_end_activities, parameters=self.parameters))
        elif type_of_cut == 'sequential':
            new_logs = split.split_sequence(cut[1], self.log, activity_key)
            self.detected_cut = "sequential"
            for l in new_logs:
                new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=self.parameters).items() if v > 0]
                activities = attributes_get.get_attribute_values(l, activity_key)
                start_activities = list(
                    start_activities_get.get_start_activities(l, parameters=self.parameters).keys())
                end_activities = list(
                    end_activities_get.get_end_activities(l, parameters=self.parameters).keys())
                self.children.append(
                    MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities, self.counts,
                                      self.rec_depth + 1, self.f,
                                      noise_threshold=self.noise_threshold, start_activities=start_activities,
                                      end_activities=end_activities,
                                      initial_start_activities=self.initial_start_activities,
                                      initial_end_activities=self.initial_end_activities, parameters=self.parameters))
        elif type_of_cut == 'parallel':
            new_logs = split.split_parallel(cut[1], self.log, activity_key)
            self.detected_cut = "parallel"
            for l in new_logs:
                new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=self.parameters).items() if v > 0]
                activities = attributes_get.get_attribute_values(l, activity_key)
                start_activities = list(
                    start_activities_get.get_start_activities(l, parameters=self.parameters).keys())
                end_activities = list(
                    end_activities_get.get_end_activities(l, parameters=self.parameters).keys())
                self.children.append(
                    MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities, self.counts,
                                      self.rec_depth + 1, self.f,
                                      noise_threshold=self.noise_threshold, start_activities=start_activities,
                                      end_activities=end_activities,
                                      initial_start_activities=self.initial_start_activities,
                                      initial_end_activities=self.initial_end_activities, parameters=self.parameters))
        elif type_of_cut == 'loopCut':
            new_logs = split.split_loop(cut[1], self.log, activity_key)
            self.detected_cut = "loopCut"
            for l in new_logs:
                new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=self.parameters).items() if v > 0]
                activities = attributes_get.get_attribute_values(l, activity_key)
                start_activities = list(
                    start_activities_get.get_start_activities(l, parameters=self.parameters).keys())
                end_activities = list(
                    end_activities_get.get_end_activities(l, parameters=self.parameters).keys())
                self.children.append(
                    MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities, self.counts,
                                      self.rec_depth + 1, self.f,
                                      noise_threshold=self.noise_threshold,
                                      start_activities=start_activities,
                                      end_activities=end_activities,
                                      initial_start_activities=self.initial_start_activities,
                                      initial_end_activities=self.initial_end_activities, parameters=self.parameters))

    #TODO; da modificare rimuovendo log
    def detect_cut_if(self, second_iteration=False, parameters=None):
        if parameters is None:
            parameters = {}
        activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters,
                                                  pmutil.xes_constants.DEFAULT_NAME_KEY)
        # check base cases:
        empty_log = base_case.empty_log(self.log)
        single_activity = base_case.single_activity(self.log, activity_key)
        if empty_log:
            self.detected_cut = 'empty_log'
        elif single_activity:
            self.detected_cut = 'single_activity'
            current_activity = list(self.activities.keys())[0]
            filtered_initial_dfg_start_activities = [x[0][0] for x in self.initial_dfg if x[0][1] == current_activity and x[0][0] in self.initial_start_activities]
            filtered_initial_dfg_end_activities = [x[0][1] for x in self.initial_dfg if x[0][0] == current_activity and x[0][1] in self.initial_end_activities]
            # remove from filtered_initial_dfg the activities that are in the log
            any_log_activity = []
            for trace in self.initial_log:
                for event in trace:
                    if event[activity_key] not in any_log_activity:
                        any_log_activity.append(event[activity_key])
        
            if len(filtered_initial_dfg_start_activities) > 0:
                filtered_initial_dfg_start_activities = list(set(filtered_initial_dfg_start_activities).difference(set(any_log_activity)))
            if len(filtered_initial_dfg_end_activities) > 0:
                filtered_initial_dfg_end_activities = list(set(filtered_initial_dfg_end_activities).difference(set(any_log_activity)))
            
            if len(filtered_initial_dfg_start_activities) > 0:
                self.detected_cut = 'receive_message_activity'
                from pm4py.objects.log import obj
                for a in filtered_initial_dfg_start_activities:
                    sender_node = MySubtreeInfrequent(None, None, None, None, None, None, None, None, None, None, real_init=False)
                    sender_node.detected_cut = 'single_activity'
                    sender_node.activities = {a: self.activities[current_activity]}
                    sender_node.parameters = self.parameters
                    tmp_log = obj.EventLog()
                    tmp_log.attributes.clear()
                    tmp_log.append([])
                    tmp_log[0].append({activity_key: a})
                    sender_node.log = tmp_log
                    self.children.append(sender_node)
                receiver_node = MySubtreeInfrequent(None, None, None, None, None, None, None, None, None, None, real_init=False)
                receiver_node.detected_cut = 'single_activity'
                receiver_node.activities = {current_activity: self.activities[current_activity]}
                receiver_node.parameters = self.parameters
                tmp_log = obj.EventLog()
                tmp_log.attributes.clear()
                tmp_log.append([])
                tmp_log[0].append({activity_key: current_activity})
                receiver_node.log = tmp_log
                self.children.append(receiver_node)
            
            if len(filtered_initial_dfg_end_activities) > 0:
                self.detected_cut = 'send_message_activity'
                from pm4py.objects.log import obj
                receiver_node = MySubtreeInfrequent(None, None, None, None, None, None, None, None, None, None, real_init=False)
                receiver_node.detected_cut = 'single_activity'
                receiver_node.activities = {current_activity: self.activities[current_activity]}
                receiver_node.parameters = self.parameters
                tmp_log = obj.EventLog()
                tmp_log.attributes.clear()
                tmp_log.append([])
                tmp_log[0].append({activity_key: current_activity})
                receiver_node.log = tmp_log
                self.children.append(receiver_node)
                for a in filtered_initial_dfg_end_activities:
                    sender_node = MySubtreeInfrequent(None, None, None, None, None, None, None, None, None, None, real_init=False)
                    sender_node.detected_cut = 'single_activity'
                    sender_node.activities = {a: self.activities[current_activity]}
                    sender_node.parameters = self.parameters
                    tmp_log = obj.EventLog()
                    tmp_log.attributes.clear()
                    tmp_log.append([])
                    tmp_log[0].append({activity_key: a})
                    sender_node.log = tmp_log
                    self.children.append(sender_node)

        # if no base cases are found, search for a cut:
        # use the cutting and splitting functions of im_plain:
        else:
            found_plain_cut, type_of_cut, cut = self.check_cut_im_plain()

            if found_plain_cut:
                self.apply_cut_im_plain(type_of_cut, cut, activity_key)
            # if im_plain does not find a cut, we filter on our threshold and then again apply the im_cut detection
            # but this time, we have to use different splitting functions:
            else:
                self.filter_dfg_on_threshold()
                found_plain_cut, type_of_cut, cut = self.check_cut_im_plain()
                if found_plain_cut:
                    if type_of_cut == 'concurrent':
                        logging.debug("concurrent_cut_if")
                        self.detected_cut = 'concurrent'
                        new_logs = splitting_infrequent.split_xor_infrequent(cut[1], self.log, activity_key)
                        for l in new_logs:
                            new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=parameters).items() if v > 0]
                            activities = attributes_get.get_attribute_values(l, activity_key)
                            start_activities = list(
                                start_activities_get.get_start_activities(l, parameters=parameters).keys())
                            end_activities = list(
                                end_activities_get.get_end_activities(l, parameters=parameters).keys())
                            self.children.append(
                                MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities,
                                                  self.counts,
                                                  self.rec_depth + 1, self.f,
                                                  noise_threshold=self.noise_threshold,
                                                  start_activities=start_activities,
                                                  end_activities=end_activities,
                                                  initial_start_activities=self.initial_start_activities,
                                                  initial_end_activities=self.initial_end_activities,
                                                  parameters=parameters))
                    elif type_of_cut == 'sequential':
                        logging.debug("sequential_if")
                        new_logs = splitting_infrequent.split_sequence_infrequent(cut[1], self.log, activity_key)
                        self.detected_cut = "sequential"
                        for l in new_logs:
                            new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=parameters).items() if v > 0]
                            activities = attributes_get.get_attribute_values(l, activity_key)
                            start_activities = list(
                                start_activities_get.get_start_activities(l, parameters=parameters).keys())
                            end_activities = list(
                                end_activities_get.get_end_activities(l, parameters=parameters).keys())
                            self.children.append(
                                MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities,
                                                  self.counts,
                                                  self.rec_depth + 1, self.f,
                                                  noise_threshold=self.noise_threshold,
                                                  start_activities=start_activities,
                                                  end_activities=end_activities,
                                                  initial_start_activities=self.initial_start_activities,
                                                  initial_end_activities=self.initial_end_activities,
                                                  parameters=parameters))
                    elif type_of_cut == 'parallel':
                        logging.debug("parallel_if")
                        new_logs = split.split_parallel(cut[1], self.log, activity_key)
                        self.detected_cut = "parallel"
                        for l in new_logs:
                            new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=parameters).items() if v > 0]
                            activities = attributes_get.get_attribute_values(l, activity_key)
                            start_activities = list(
                                start_activities_get.get_start_activities(l, parameters=parameters).keys())
                            end_activities = list(
                                end_activities_get.get_end_activities(l, parameters=parameters).keys())
                            self.children.append(
                                MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities,
                                                  self.counts,
                                                  self.rec_depth + 1, self.f,
                                                  noise_threshold=self.noise_threshold,
                                                  start_activities=start_activities,
                                                  end_activities=end_activities,
                                                  initial_start_activities=self.initial_start_activities,
                                                  initial_end_activities=self.initial_end_activities,
                                                  parameters=parameters))
                    elif type_of_cut == 'loopCut':
                        logging.debug("loopCut_if")
                        new_logs = splitting_infrequent.split_loop_infrequent(cut[1], self.log, activity_key)
                        self.detected_cut = "loopCut"
                        for l in new_logs:
                            new_dfg = [(k, v) for k, v in dfg_inst.apply(l, parameters=parameters).items() if v > 0]
                            activities = attributes_get.get_attribute_values(l, activity_key)
                            start_activities = list(
                                start_activities_get.get_start_activities(l, parameters=parameters).keys())
                            end_activities = list(
                                end_activities_get.get_end_activities(l, parameters=parameters).keys())
                            self.children.append(
                                MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, l, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities,
                                                  self.counts,
                                                  self.rec_depth + 1, self.f,
                                                  noise_threshold=self.noise_threshold,
                                                  start_activities=start_activities,
                                                  end_activities=end_activities,
                                                  initial_start_activities=self.initial_start_activities,
                                                  initial_end_activities=self.initial_end_activities,
                                                  parameters=parameters))

                else:
                    self.apply_fall_through_infrequent(parameters)

    #TODO; da modificare rimuovendo log
    def apply_fall_through_infrequent(self, parameters=None):
        if parameters is None:
            parameters = {}
        activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, self.parameters,
                                                  pmutil.xes_constants.DEFAULT_NAME_KEY)

        # set flags for fall_throughs, base case is True (enabled)
        use_empty_trace = (Parameters.EMPTY_TRACE_KEY not in parameters) or parameters[
            Parameters.EMPTY_TRACE_KEY]
        use_act_once_per_trace = (Parameters.ONCE_PER_TRACE_KEY not in parameters) or parameters[
            Parameters.ONCE_PER_TRACE_KEY]
        use_act_concurrent = (Parameters.CONCURRENT_KEY not in parameters) or parameters[
            Parameters.CONCURRENT_KEY]
        use_strict_tau_loop = (Parameters.STRICT_TAU_LOOP_KEY not in parameters) or parameters[
            Parameters.STRICT_TAU_LOOP_KEY]
        use_tau_loop = (Parameters.TAU_LOOP_KEY not in parameters) or parameters[Parameters.TAU_LOOP_KEY]

        if use_empty_trace:
            empty_traces_present, enough_traces, new_log = fall_through_infrequent.empty_trace_filtering(self.log,
                                                                                                         self.f)
            self.log = new_log
        else:
            empty_traces_present = False
            enough_traces = False
        # if an empty trace is found, the empty trace fallthrough applies
        if empty_traces_present and enough_traces:
            logging.debug("empty_trace_if")
            self.detected_cut = 'empty_trace'
            new_dfg = [(k, v) for k, v in dfg_inst.apply(new_log, parameters=self.parameters).items() if v > 0]
            activities = attributes_get.get_attribute_values(new_log, activity_key)
            start_activities = list(
                start_activities_get.get_start_activities(new_log, parameters=parameters).keys())
            end_activities = list(
                end_activities_get.get_end_activities(new_log, parameters=parameters).keys())
            self.children.append(
                MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, new_log, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities, self.counts,
                                  self.rec_depth + 1, self.f,
                                  noise_threshold=self.noise_threshold,
                                  start_activities=start_activities,
                                  end_activities=end_activities,
                                  initial_start_activities=self.initial_start_activities,
                                  initial_end_activities=self.initial_end_activities, parameters=parameters))
        elif empty_traces_present and not enough_traces:
            # no node is added to the PT, instead we just use recursion on the log without the empty traces
            self.detect_cut_if(parameters=parameters)
        else:
            if use_act_once_per_trace:
                activity_once, new_log, small_log = fall_through.act_once_per_trace(self.log, self.activities,
                                                                                    activity_key)
            else:
                activity_once = False
            if activity_once:
                self.detected_cut = 'parallel'
                # create two new dfgs as we need them to append to self.children later
                new_dfg = [(k, v) for k, v in dfg_inst.apply(new_log, parameters=parameters).items() if
                           v > 0]
                activities = attributes_get.get_attribute_values(new_log, activity_key)
                small_dfg = [(k, v) for k, v in dfg_inst.apply(small_log, parameters=parameters).items() if
                             v > 0]
                small_activities = attributes_get.get_attribute_values(small_log, activity_key)
                start_activities = list(
                    start_activities_get.get_start_activities(new_log, parameters=parameters).keys())
                end_activities = list(
                    end_activities_get.get_end_activities(new_log, parameters=parameters).keys())
                # append the chosen activity as leaf:
                self.children.append(
                    MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, small_log, self.initial_log, small_dfg, self.master_dfg, self.initial_dfg, small_activities,
                                      self.counts,
                                      self.rec_depth + 1, self.f,
                                      noise_threshold=self.noise_threshold,
                                      initial_start_activities=self.initial_start_activities,
                                      initial_end_activities=self.initial_end_activities, parameters=parameters))
                # continue with the recursion on the new log
                self.children.append(
                    MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, new_log, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg, activities,
                                      self.counts,
                                      self.rec_depth + 1, self.f,
                                      noise_threshold=self.noise_threshold,
                                      start_activities=start_activities,
                                      end_activities=end_activities,
                                      initial_start_activities=self.initial_start_activities,
                                      initial_end_activities=self.initial_end_activities, parameters=parameters))

            else:
                if use_act_concurrent:
                    activity_concurrent, new_log, small_log, key = fall_through.activity_concurrent(self, self.log,
                                                                                                    self.activities,
                                                                                                    activity_key,
                                                                                                    parameters=parameters)
                else:
                    activity_concurrent = False
                if activity_concurrent:
                    self.detected_cut = 'parallel'
                    # create two new dfgs on to append later
                    new_dfg = [(k, v) for k, v in dfg_inst.apply(new_log, parameters=parameters).items() if
                               v > 0]
                    activities = attributes_get.get_attribute_values(new_log, activity_key)
                    small_dfg = [(k, v) for k, v in dfg_inst.apply(small_log, parameters=parameters).items() if
                                 v > 0]
                    small_activities = attributes_get.get_attribute_values(small_log, activity_key)
                    start_activities = list(
                        start_activities_get.get_start_activities(new_log, parameters=parameters).keys())
                    end_activities = list(
                        end_activities_get.get_end_activities(new_log, parameters=parameters).keys())
                    # append the concurrent activity as leaf:
                    self.children.append(
                        MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, small_log, self.initial_log, small_dfg, self.master_dfg, self.initial_dfg,
                                          small_activities,
                                          self.counts,
                                          self.rec_depth + 1, self.f,
                                          noise_threshold=self.noise_threshold,
                                          initial_start_activities=self.initial_start_activities,
                                          initial_end_activities=self.initial_end_activities, parameters=parameters))
                    # continue with the recursion on the new log:
                    self.children.append(
                        MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, new_log, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg,
                                          activities,
                                          self.counts,
                                          self.rec_depth + 1, self.f,
                                          noise_threshold=self.noise_threshold,
                                          start_activities=start_activities,
                                          end_activities=end_activities,
                                          initial_start_activities=self.initial_start_activities,
                                          initial_end_activities=self.initial_end_activities, parameters=parameters))
                else:
                    if use_strict_tau_loop:
                        strict_tau_loop, new_log = fall_through.strict_tau_loop(self.log, self.start_activities,
                                                                                self.end_activities, activity_key)
                    else:
                        strict_tau_loop = False
                    if strict_tau_loop:
                        self.detected_cut = 'strict_tau_loop'
                        new_dfg = [(k, v) for k, v in dfg_inst.apply(new_log, parameters=parameters).items() if
                                   v > 0]
                        activities = attributes_get.get_attribute_values(new_log, activity_key)
                        start_activities = list(
                            start_activities_get.get_start_activities(new_log, parameters=parameters).keys())
                        end_activities = list(
                            end_activities_get.get_end_activities(new_log, parameters=parameters).keys())
                        self.children.append(
                            MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, new_log, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg,
                                              activities,
                                              self.counts,
                                              self.rec_depth + 1, self.f,
                                              noise_threshold=self.noise_threshold,
                                              start_activities=start_activities,
                                              end_activities=end_activities,
                                              initial_start_activities=self.initial_start_activities,
                                              initial_end_activities=self.initial_end_activities,
                                              parameters=parameters))
                    else:
                        if use_tau_loop:
                            tau_loop, new_log = fall_through.tau_loop(self.log, self.start_activities, activity_key)
                        else:
                            tau_loop = False
                        if tau_loop:
                            self.detected_cut = 'tau_loop'
                            new_dfg = [(k, v) for k, v in dfg_inst.apply(new_log, parameters=parameters).items() if
                                       v > 0]
                            activities = attributes_get.get_attribute_values(new_log, activity_key)
                            start_activities = list(
                                start_activities_get.get_start_activities(new_log, parameters=parameters).keys())
                            end_activities = list(
                                end_activities_get.get_end_activities(new_log, parameters=parameters).keys())
                            self.children.append(
                                MySubtreeInfrequent(self.sender_nodes, self.receiver_nodes, new_log, self.initial_log, new_dfg, self.master_dfg, self.initial_dfg,
                                                  activities,
                                                  self.counts,
                                                  self.rec_depth + 1, self.f,
                                                  noise_threshold=self.noise_threshold,
                                                  start_activities=start_activities,
                                                  end_activities=end_activities,
                                                  initial_start_activities=self.initial_start_activities,
                                                  initial_end_activities=self.initial_end_activities,
                                                  parameters=parameters))
                        else:
                            logging.debug("flower_if")
                            self.detected_cut = 'flower'
                            # apply flower fall through as last option:


def my_make_tree(sender_nodes, receiver_nodes, log, original_dfg, dfg, activities, c, f, recursion_depth, noise_threshold, start_activities, end_activities, parameters=None):
    if parameters is None:
        parameters = {}

    tree = MySubtreeInfrequent(sender_nodes, receiver_nodes, log, log, original_dfg, dfg, dfg, activities, c, f, recursion_depth, noise_threshold,
                             start_activities, end_activities, start_activities, end_activities,
                             parameters=parameters)
    return tree

pm4py.algo.discovery.inductive.variants.im_f.data_structures.subtree_infrequent.make_tree = my_make_tree
pm4py.algo.discovery.inductive.variants.im_f.data_structures.subtree_infrequent.SubtreeInfrequent = MySubtreeInfrequent
