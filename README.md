# Generating electrical power datasets for data-driven modeling

### Description
This tool assists researchers  to export electrical quantities such as power flows, 
injections and others to featured datasets that can be used in data-driven modeling 
such as neural networks. 

Using Pandapower (http://www.pandapower.org/), the electrical  quantities are first imported from
 a test power grid such as IEEE-118. Loads in the power grid are then varied and powerflow 
 analysis is conducted for each **load scenario**. The resulting data is csv tabulated 
 with proper headers that fully describe  the electrical quantities. 
For instance, qfl45_35_33 is the reactive power flowing in a transmission line from bus 35 to bus 33. 

Since this code was developed as part of a research related to Power State Estimation, states 
are generated in separate file. However, all quantities are linked with an ID indicating 
the corresponding load scenario. Rows are duplicated to allow for adding noise. If not needed, 
duplicate rows may be easily  dropped when imported by Pandas. The three generated  files: 
***source_clean_meas.csv, source_noisy_meas and target_gt_states.csv*** are all found in the 
subfolder ***datasets***.

The underlying functions are all defined in the python script file ***gen_scen_fnctns.py***. The 
loads are varied using a uniform distribution. If needed, the function ***gen_clean_scen_unfrm***
may be easily  modified to allow for other projected load patterns.  

The tool further generates the DC measurement matrix H sorted in the same order of the selected
measurements. Clearly, the H matrix does not include entries for voltage magnitudes (all assumed 1 p.u. for
DC model assumptions). 
This matrix can be found under the subfolder ***base_net***. Note: The H matrix is tested only for 
IEEE-118 case.

If you are using our code or part of it for any of your projects, please make sure to cite 
our paper below:

xxxxxx      



### Installation
1) Install conda  https://docs.conda.io/en/latest/#
2) Open conda ternminal in the project root and create conda environment using:
***conda env create -f psse_env.yml***
3) Activate psse_env  using:
***conda activate psse_env***
4) Install panda power from terminal using (This will take time!):

***pip install git+https://github.com/skababji/pandapower.git@develop#egg=pandapower***

4) Run jupyter notebook from the terminal

### Structure
Please make sure you have the following main folders in your project:

| notebooks

| runs

| src 

You may need to manually create 'runs' folder if not available

### Use
1) Open **generate_meas_template** notebook.
2) Select a power grid e.g. Enter **net=nw.case118()**. Note: This tool is tested only for IEEE118.
3) Run the notebook.
4) Go to and open **../runs/meas_template.csv**. The file lists all available measurements in the selected grid.
Set the measurement you need to include in your target dataset to **TRUE**. Save the file and close it.
5) Open **generate_load_scenarios** notebook.
6) Select the base power grid. This should match the one used to generate the measurement template e.g. **net=nw.case118()**
7) Enter your parameters and run the notebook. The notebook will construct a timestamped run folder with three subfolders, namely **base_net, datasets, and grid**.
Check the gnerated datastes under the subfolder ***datasets***. Other subfolders contain useful
infromation about the grid, e.g. buses, lines..etc. 

Please note that you will find useful comments embedded in the code.

### Contact
For any queries, please contact Samer Kababji at  <skababji@gmail.com>
