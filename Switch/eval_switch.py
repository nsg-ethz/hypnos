import sys
sys.path.insert(1, '../Lib/')
import lib, pickle, os
import networkx as nx
import numpy as np


# script to evaluate the algorithm on the SWITCH data

# start and end timestep number
start = int(sys.argv[1])
end = int(sys.argv[2])

# configuration
scales = [1,2,5,10]                         # scales to use
bundle = True                               # include bundle optimization
two_connectedness = False                   # two connectedness option
budget_scale = 1                            # scale of reroute budget

TM_path = "../TM/Switch"                    # path to the traffic matrix files
result_path = "../Results"                  # path to the result files

# setup variables
timesteps = list(range(start, end))
problems = {}
result = []
total = {}


# iterate over all scales and timesteps
for scale in scales:

    for i in timesteps:
        # skip the problematic timesteps(no data collected) in our dataset
        if i >= 10029 and i <= 10041:
            continue
        print(f"timestep: {i}, scale: {scale}")
        ts = 1703858100 + 300 * i


        links_off = []

        # load networkx graph and traffic matrix from the file
        with open(f"{TM_path}/scale_{scale}/{ts}_{scale}.pkl", "rb") as file:
            G, t = pickle.load(file)
            if t.ndim == 1:
                t = t[:,np.newaxis]

        topo_graph = nx.MultiGraph()
        topo_graph.add_nodes_from(G.nodes())
        sleep_edges = []

        for edge in G.edges:
            if topo_graph.has_edge(edge[1],edge[0],tuple(reversed(edge[2]))):
                continue
            else:
                if topo_graph.has_edge(edge[0], edge[1], key=edge[2]):
                    print(edge)
                    continue
                topo_graph.add_edge(edge[0], edge[1], key=edge[2], sleep=False, max_bw=G[edge[0]][edge[1]][edge[2]]["max_bw"])
                sleep_edges.append(edge)
        

        G = lib.get_load(G, topo_graph, t, check_sleep=False)
        
        budget = lib.get_reroute_budget(G)
        budget = budget_scale*budget
        print(f"Budget: {budget}")

        result.append(dict(config={"scale":scale,"timestep":ts, "reroute_budget": budget, "bundle": bundle, "two_connectedness": two_connectedness, "budget_scale": budget_scale}))

        if bundle:
            bundles = lib.check_bundles(sleep_edges, G, topo_graph, link_margin=0.2)
        
        edges_to_sleep = lib.get_links_to_sleep(sleep_edges, G, link_margin=0.2)

        edges_to_sleep = lib.optimize_link_sleep(edges_to_sleep, G)
        
        # setup two connectedness option
        if two_connectedness:
            H = nx.Graph(topo_graph)
            two_topo_graph = topo_graph.copy()
            component = sorted(list(nx.k_edge_components(H, 2)),key=len,reverse=True)[0]

        # check connectedness and reroute budget
        for sleep_edge, score in edges_to_sleep:
            if budget - score < 0:
                break
            if lib.check_connectedness(sleep_edge, topo_graph) == False:
                continue

            budget -= score
            topo_graph[sleep_edge[0]][sleep_edge[1]][sleep_edge[2]]["sleep"] = True
            links_off.append(sleep_edge)
        
        if two_connectedness:
            two_links_off = []
            for sleep_edge in links_off:
                if lib.check_two_connectedness(sleep_edge, two_topo_graph,component) == False:
                    continue
                two_topo_graph[sleep_edge[0]][sleep_edge[1]][sleep_edge[2]]["sleep"] = True
                two_links_off.append(sleep_edge)
            links_off = two_links_off
            

        if bundle:
            lib.bundle_to_links(bundles, G, topo_graph, links_off)

        result[-1]["sleep_edges"] = links_off
        result[-1]["ol_now"] = lib.check_overload(f"{TM_path}/scale_{scale}/{ts}_{scale}.pkl", topo_graph)
        result[-1]["ol_next"] = lib.check_overload(f"{TM_path}/scale_{scale}/{ts+300}_{scale}.pkl", topo_graph)


# calculate the results
for element in result:
    ol_now = (len(element["ol_now"]["ol_sleep"])-len(element["ol_now"]["ol_active"]), len(element["ol_now"]["ol_sleep_1"])-len(element["ol_now"]["ol_active_1"]))
    ol_next = (len(element["ol_next"]["ol_sleep"])-len(element["ol_next"]["ol_active"]), len(element["ol_next"]["ol_sleep_1"])-len(element["ol_next"]["ol_active_1"]))
    element["result"] = {"scale": element["config"]["scale"] ,"ol_now":ol_now,"ol_next": ol_next, "no_sleep": len(element["sleep_edges"])}


# write results to the file and select path depending on experiment
if two_connectedness:
    savepath = f"{result_path}/switch_2"
else:
    if budget_scale != 1:
        savepath = f"{result_path}/switch_budget_{budget_scale}"
    else:
        savepath = f"{result_path}/switch"

if not os.path.exists(savepath):
            os.makedirs(savepath)

lib.save_result(savepath, result)

