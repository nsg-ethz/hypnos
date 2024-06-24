import os,time,pickle,json, csv

# set appropriatly to not create more threads than available cores
os.environ["MKL_NUM_THREADS"] = "2" 
os.environ["NUMEXPR_NUM_THREADS"] = "2" 
os.environ["OMP_NUM_THREADS"] = "2" 

import networkx as nx
import numpy as np
import tomogravity as tg


# helper functions for Surfnet and Switch


# creates topology from switch topology file (.txt)
def create_topo_switch(topopath):

    topo = dict()
    with open(topopath,"r") as file:
        topofile = list(csv.reader(file, delimiter=","))
        #print(f" header: {topofile[0]}")

    # iterate through entries and build dictionary containing the topology
    for element in topofile[1:]:
        router1 = element[0].removeprefix("swi")
        intf1 = element[1].replace("/","_").lower()
        router2 = element[2].removeprefix("swi")
        intf2 = element[3].replace("/","_").lower()
        speed = float(element[4])
        weight = int(element[5])

        if speed == 0:
            print((router1, intf1, router2, intf2))
            continue
        topo[(router1, intf1, router2, intf2)] = [speed, weight]
    return topo


def create_topo_surf(topopath):
    topo = nx.MultiDiGraph()
    with open(topopath,"r") as file:
        topofile = list(csv.reader(file, delimiter=","))
    
    # iterate through entries and build dictionary containing the topology
    for element in topofile[1:]:
        router1 = element[0]
        intf1 = element[1]
        router2 = element[2]
        intf2 = element[3]
        if element[4] == "":
            continue
        else:
            speed = int(element[4])

        if element[5] == "":
            weight = 2000
        else:
            weight = int(element[5])
        
        topo.add_edge(router1, router2, key=(intf1,intf2), weight=weight, speed=speed)
        topo.add_edge(router2, router1, key=(intf2,intf1), weight=weight, speed=speed)
    return topo



# helper function to read from the SWITCH dataset
def read_file_switch(filepath, timestep):

    # check if file exists
    if os.path.isfile(filepath):
        with open(filepath, "r") as file:
            contents = list(csv.reader(file, delimiter=","))
        index = 1
        content = contents[index]

        # iterate through content until timestep is found
        while float(content[0]) != timestep:
            index = index + 1
            if index >= len(contents):
                return []
            content = contents[index]
        
        content = contents[index]
        if content[1:3] == ['','']:
            if index == 1:
                return []
            content = content[0:1] + contents[index-1][1:]
            
        if content[1:3] == ['','']:
            return []

            
        content = [float(x) if x != "" else 0 for x in content]

    # if file doesn't exist return empty list
    else:
        #print(f"file {filepath} not found")
        content = []
    return content



# create networkx graph from topofile and link loads
def create_graph_switch(topo, linkdatapath, timestep, scale = 1, max_util = 0.7): 

    link_util = {}
    link = []
    nodes = set()

    # for every link read the link loads
    for key, element in topo.items():
        
        filepath1 = f"{linkdatapath}/swi{key[0]}/{key[1]}.csv"
        content1 = read_file_switch(filepath1, timestep)
        filepath2 = f"{linkdatapath}/swi{key[2]}/{key[3]}.csv"
        content2 = read_file_switch(filepath2, timestep)

        # if there is no value go to next entry
        if len(content1) == 0 and len(content2) == 0:
            continue
        else:
            # fill value if only one side is available
            if len(content1) == 0:
                content1 = content2
            if len(content2) == 0:
                content2 = content1

            if content1[1] == 0 or content1[2] == 0:
                print(f"{key} zero value")
            
            if content1[0]-content2[0] != 0:
                print("not the same timestep")

            # take the average of both sides
            tx = (content1[2]+content2[1])/2
            rx = (content1[1]+content2[2])/2

            link_util[key] = [tx*(10**(-9))*8, rx*(10**(-9))*8, element[0]*10**(-9), element[1]]
            link.append(key)
            nodes.add(key[0])
            nodes.add(key[2])

    # create networkx graph
    G = nx.MultiDiGraph()
    G.add_nodes_from(nodes)
    
    # add edges to graph
    for key, element in link_util.items():

        if element[0] * scale < max_util * element[2]:
            G.add_edge(key[0], key[2], key=(key[1],key[3]), weight=element[3], 
                       usage=element[0]*scale, avail=element[2]-element[0]*scale, max_bw=element[2])
        else:
            G.add_edge(key[0], key[2], key=(key[1],key[3]), weight=element[3],
                       usage=element[2]*max_util, avail=element[2]*(1-max_util), max_bw=element[2])

        if element[1] * scale < max_util * element[2]:
            G.add_edge(key[2], key[0], key=(key[3],key[1]), weight=element[3],
                       usage=element[1]*scale, avail=element[2]-element[1]*scale, max_bw=element[2])
        else:
            G.add_edge(key[2], key[0], key=(key[3],key[1]), weight=element[3],
                       usage=element[2]*max_util, avail=element[2]*(1-max_util), max_bw=element[2])

    return G


# create the networkx graph for the surf network
def create_graph_surf(links_path, topo, scale=1, max_util=0.7):

    with open(links_path, "r") as file:
        links = list(csv.reader(file, delimiter=","))
    link_util = {}
    for i, link in enumerate(links):
        if i == 0:
            #print(link)
            continue
        else:
            if topo.has_edge(link[0],link[1]):

                for key in topo[link[0]][link[1]].keys():
                    if key[1] == link[2]:
                        for link_2 in links:
                            if link_2[0] == link[1] and link_2[1] == link[0] and link_2[2] == key[0]:
                                link_util_key = (link[0],key[0],link[1],key[1])
                                tx = (int(link[4])+int(link_2[3]))/2
                                rx = (int(link[3])+int(link_2[4]))/2
                                speed = topo[link[0]][link[1]][key]["speed"]
                                link_util[link_util_key] = [tx*(10**(-9)), rx*(10**(-9)), speed*10**(-9)]

                        link_util_key = (link[0],key[0],link[1],key[1])
                        if link_util_key not in link_util.keys():
                            tx = int(link[4])
                            rx = int(link[3])
                            speed = topo[link[0]][link[1]][key]["speed"]
                            link_util[link_util_key] = [tx*(10**(-9)), rx*(10**(-9)), speed*10**(-9)]

    G = topo.copy()

    for key, element in link_util.items():
        if (key[0],key[2],(key[1],key[3])) in G.edges:
            if element[0] * scale < max_util * element[2]:
                usage=element[0]*scale
                avail=element[2]-element[0]*scale
                max_bw=element[2]
            else:
                usage=element[2]*max_util
                avail=element[2]*(1-max_util)
                max_bw=element[2]
        
            G[key[0]][key[2]][(key[1],key[3])]["usage"] = usage
            G[key[0]][key[2]][(key[1],key[3])]["avail"] = avail
            G[key[0]][key[2]][(key[1],key[3])]["max_bw"] = max_bw

        if (key[2],key[0],(key[3],key[1])) in G.edges:
            if element[1] * scale < max_util * element[2]:
                usage=element[1]*scale
                avail=element[2]-element[1]*scale
                max_bw=element[2]
            else:
                usage=element[2]*max_util
                avail=element[2]*(1-max_util)
                max_bw=element[2]

            G[key[2]][key[0]][(key[3],key[1])]["usage"] = usage
            G[key[2]][key[0]][(key[3],key[1])]["avail"] = avail
            G[key[2]][key[0]][(key[3],key[1])]["max_bw"] = max_bw

    cnt = 0
    for edge in list(G.edges):
        if "usage" not in G[edge[0]][edge[1]][edge[2]].keys():
            cnt += 1
            G.remove_edge(edge[0],edge[1],edge[2])
    
    isolated = list(nx.isolates(G))

    print(f"deleted {len(isolated)} nodes that were not connected")
    print(f"deleted {cnt} edges where no data was available")

    G.remove_nodes_from(isolated)
    before = len(G.edges)
    nodes = max(nx.strongly_connected_components(G),key=len)
    G.remove_nodes_from([n for n in G if n not in set(nodes)])

    print(f"deleted {before-len(G.edges)} nodes that were not connected")
    return G


# get the load that is going into the router and flowing out of the router
# at the moment just percentage of total traffic
def get_in_out_load(G, perc=0.5):
    load_in = {}
    load_out = {}

    for router in G.nodes:
        
        out = 0
        inp = 0
        internal = []
        neighbors = list(G.neighbors(router))
        
        for neighbor in neighbors:
            tx = 0
            rx = 0

            for intf in G[router][neighbor]:
                out += G[router][neighbor][intf]["usage"]
                tx += G[router][neighbor][intf]["usage"]
                internal.append(intf)

            for intf in G[neighbor][router]:
                inp += G[neighbor][router][intf]["usage"]
                rx += G[neighbor][router][intf]["usage"]

        load_in[router] = out * perc
        load_out[router] = inp * perc
    return load_in, load_out


# get the traffic matrix from the link loads using the tomogravity method
def get_traffic_matrix(G, load_in, load_out):

    A, x, t, tm_g = tg.create_vectors(G, load_in, load_out)

    traffic_matrix = tg.tomogravity(A, x, tm_g, np.sqrt(tm_g))

    loss = np.max(np.abs(np.matmul(A,traffic_matrix[:,np.newaxis])-x))
    
    #print(f"loss before setting entries to 0: {loss}")

    for i, element in enumerate(t):

        if traffic_matrix[i] < 0:

            traffic_matrix[i] = 0

    loss = np.max(np.abs(np.matmul(A,traffic_matrix[:,np.newaxis])-x))

    #print(f"loss after setting entries to 0: {loss}")

    cnt = 0
    while loss > 0.0001 and cnt < 20:

        for index, row in enumerate(A):

            sum = np.matmul(row,traffic_matrix[:,np.newaxis])
            
            if sum[0] != 0:
                factor = x[index]/sum[0]
                traffic_matrix = np.add(traffic_matrix, np.multiply(traffic_matrix, np.sign(row)) * (factor-1))

        loss = np.max(np.abs(np.matmul(A,traffic_matrix)-x))    
        cnt += 1

    print(f"Max loss after optimization: {loss}")
    losses = np.abs(np.matmul(A,traffic_matrix)-x)
    for i, element in enumerate(traffic_matrix):
        t[i] = (t[i], element)

    return t[:,np.newaxis], losses


# check if bundles can be partially shutdown
def check_bundles(sleep_edges, G, topo_graph, link_margin=0.2):

    bundles = []
    checked = set()
    for sleep_edge in sleep_edges:
        
        if (sleep_edge[0],sleep_edge[1]) in checked:
            continue
        checked.add((sleep_edge[0],sleep_edge[1]))
        interfaces = G[sleep_edge[0]][sleep_edge[1]]

        if len(interfaces) > 1:
            weights = {}

            for key, intf in interfaces.items():

                if intf["weight"] in weights.keys():
                    weights[intf["weight"]].append((key,intf))
                else:
                    weights[intf["weight"]] = [(key,intf)]

            for key, values in weights.items():

                if len(values) > 1:
                    values_2 = list(G[sleep_edge[1]][sleep_edge[0]].items())
                    bundles.append(((sleep_edge[0],sleep_edge[1],key),(values,values_2)))

    for key, bundle in bundles:

        t_sum_1, t_sum_2 = 0, 0
        c_sum_1, c_sum_2 = 0, 0
        for i, _ in enumerate(bundle[0]):
            
            t_sum_1 += bundle[0][i][1]["usage"]
            c_sum_1 += bundle[0][i][1]["max_bw"]
            t_sum_2 += bundle[1][i][1]["usage"]
            c_sum_2 += bundle[1][i][1]["max_bw"]
            
            bundle[0][i][1]["sleep"] = True
            bundle[1][i][1]["sleep"] = True

            if t_sum_1/c_sum_1 > (1-link_margin) or t_sum_2/c_sum_2 > (1-link_margin):
                bundle[0][i][1]["sleep"] = False
                bundle[1][i][1]["sleep"] = False

        bundle[0][-1][1]["sleep"] = False
        bundle[1][-1][1]["sleep"] = False
    
    for b_no, (key, bundle) in enumerate(bundles):
        t_sum_1, t_sum_2 = 0, 0
        c_sum_1, c_sum_2 = 0, 0

        for i, _ in enumerate(bundle[0]):

            if bundle[0][i][1]["sleep"] == False:
                c_sum_1 += bundle[0][i][1]["max_bw"]
                c_sum_2 += bundle[1][i][1]["max_bw"]

            t_sum_1 += bundle[0][i][1]["usage"]
            t_sum_2 += bundle[1][i][1]["usage"]

            sleep_edges.remove((key[0],key[1], bundle[0][i][0]))
            topo_graph.remove_edge(key[0],key[1], bundle[0][i][0])
            G.remove_edge(key[0],key[1],bundle[0][i][0])
            G.remove_edge(key[1],key[0],tuple(reversed(bundle[0][i][0])))
        
        G.add_edge(key[0],key[1],key=(f"bundle_{b_no}",f"bundle_{b_no}"), usage=t_sum_1, max_bw=c_sum_1, avail=c_sum_1-t_sum_1, weight=bundle[0][0][1]["weight"])
        G.add_edge(key[1],key[0],key=(f"bundle_{b_no}",f"bundle_{b_no}"), usage=t_sum_2, max_bw=c_sum_2, avail=c_sum_2-t_sum_2, weight=bundle[0][0][1]["weight"])
        sleep_edges.append((key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}")))
        topo_graph.add_edge(key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}"), sleep=False, max_bw=c_sum_1)

    return bundles


# exchange bundles for physical links again
def bundle_to_links(bundles, G, topo_graph, links_off):

    for b_no, (key, bundle) in enumerate(bundles):

        if (key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}")) in links_off:

            links_off.remove((key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}")))
            topo_graph.remove_edge(key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}"))
            G.remove_edge(key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}"))

            for i, _ in enumerate(bundle[0]):

                links_off.append((key[0],key[1], bundle[0][i][0]))
                topo_graph.add_edge(key[0], key[1], key=bundle[0][i][0], sleep=True, max_bw=bundle[0][i][1]["max_bw"])
                G.add_edge(key[0], key[1], key=bundle[0][i][0], usage=bundle[0][i][1]["usage"], avail=bundle[0][i][1]["avail"], max_bw=bundle[0][i][1]["max_bw"])
                G.add_edge(key[1], key[0], key=tuple(reversed(bundle[0][i][0])), usage=bundle[1][i][1]["usage"], avail=bundle[1][i][1]["avail"], max_bw=bundle[1][i][1]["max_bw"])

        else:
            topo_graph.remove_edge(key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}"))
            G.remove_edge(key[0],key[1],(f"bundle_{b_no}",f"bundle_{b_no}"))
            G.remove_edge(key[1],key[0],tuple(reversed((f"bundle_{b_no}",f"bundle_{b_no}"))))

            for i, _ in enumerate(bundle[0]):

                if bundle[0][i][1]["sleep"] == True:
                    links_off.append((key[0],key[1], bundle[0][i][0]))

                topo_graph.add_edge(key[0], key[1], key=bundle[0][i][0], sleep=False, max_bw=bundle[0][i][1]["max_bw"])
                G.add_edge(key[0], key[1], key=bundle[0][i][0], usage=bundle[0][i][1]["usage"], avail=bundle[0][i][1]["avail"], max_bw=bundle[0][i][1]["max_bw"])
                G.add_edge(key[1], key[0], key=tuple(reversed(bundle[0][i][0])), usage=bundle[1][i][1]["usage"], avail=bundle[1][i][1]["avail"], max_bw=bundle[1][i][1]["max_bw"])
    return


# algorithm to decide which links can sleep
def get_links_to_sleep(sleep_edges, G, link_margin=0.2):

    edges_to_sleep = []

    for sleep_edge in sleep_edges:
        minimum = [0] * len(sleep_edge)

        for i, node in enumerate(sleep_edge[:2]):
            
            if node not in G.nodes():
                break
            min_avail_list = []

            for neigh in nx.neighbors(G, node):
                
                if neigh in sleep_edge:
                    for intf in G[node][neigh]:
                        if intf == sleep_edge[2] or tuple(reversed(intf)) == sleep_edge[2]:
                            continue
                        
                        margin = G[node][neigh][intf]["max_bw"] * link_margin
                        min_avail_list.append(max(0, G[node][neigh][intf]["avail"]-margin))
                    
                
                for intf in G[node][neigh]:
                    margin = G[node][neigh][intf]["max_bw"] * link_margin
                    min_avail_list.append(max(0, G[node][neigh][intf]["avail"]-margin))

            if len(min_avail_list) == 0:
                break
            minimum[i] = min(min_avail_list)

        if G[sleep_edge[0]][sleep_edge[1]][sleep_edge[2]]["usage"]/G[sleep_edge[0]][sleep_edge[1]][sleep_edge[2]]["max_bw"] > (1-link_margin) or G[sleep_edge[1]][sleep_edge[0]][tuple(reversed(sleep_edge[2]))]["usage"]/G[sleep_edge[1]][sleep_edge[0]][tuple(reversed(sleep_edge[2]))]["max_bw"] > (1-link_margin):
            continue

        if G[sleep_edge[0]][sleep_edge[1]][sleep_edge[2]]["usage"] < minimum[0] and G[sleep_edge[1]][sleep_edge[0]][tuple(reversed(sleep_edge[2]))]["usage"] < minimum[1]:
            edges_to_sleep.append(sleep_edge)
        
    return edges_to_sleep




# optimize the links to sleep acording to their absolute usage
def optimize_link_sleep(edges_to_sleep, G):

    score = [None] * len(edges_to_sleep)

    for index, edge in enumerate(edges_to_sleep):
        score1 = G[edge[0]][edge[1]][edge[2]]["usage"]
        score2 = G[edge[1]][edge[0]][tuple(reversed(edge[2]))]["usage"]
        score[index] = (score1 + score2, edge)
    
    score.sort()
    opt_edges_to_sleep = []

    for score, edge in score:
        opt_edges_to_sleep.append((edge,score))
    
    return opt_edges_to_sleep


# check if the topology is still connected after link is put to sleep
def check_connectedness(sleep_edge, topo_graph):
    H=topo_graph.copy()

    for edge in list(H.edges):

        if H[edge[0]][edge[1]][edge[2]]["sleep"] == True:
            H.remove_edge(edge[0],edge[1],edge[2])
    
    H.remove_edge(sleep_edge[0],sleep_edge[1],sleep_edge[2])

    return nx.is_connected(H)


# check if the component is still connected after link is put to sleep
def check_two_connectedness(sleep_edge, topo_graph, component):
    H=topo_graph.copy()

    for edge in list(H.edges):
        if H[edge[0]][edge[1]][edge[2]]["sleep"] == True:
            H.remove_edge(edge[0],edge[1],edge[2])
    
    if len(H[sleep_edge[0]][sleep_edge[1]]) > 1:
        return True
    
    H = nx.Graph(H)
    H.remove_nodes_from([n for n in H if n not in set(component)])

    if H.has_edge(sleep_edge[0],sleep_edge[1]):
        H.remove_edge(sleep_edge[0],sleep_edge[1])
    else:
        return False
    
    return nx.is_k_edge_connected(H,2)


# get utilization in the network using the active topology and traffic matrix
def get_load(G, topo_graph, t, check_sleep=True):

    active_topology = nx.MultiDiGraph()
    for edge in G.edges:
        if topo_graph.has_edge(edge[0], edge[1], key=edge[2]) or topo_graph.has_edge(edge[1], edge[0], key=tuple(reversed(edge[2]))):
            pass
        else:
            max_bw = G[edge[0]][edge[1]][edge[2]]["max_bw"]
            if max_bw == 0:
                continue
            topo_graph.add_edge(edge[0], edge[1], key=edge[2], sleep=False, max_bw=max_bw)


    for edge in topo_graph.edges:

        if edge not in G.edges:
            #print("topo mismatch")
            continue

        weight = G[edge[0]][edge[1]][edge[2]]["weight"]
        max_bw = G[edge[0]][edge[1]][edge[2]]["max_bw"]

        if check_sleep:

            if topo_graph[edge[0]][edge[1]][edge[2]]["sleep"] == False:
                active_topology.add_edge(edge[0], edge[1], key=edge[2], weight=weight, usage=0, avail=max_bw, max_bw=max_bw)
                active_topology.add_edge(edge[1], edge[0], key=tuple(reversed(edge[2])), weight=weight, usage=0, avail=max_bw, max_bw=max_bw)

        else:
            active_topology.add_edge(edge[0], edge[1], key=edge[2], weight=weight, usage=0, avail=max_bw, max_bw=max_bw)
            active_topology.add_edge(edge[1], edge[0], key=tuple(reversed(edge[2])), weight=weight, usage=0, avail=max_bw, max_bw=max_bw)

    paths = dict(nx.all_pairs_dijkstra(active_topology, weight="weight"))
    
    for element in t[:,0]:

        if element[1] == 0:
            continue

        if element[0][0] not in paths.keys() or element[0][1] not in paths[element[0][0]][1].keys():
            #print("topo mismatch 2", element[0][0], element[0][1])
            continue

        path_nodes = paths[element[0][0]][1][element[0][1]]
        
        for link in zip(path_nodes, path_nodes[1:]):

            usage = element[1]/len(active_topology[link[0]][link[1]])

            for intf in active_topology[link[0]][link[1]]:

                active_topology[link[0]][link[1]][intf]["usage"] += usage
                active_topology[link[0]][link[1]][intf]["avail"] -= usage
                    
    return active_topology


# check if the utilization is above a certain threshold
def check_load(active_topology, max_util=[0.8, 1]):
    
    edges_overloaded = []
    for util in max_util:
        edges_overloaded.append([])
        for edges in list(active_topology.edges):
            usage = active_topology[edges[0]][edges[1]][edges[2]]["usage"]
            max_bw = active_topology[edges[0]][edges[1]][edges[2]]["max_bw"]

            if usage / max_bw > util:
                edges_overloaded[-1].append((usage,max_bw,edges))
    
    return edges_overloaded


# return utilization and total capacity of the network
def get_network_util(G):

    utilizations = []

    for edge in G.edges:
        utilizations.append((G[edge[0]][edge[1]][edge[2]]["usage"],G[edge[0]][edge[1]][edge[2]]["max_bw"]))

    utilizations = np.array(utilizations)
    capacity = np.sum(utilizations[:,1])
    util = np.sum(utilizations[:,0])/np.sum(utilizations[:,1])
    return util, capacity/2


# calculate the reroute budget from the network utilization
def get_reroute_budget(G, x=250, y=0.0001):

    util, capacity = get_network_util(G)

    return (capacity / x) * y/(util**2)


# check if any link is overloaded
def check_overload(path, topo_graph):

    with open(path, "rb") as file:

        G, t = pickle.load(file)

        if (t.ndim == 1):
            t=t[:,np.newaxis]

    topo_sleep = get_load(G, topo_graph, t, True)
    topo_active = get_load(G, topo_graph, t, False)

    ol_sleep, ol_sleep_1 = check_load(topo_sleep, max_util=[0.8, 1])
    ol_active, ol_active_1 = check_load(topo_active, max_util=[0.8, 1])
    
    return {"ol_sleep": ol_sleep,"ol_active": ol_active,"ol_sleep_1": ol_sleep_1,"ol_active_1": ol_active_1}


# save the result of the evaluation
def save_result(path, result):

    now = time.time()

    for element in result:

        filepath = path + f"/scale_{element['config']['scale']}.txt"

        with open(filepath, "a") as f:
            f.write(f"{now}, {json.dumps(element)} \n")

