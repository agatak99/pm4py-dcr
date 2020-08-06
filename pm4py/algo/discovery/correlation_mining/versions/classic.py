from pm4py.util import exec_utils
from enum import Enum
from pm4py.util import constants, xes_constants
from pm4py.objects.conversion.log import converter
from pm4py.objects.log.log import EventStream, Event
from pm4py.algo.discovery.correlation_mining import util as cm_util
from statistics import mean
import numpy as np
import pandas as pd


class Parameters(Enum):
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY
    TIMESTAMP_KEY = constants.PARAMETER_CONSTANT_TIMESTAMP_KEY
    INDEX_KEY = "index_key"


DEFAULT_INDEX_KEY = "@@@index"


def apply(stream, parameters=None):
    """
    Apply the correlation miner to an event stream
    (other types of logs are converted to that)

    The approach is described in:
    Pourmirza, Shaya, Remco Dijkman, and Paul Grefen. "Correlation miner: mining business process models and event
    correlations without case identifiers." International Journal of Cooperative Information Systems 26.02 (2017):
    1742002.

    Parameters
    ---------------
    stream
        Event stream
    parameters
        Parameters of the algorithm

    Returns
    ---------------
    dfg
        DFG
    performance_dfg
        Performance DFG (containing the estimated performance for the arcs)
    """
    if parameters is None:
        parameters = {}

    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)
    timestamp_key = exec_utils.get_param_value(Parameters.TIMESTAMP_KEY, parameters,
                                               xes_constants.DEFAULT_TIMESTAMP_KEY)
    index_key = exec_utils.get_param_value(Parameters.INDEX_KEY, parameters, DEFAULT_INDEX_KEY)

    if type(stream) is pd.DataFrame:
        # keep only the two columns before conversion
        stream = stream[[activity_key, timestamp_key]]
    stream = converter.apply(stream, variant=converter.TO_EVENT_STREAM, parameters=parameters)
    transf_stream = EventStream()
    for idx, ev in enumerate(stream):
        transf_stream.append(
            Event({activity_key: ev[activity_key], timestamp_key: ev[timestamp_key].timestamp(), index_key: idx}))
    transf_stream = sorted(transf_stream, key=lambda x: (x[timestamp_key], x[index_key]))
    activities = sorted(list(set(x[activity_key] for x in transf_stream)))
    activities_grouped = {x: [y for y in transf_stream if y[activity_key] == x] for x in activities}
    activities_counter = {x: len(y) for x,y in activities_grouped.items()}
    PS_matrix = get_precede_succeed_matrix(activities, activities_grouped, timestamp_key)
    duration_matrix = get_duration_matrix(activities, activities_grouped, timestamp_key)
    C_matrix = cm_util.get_c_matrix(PS_matrix, duration_matrix, activities, activities_counter)
    dfg, performance_dfg = cm_util.resolve_LP(C_matrix, duration_matrix, activities, activities_counter)
    return dfg, performance_dfg


def get_precede_succeed_matrix(activities, activities_grouped, timestamp_key):
    """
    Calculates the precede succeed matrix

    Parameters
    ---------------
    activities
        Ordered list of activities of the log
    activities_grouped
        Grouped list of activities
    timestamp_key
        Timestamp key

    Returns
    ---------------
    precede_succeed_matrix
        Precede succeed matrix
    """
    ret = np.zeros((len(activities), len(activities)))
    for i in range(len(activities)):
        ai = [x[timestamp_key] for x in activities_grouped[activities[i]]]
        for j in range(i + 1, len(activities)):
            aj = [x[timestamp_key] for x in activities_grouped[activities[j]]]
            k = 0
            z = 0
            count = 0
            while k < len(ai):
                while z < len(aj):
                    if ai[k] < aj[z]:
                        break
                    z = z + 1
                count = count + (len(aj) - z)
                k = k + 1
            ret[i, j] = count / float(len(ai) * len(aj))
            ret[j, i] = 1.0 - ret[i, j]

    return ret


def get_duration_matrix(activities, activities_grouped, timestamp_key):
    """
    Calculates the duration matrix

    Parameters
    ---------------
    activities
        Ordered list of activities of the log
    activities_grouped
        Grouped list of activities
    timestamp_key
        Timestamp key

    Returns
    ---------------
    duration_matrix
        Duration matrix
    """
    # greedy algorithm
    ret = np.zeros((len(activities), len(activities)))
    for i in range(len(activities)):
        ai = [x[timestamp_key] for x in activities_grouped[activities[i]]]
        for j in range(len(activities)):
            if not i == j:
                aj = [x[timestamp_key] for x in activities_grouped[activities[j]]]
                k = 0
                z = 0
                times0 = []
                while k < len(ai):
                    while z < len(aj):
                        if ai[k] < aj[z]:
                            times0.append((aj[z] - ai[k]))
                            z = z + 1
                            break
                        z = z + 1
                    k = k + 1
                times0 = mean(times0) if times0 else 0
                k = len(ai) - 1
                z = len(aj) - 1
                times1 = []
                while z >= 0:
                    while k >= 0:
                        if ai[k] < aj[z]:
                            times1.append((aj[z] - ai[k]))
                            k = k - 1
                            break
                        k = k - 1
                    z = z - 1
                times1 = mean(times1) if times1 else 0
                ret[i, j] = min(times0, times1)
    return ret


