import numpy as np
import networkx as nx
import time, json, pickle


# helper function for the repetita evaluation

def load_topo(path, traffic):
    links = []
    nodes = set()
    with open(path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "EDGES" in line:
                lines = lines[i+2:]
                break
        for i, line in enumerate(lines):
            if line == "\n":
                continue
            elements = line.split()
            links.append((elements[0], (int(elements[1]), int(elements[2])), int(elements[3]),int(elements[4])))
            nodes.add(int(elements[1]))
            nodes.add(int(elements[2]))

    G = nx.MultiDiGraph()
    G.add_nodes_from(nodes)

    for i, link in enumerate(links):

        for link2 in links:
            if (link[1][1], link[1][0]) == link2[1]:
                other_link = link2
                if G.has_edge(link[1][1], link[1][0], key=(other_link[0], link[0])):
                    G.add_edge(link[1][0], link[1][1], key=(link[0], other_link[0]), weight=link[2], max_bw=link[3], avail=link[3], usage=0)
                    break
                else:
                    if G.has_edge(link[1][0], link[1][1]):
                        if any(list(other_link[0] in x for x in G[link[1][0]][link[1][1]])):
                            continue
                        else:
                            G.add_edge(link[1][0], link[1][1], key=(link[0], other_link[0]), weight=link[2], max_bw=link[3], avail=link[3], usage=0)
                            break
                    else:
                        G.add_edge(link[1][0], link[1][1], key=(link[0], other_link[0]), weight=link[2], max_bw=link[3], avail=link[3], usage=0)
                        break

    
    paths = dict(nx.all_pairs_dijkstra(G, weight="weight"))
    
    for element in traffic:
        if element[1] == 0:
            continue
        
        path_nodes = paths[element[0][0]][1][element[0][1]]

        for link in zip(path_nodes, path_nodes[1:]):
            
            usage = element[1]/len(G[link[0]][link[1]])
            for intf in G[link[0]][link[1]]:
                G[link[0]][link[1]][intf]["usage"] += usage
                G[link[0]][link[1]][intf]["avail"] -= usage

    return G

def load_traffic(path):
    traffic = []
    with open(path, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[2:]):
            elements = line.split()
            traffic.append(((int(elements[1]), int(elements[2])), int(elements[3])))
    return traffic


def get_utilization(G):
    utilizations = []
    for edge in G.edges:
        utilizations.append((G[edge[0]][edge[1]][edge[2]]["usage"],G[edge[0]][edge[1]][edge[2]]["max_bw"]))

    utilizations = np.array(utilizations)
    return np.sum(utilizations[:,0]), np.sum(utilizations[:,1])

