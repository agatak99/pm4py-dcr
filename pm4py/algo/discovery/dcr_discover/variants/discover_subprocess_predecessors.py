import pm4py

from copy import deepcopy
from pm4py.algo.discovery.dcr_discover.variants import discover_basic as alg
from pm4py.objects.dcr import semantics as dcr_semantics


def apply(log, findAdditionalConditions=True, discardSelfInPredecessors=True, inBetweenRels=False, **kwargs):
    event_log = log
    basic_dcr, la = alg.apply(event_log, findAdditionalConditions=findAdditionalConditions)
    log_abstraction = deepcopy(la)
    events = log_abstraction['events']
    if discardSelfInPredecessors:
        for e in events:
            if e in log_abstraction['predecessor'] and e in log_abstraction['predecessor'][e]:
                log_abstraction['predecessor'][e].discard(e)
            if e in log_abstraction['successor'] and e in log_abstraction['successor'][e]:
                log_abstraction['successor'][e].discard(e)

    cluster_dict = {}
    keys = sorted(log_abstraction['predecessor'].keys())
    for k in keys:
        preds_set = frozenset(sorted(log_abstraction["predecessor"][k]))
        if preds_set in cluster_dict.keys():
            cluster_dict[preds_set].add(k)
        else:
            cluster_dict[preds_set] = set([k])

    subprocesses = {}
    subprocess_notation = 'S'
    i = 0
    for k, v in cluster_dict.items():
        if len(v) > 1:
            subprocesses[f'{subprocess_notation}{i}'] = frozenset(v)
            i = i + 1

    subprocess_log = get_subprocess_log(event_log, subprocesses)
    # now run the dcr graph with the subprocess events replaced as the subprocess
    subprocess_dcr, la = alg.apply(subprocess_log, findAdditionalConditions=findAdditionalConditions)

    final_dcr = get_final_dcr(basic_dcr, subprocess_dcr, subprocesses, inBetweenRels=inBetweenRels)
    return final_dcr, subprocess_log


def get_subprocess_log(event_log, subprocesses):
    sp_dcr_dict = {}
    for name, subprocess in subprocesses.items():
        sp_dcr_dict[name] = {'events': subprocess,
                             'conditionsFor': {},
                             'milestonesFor': {},
                             'responseTo': {},
                             'includesTo': {},
                             'excludesTo': {},
                             'marking': {'included': subprocess,
                                         'pending': set(),
                                         'executed': set()}
                             }

    subprocess_log = pm4py.objects.log.obj.EventLog()
    trace: pm4py.objects.log.obj.Trace
    event: pm4py.objects.log.obj.Event
    for trace in event_log:
        # only replace with the subprocess when the subprocess is accepting
        sp_trace = pm4py.objects.log.obj.Trace()
        for event in trace:
            # set all subprocess dcr graphs to their initial state
            sp_dcr_instance = deepcopy(sp_dcr_dict)
            sp_event = None
            for name, sp in subprocesses.items():
                if event['concept:name'] in sp:
                    # if the event is in the subprocess then execute it within the subprocess model
                    executed = dcr_semantics.execute(event['concept:name'],
                                                     sp_dcr_instance[name])  # TODO: check if it always executes
                    accepting = dcr_semantics.is_accepting(sp_dcr_instance[name])
                    if accepting & executed:
                        # if the event did execute and is accepting then reset the subprocess to its initial marking
                        sp_dcr_instance[name] = deepcopy(sp_dcr_dict[name])
                        # also replace the event with the subprocess in the new event log
                        event['concept:name'] = name
                        sp_event = event
            if not sp_event:
                sp_event = event
            sp_trace.append(sp_event)
        subprocess_log.append(sp_trace)
    return subprocess_log


def get_final_dcr(basic_dcr, sp_dcr, subprocesses, inBetweenRels=True):
    final_dcr = {
        'events': {},
        'conditionsFor': {},
        'milestonesFor': {},
        'responseTo': {},
        'includesTo': {},
        'excludesTo': {},
        'marking': {'executed': set(),
                    'included': set(),
                    'pending': set()
                    },
        'conditionsForDelays': {},
        'responseToDeadlines': {},
        'subprocesses': {}
    }
    rels = ['conditionsFor', 'responseTo', 'includesTo', 'excludesTo']
    for k in sp_dcr.keys():
        if k in basic_dcr.keys():
            match k:
                case 'events':
                    final_dcr[k] = sp_dcr[k].union(basic_dcr[k])
                case 'marking':
                    final_dcr[k]['executed'] = sp_dcr[k]['executed'].union(basic_dcr[k]['executed'])
                    final_dcr[k]['included'] = sp_dcr[k]['included'].union(basic_dcr[k]['included'])
                    final_dcr[k]['pending'] = sp_dcr[k]['pending'].union(basic_dcr[k]['pending'])
                case 'conditionsFor' | 'responseTo' | 'includesTo' | 'excludesTo':
                    # comment this if debugging the i2e and e2i relations
                    final_dcr[k] = deepcopy(sp_dcr[k])
                    # in between the internal to external and external to internal
                    if inBetweenRels:
                        for sp_name, internal_events in subprocesses.items():
                            # print('e2i')
                            external_events = basic_dcr['events'].difference(internal_events)
                            for external_event in external_events:
                                if external_event in basic_dcr[k] and external_event in sp_dcr[k]:
                                    e2i = basic_dcr[k][external_event].intersection(internal_events)
                                    e2_sp = sp_dcr[k][external_event].intersection({sp_name})
                                    if len(e2_sp) == 0 and len(e2i) > 0:
                                        # print(f'{k} {external_event}')
                                        # print(e2i)
                                        if external_event not in final_dcr[k]:
                                            final_dcr[k][external_event] = set()
                                        final_dcr[k][external_event] = final_dcr[k][external_event].union(e2i)
                            # print('i2e')
                            for internal_event in internal_events:
                                if internal_event in basic_dcr[k] and sp_name in sp_dcr[k]:
                                    i2e = basic_dcr[k][internal_event].intersection(external_events)
                                    sp2e = sp_dcr[k][sp_name].intersection(external_events)
                                    i2e_not_sp2e = i2e.difference(sp2e)
                                    if len(i2e_not_sp2e) > 0:
                                        # print(f'{k} {internal_event}')
                                        # print(i2e_not_sp2e)
                                        if internal_event not in final_dcr[k]:
                                            final_dcr[k][internal_event] = set()
                                        final_dcr[k][internal_event] = final_dcr[k][internal_event].union(i2e_not_sp2e)

    for name, sp_events in subprocesses.items():
        final_dcr['subprocesses'][name] = set(sp_events)
    return final_dcr
