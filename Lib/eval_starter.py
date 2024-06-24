import os, time


# helper function that can parallelize the evaluation of the sleep algorithm

start = 0                   # first timestep
end = 4029                 # last timestep
no_workers = 32             # number of workers
file = "../Surfnet/eval_surf.py"       # file to run


# end needs to be one less than the actual end due to checking the next timestep
end = end - 1

# create a screen for each worker
shard = (end - start) // (no_workers - 1)
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
