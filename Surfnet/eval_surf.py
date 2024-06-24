import sys
sys.path.insert(1, '../Lib/')
import lib, pickle, sys, datetime, os
import networkx as nx
import numpy as np


# script to evaluate the algorithm on the Surf data

# start and end timestep number
start = int(sys.argv[1])
end = int(sys.argv[2])

# configuration
scales = [1,2,5,10]                 # scales to use
two_connectedness = False           # two connectedness option
bundle = True                       # include bundle optimization
budget_scale = 1                    # scale of reroute budget

result_path = "../Results"          # path to the traffic matrix files
TM_path = "../TM/Surfnet"           # path to the result files

# setup variables
timesteps = list(range(start, end))
problems = {}
result = []
total = {}

for scale in scales:

    for i in timesteps:

        print(f"timestep: {i}, scale: {scale}")

        ts = 1711922700 + 300 * i

        timestep = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ')
        links_off = []

        # load networkx graph and traffic matrix from the file
        with open(f"{TM_path}/scale_{scale}/{timestep}_{scale}.pkl", "rb") as file:
            G, t = pickle.load(file)
            if t.ndim == 1:
                t = t[:,np.newaxis]


        topo_graph = nx.MultiGraph()
        topo_graph.add_nodes_from(G.nodes())

        for edge in list(G.edges):
            if G[edge[0]][edge[1]][edge[2]]["max_bw"]==0:
                G.remove_edge(edge[0], edge[1], key=edge[2])

        for edge in G.edges:
            if topo_graph.has_edge(edge[1],edge[0],tuple(reversed(edge[2]))):
                continue
            else:
                if topo_graph.has_edge(edge[0], edge[1], key=edge[2]):
                    continue
                topo_graph.add_edge(edge[0], edge[1], key=edge[2], sleep=False, max_bw=G[edge[0]][edge[1]][edge[2]]["max_bw"])


        G = lib.get_load(G, topo_graph, t, check_sleep=False)
        nodes = max(nx.connected_components(topo_graph),key=len)
        topo_graph.remove_nodes_from([n for n in topo_graph if n not in set(nodes)])
        G.remove_nodes_from([n for n in G if n not in set(nodes)])
        sleep_edges = list(topo_graph.edges)

        budget = lib.get_reroute_budget(G)
        budget = budget_scale*budget
        print(f"Budget: {budget}")

        result.append(dict(config={"scale":scale,"timestep":ts,"reroute_budget": budget, "two_connectedness": two_connectedness, "bundle": bundle, "budget_scale": budget_scale}))
        if bundle:
            bundles = lib.check_bundles(sleep_edges, G, topo_graph, link_margin=0.2)

        edges_to_sleep = lib.get_links_to_sleep(sleep_edges, G, link_margin=0.2)

        edges_to_sleep = lib.optimize_link_sleep(edges_to_sleep, G)

        # setup two connectedness option
        if two_connectedness:
            H = nx.Graph(topo_graph)
            component = sorted(list(nx.k_edge_components(H, 2)),key=len,reverse=True)[0]
            two_topo_graph = topo_graph.copy()

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
        
        result[-1]["ol_now"] = lib.check_overload(f"{TM_path}/scale_{scale}/{timestep}_{scale}.pkl", topo_graph)
        timestep_2 = datetime.datetime.fromtimestamp(ts+300).strftime('%Y-%m-%dT%H:%M:%SZ')
        result[-1]["ol_next"] = lib.check_overload(f"{TM_path}/scale_{scale}/{timestep_2}_{scale}.pkl", topo_graph)


# calculate the results
for element in result:
    ol_now = (len(element["ol_now"]["ol_sleep"])-len(element["ol_now"]["ol_active"]), len(element["ol_now"]["ol_sleep_1"])-len(element["ol_now"]["ol_active_1"]))
    ol_next = (len(element["ol_next"]["ol_sleep"])-len(element["ol_next"]["ol_active"]), len(element["ol_next"]["ol_sleep_1"])-len(element["ol_next"]["ol_active_1"]))
    element["result"] = {"scale": element["config"]["scale"] ,"ol_now":ol_now,"ol_next": ol_next, "no_sleep": len(element["sleep_edges"])}


# write results to the file and select path depending on experiment
if two_connectedness:
    savepath = f"{result_path}/surf_2"
else:
    if budget_scale != 1:
        savepath = f"{result_path}/surf_budget_{budget_scale}"
    else:
        savepath = f"{result_path}/surf"

if not os.path.exists(savepath):
            os.makedirs(savepath)

lib.save_result(savepath, result)

