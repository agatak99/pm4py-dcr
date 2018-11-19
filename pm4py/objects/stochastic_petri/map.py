import pm4py
from pm4py.algo.conformance.tokenreplay import factory as token_replay
from pm4py.algo.filtering.tracelog.variants import variants_filter as variants_module
from pm4py.objects import log as log_lib
from pm4py.objects.petri.petrinet import PetriNet
from pm4py.objects.random_variables.random_variable import RandomVariable
from pm4py.visualization.petrinet.util import performance_map

PARAM_ACTIVITY_KEY = pm4py.util.constants.PARAMETER_CONSTANT_ACTIVITY_KEY
PARAM_TIMESTAMP_KEY = pm4py.util.constants.PARAMETER_CONSTANT_TIMESTAMP_KEY


def get_map_from_log_and_net(log, net, initial_marking, final_marking, parameters=None):
    """
    Get transition stochastic distribution map given the log and the Petri net

    Parameters
    -----------
    log
        Event log
    net
        Petri net
    initial_marking
        Initial marking of the Petri net
    final_marking
        Final marking of the Petri net
    parameters
        Parameters of the algorithm, including:
            PARAM_ACTIVITY_KEY -> activity name
            PARAM_TIMESTAMP_KEY -> timestamp key

    Returns
    -----------
    stochastic_map
        Map that to each transition associates a random variable
    """
    stochastic_map = {}

    if parameters is None:
        parameters = {}

    activity_key = parameters[
        PARAM_ACTIVITY_KEY] if PARAM_ACTIVITY_KEY in parameters else log_lib.util.xes.DEFAULT_NAME_KEY
    timestamp_key = parameters[PARAM_TIMESTAMP_KEY] if PARAM_TIMESTAMP_KEY in parameters else "time:timestamp"

    parameters_variants = {PARAM_ACTIVITY_KEY: activity_key}
    variants_idx = variants_module.get_variants_from_log_trace_idx(log, parameters=parameters_variants)
    variants = variants_module.convert_variants_trace_idx_to_trace_obj(log, variants_idx)

    parameters_tr = {PARAM_ACTIVITY_KEY: activity_key, "variants": variants}

    # do the replay
    aligned_traces = token_replay.apply(log, net, initial_marking, final_marking, parameters=parameters_tr)

    element_statistics = performance_map.single_element_statistics(log, net, initial_marking,
                                                                   aligned_traces, variants_idx,
                                                                   activity_key=activity_key,
                                                                   timestamp_key=timestamp_key)

    for el in element_statistics:
        if type(el) is PetriNet.Transition and "performance" in element_statistics[el]:
            values = element_statistics[el]["performance"]

            R = RandomVariable()
            R.calculate_parameters(values)

            no_of_times_enabled = element_statistics[el]['no_of_times_enabled']
            no_of_times_activated = element_statistics[el]['no_of_times_activated']

            if no_of_times_enabled > 0:
                R.set_weight(float(no_of_times_activated) / float(no_of_times_enabled))
            else:
                R.set_weight(0.0)

            stochastic_map[el] = R

    return stochastic_map
