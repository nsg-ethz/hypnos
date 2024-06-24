import time
import numpy as np
import networkx as nx
import torch


# create the vectors needed for the tomogravity method
def create_vectors(G, load_in, load_out):
    x = np.empty((len(G.edges)))
    x_link = {}

    sum_load_out = np.sum(list(load_out.values()))

    for i, edge in enumerate(sorted(G.edges)):
        
        x[i] = G[edge[0]][edge[1]][edge[2]]["usage"]
        x_link[(edge[0], edge[1], edge[2])] = i
    nodes = sorted(G.nodes)

    t = np.empty((len(nodes)**2),dtype=tuple)
    for i, node1 in enumerate(nodes):
        for j, node2 in enumerate(nodes):
            t[i*len(nodes)+j] = (node1, node2)

    # gravity model
    tm_g = np.empty((len(nodes)**2))
    for i, node1 in enumerate(nodes):
        for j, node2 in enumerate(nodes):
            tm_g[i*len(nodes)+j] = load_in[node1] * load_out[node2]/sum_load_out
            
    A = np.zeros((len(x),len(t)))
    paths = dict(nx.all_pairs_dijkstra(G, weight="weight"))
    for i, path in enumerate(t):
        path_nodes = paths[path[0]][1][path[1]]

        for link in zip(path_nodes, path_nodes[1:]):
            no_intf = len(G[link[0]][link[1]])
            for intf in G[link[0]][link[1]]:

                j = x_link[(link[0],link[1],intf)]
                A[j,i] = 1/no_intf

    return (A, x, t, tm_g)


# tomogravity to create TM from link loads
def tomogravity(A, x, tm_g, w):

    xw=x-np.matmul(A,tm_g) 
    r, c = np.shape(A)
    Aw = A * np.repeat(w[:, np.newaxis].T, r, axis=0)
    
    start = time.time()
    tw = torch.linalg.lstsq(torch.from_numpy(Aw), torch.from_numpy(xw[:, np.newaxis]), rcond=None)[0].numpy()
    print(time.time()-start)

    t = tm_g + w * tw[:,0]
    return t

