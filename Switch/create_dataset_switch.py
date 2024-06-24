import sys
sys.path.insert(1, '../Lib/')
import lib, os, pickle


# start and end timestep number
start = int(sys.argv[1])
end = int(sys.argv[2])

# scales to use
scales = [1,2,5,10]


# create timestep numbers
time_offsets = range(start,end)

# point to the dataset and topology file
folderpath = "../Dataset/Switch/"
topopath = folderpath + "topology.csv"
TM_path = "../TM/Switch"

# create directories for the TM
for scale in scales:
    if not os.path.exists(f"{TM_path}/scale_{scale}"):
        os.makedirs(f"{TM_path}/scale_{scale}")

topo = lib.create_topo_switch(topopath)

# create the TM for each timestep and scale
for scale in scales:
    for i in time_offsets:
        
        # skip the problematic timesteps(no data collected) in our dataset
        if i >= 10030 and i <= 10041:
            continue
        timestep = 1703858100 + 300 * i
        print(f"scale: {scale}, timestep: {i}, time: {timestep}")
       
        linkdatapath = folderpath + "interfaces"

        G = lib.create_graph_switch(topo, linkdatapath, timestep, scale=scale, max_util=0.7)
        
        print(len(G.edges)/2, len(G.nodes))
        load_in, load_out = lib.get_in_out_load(G)
        
        t, losses = lib.get_traffic_matrix(G, load_in, load_out)
       
        with open(f"{TM_path}/scale_{scale}/{timestep}_{scale}.pkl", 'wb') as file:
            pickle.dump((G, t), file)

