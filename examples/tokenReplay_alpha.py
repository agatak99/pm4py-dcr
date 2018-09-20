import os, sys, inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
import pm4py
from pm4py.algo.discovery.alpha import factory as alpha_factory
from pm4py.entities.log.importer.xes import factory as xes_importer
from pm4py.entities.petri import visualize as pn_viz
from pm4py.algo.conformance.tokenreplay import factory as token_replay
import time


def execute_script():
    logPath = os.path.join("..", "tests", "inputData", "running-example.xes")
    log = xes_importer.import_log(logPath)
    # log = xes_importer.import_from_path_xes('a32f0n00.xes')
    net, marking, final_marking = alpha_factory.apply(log)
    for place in marking:
        print("initial marking " + place.name)
    for place in final_marking:
        print("final marking " + place.name)
    gviz = pn_viz.graphviz_visualization(net, initial_marking=marking, final_marking=final_marking)
    gviz.view()
    time0 = time.time()
    print("started token replay")
    aligned_traces = token_replay.apply(log, net, marking, final_marking)
    fit_traces = [x for x in aligned_traces if x['tFit']]
    perc_fitness = 0.00
    if len(aligned_traces) > 0:
        perc_fitness = len(fit_traces) / len(aligned_traces)
    print("perc_fitness=", perc_fitness)


if __name__ == "__main__":
    execute_script()
