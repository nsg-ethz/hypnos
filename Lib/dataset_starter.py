import os, time


# helper function that can parallelize the Traffic Matrix dataset creation

# configure dataset creation parameters
start = 0                           # first timestep
end = 4030                           # last timestep
no_workers = 12                        # number of workers
file = "../Surfnet/create_dataset_surf.py"     # file to run

# create a screen for each worker
shard = (end - start) // no_workers
out = 0
test = False

for i in range(no_workers-1):
    time.sleep(1)
    name = f'worker{i}_{start + i * shard}_{start + (i + 1) * shard}'
    if test:
        print(f'screen -S {name} -L -Logfile "./log/{name}.log" -d -m bash -c "python3 {file} {start + i * shard} {start + (i + 1) * shard}"')
    else:
        out += os.system(f'screen -S {name} -L -Logfile "./log/{name}.log" -d -m bash -c "python3 {file} {start + i * shard} {start + (i + 1) * shard}"')

name = f'worker{no_workers-1}_{start + (no_workers-1) * shard}_{end}'
if test:
    print(f'screen -S {name} -L -Logfile "./log/{name}.log" -d -m bash -c "python3 {file} {start + (no_workers-1) * shard} {end}"')
else:
    out += os.system(f'screen -S {name} -L -Logfile "./log/{name}.log" -d -m bash -c "python3 {file} {start + (no_workers-1) * shard} {end}"')
print(out)
