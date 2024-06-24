# Codebase for Hypnos

## Folders

### Dataset
- The folder containing the datasets needs to be populated first by downloading the datasets; see point about Datasets below.
### Fig
- Figures used in the paper, generated with this codebase
### Lib
- <i>dataset_starter.py</i>: helper file to parallelize the creation of the TMs
- <i>eval_starter.py</i>:  helper file to parallelize the evaluation of the algorithm
- <i>lib.py</i>:   file containing some functions used for the TM creation and evaluation of the algorithm
- <i>rep_lib.py</i>: library specific to the evaluation of the Repetita datset
- <i>tomogravity.py</i>: file containing the tomogravity method to get from link loads to TMs
- <i>create_plots.ipynb</i>: jupyter notebook that creates the plots used in the paper from the results

### Repetita
- <i>repetita.ipynb</i>: evaluates the algorithm on the repetita dataset

### Surfnet
- <i>create_dataset_surf.py</i>: loads topology and link loads from dataset to create a networkx graph and the TM
- <i>eval_surf.py</i>: loads networkx graph and TM, evaluates the sleep algorithm and saves the results 

### Switch
- <i>create_dataset_switch.py</i>: loads topology and link loads from dataset to create a networkx graph and the TM
- <i>eval_switch.py</i>: loads networkx graph and TM, evaluates the sleep algorithm and saves the results
### TM
- Folder where the scripts will save the traffic matrix
### Results
- Folder where the scripts will save the results from the eval

## Python

Python Version: 

```
3.10.12
```

Used packages:

```
numpy==1.26.4
networkx==3.2.1
torch==2.3.1
pandas==2.2.1 
plotly==5.20.0
```

## Datasets

### Repetita
You can find the dataset under https://github.com/svissicchio/Repetita.

### SWITCH LAN & SURFnet
https://doi.org/10.5281/zenodo.12580396

### Your own dataset
Might be necessary to write your own function that loads the dataset depending on the format.

You should be able to reuse the rest of the functions as long as you can create a networkx MultiDiGraph containing the following fields for each link.
Fields:
```
key:     tuple containing (<source interface name>, <destination interface name>)
util:    link load in Gbit/s
avail:   difference between util and max_bw
max_bw:  link capacity in Gbit/s
weight:  routing weight/metric
```

You also most likely need to adapt the paths in the scripts to point to the correct folders
