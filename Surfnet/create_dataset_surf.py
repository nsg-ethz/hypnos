import sys
sys.path.insert(1, '../Lib/')
import lib, os, pickle, datetime
import networkx as nx



# start and end timestep number
start = int(sys.argv[1])
end = int(sys.argv[2])

# scales to use
scales = [1,2,5,10]

folderpath = "../Dataset/Surfnet"
topology_path = f"{folderpath}/topology.csv"
TM_path = "../TM/Surfnet"

# create timesteps from start and end timestep numbers
timesteps = []
for i in range(start, end):
    ts = 1711922700 + 300 * i
    timesteps.append(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ'))

# create directories for the TM
for scale in scales:
    if not os.path.exists(f"{TM_path}/scale_{scale}"):
        os.makedirs(f"{TM_path}/scale_{scale}")


# create the topology graph
topo = lib.create_topo_surf(topology_path)

# create the traffic matrices
for scale in scales:
    for timestep in timesteps:
        
        print(scale, timestep)

        links_path = f"{folderpath}/link_traffic/{timestep}.csv"
        
        G = lib.create_graph_surf(links_path, topo, scale=scale, max_util=0.7)

        print(f"Number of nodes: {len(G.nodes)}, Number of edges: {len(G.edges) / 2}")

        load_in, load_out = lib.get_in_out_load(G)

        t, losses = lib.get_traffic_matrix(G, load_in, load_out)

        with open(f"{TM_path}/scale_{scale}/{timestep}_{scale}.pkl", 'wb') as file:
            pickle.dump((G, t), file)
