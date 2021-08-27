# Generating electrical power datasets for data-driven modelling


## Description

This tool assists researchers to export electrical quantities such as
power flows, injections and others to featured datasets that can be used
in data-driven modelling such as neural networks.  
Using Pandapower <http://www.pandapower.org/>, the electrical quantities
are first imported from a test power grid such as IEEE-118. Loads in the
power grid are then varied and power flow analysis is conducted for each
**load scenario**. The resulting data is csv tabulated with proper
headers that fully describe the electrical quantities. For instance,
qfl45_35_33 is the reactive power flowing in a transmission line from
bus 35 to bus 33.  
Since this code was developed as part of research related to Power State
Estimation, states are generated in a separate file. However, all
quantities are linked with an ID indicating the corresponding load
scenario. Rows are duplicated to allow for adding noise. If not needed,
duplicate rows may be easily dropped when imported by Pandas. The three
generated files (**source_clean_meas.csv, source_noisy_meas and
target_gt_states.csv**) are all found in the subfolder **datasets**.  
The underlying functions are all defined in the python script file
**gen_scen_fnctns.py**. The loads are varied using a uniform
distribution. If needed, the function **gen_clean_scen_unfrm** may be
easily modified to allow for other projected load patterns.  
The tool further generates the **DC measurement matrix H** sorted in the
same order of the selected measurements. Clearly, the H matrix does not
include entries for voltage magnitudes (all 1 p.u. for DC model
assumptions). This matrix can be found under the subfolder **base_net**.
Note: The H matrix is tested only for IEEE-118 case.  

## Installation

1.  Install conda
    <https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html>

2.  Open conda ternminal in the project root and create conda
    environment using:**conda env create -f pdv1_env.yml**. Note: Change
    the prefix in the yml file as per your convenience. You may also
    choose to install the listed dependencies manually.

3.  Activate pdv1_env using: **conda activate pdv1_env**

4.  Install panda power using: **pip install pandapower**

5.  Run jupyter notebook from the terminal

## Structure

Please make sure you have the following main folders in your project:

-   notebooks

-   runs

-   src

You may need to manually create ’runs’ folder if not available

## Use

1.  Open **generate_meas_template** notebook.

2.  Select a power grid e.g. Enter **net=nw.case118()**. Note: This tool
    is tested only for IEEE118.

3.  Run the notebook.

4.  Go to and open **..runsmeas_template.csv**. The file lists all
    available measurements in the selected grid.

5.  Set the measurement you need to include in your target dataset to
    **TRUE**. Save the file and close it.

6.  Open **generate_load_scenarios** notebook.

7.  Select the base power grid. This should match the one used to
    generate the measurement template e.g. **net=nw.case118**

8.  Enter your parameters and run the notebook. The notebook will
    construct a timestamped run folder with three subfolders, namely
    **base_net, datasets, and grid**.

9.  Check the generated datastes under the subfolder **datasets**. Other
    subfolders contain useful information about the grid, e.g. buses,
    lines..etc.

Note that you will find useful comments embedded in the code. All units
of measurement are inline with Pandapower except the angles where they
are given in radians instead of degrees.

## Q&A

1.  **Q:** It is mentioned in the readme document that "qfl45_35_33 is
    the reactive power flowing in a transmission line from bus 35 to bus
    33.". What’s the meaning of 45 here, is it the line number?  
    **A:** It is the transmission line index used by panda power. The
    same applies to the rest of quantities. For instance, pft1_25_24
    refers to active power flow from bus 25 to bus 24 in the transformer
    with panda power index 1. I used the following naming convention:

    -   Pf: for active power flow

    -   qf: for reactive power flow

    -   p: for active power injection

    -   q: for reactive power injection

    -   l: for transmission line

    -   t: for transformer

    -   vm: is bus voltage magnitude in pu

    -   va :is bus voltage angle in radians

2.  **Q:** In the csv data, what is the scenario number? Can I think
    they are the independent measurement at different time points?  
    **A:** Yes, for sure. Load scenarios can be thought of as snapshots
    in time.

3.  **Q:** Each scenario (e.g.,A0) is copied 10 (or any number) times in
    the clean dataset, I think your purpose is for later use to add 10
    different noises. Is it correct?  
    **A:**Yes, correct.

4.  **Q:** I noticed there are three H matrices under the ’base_net’
    repository, which one should be used in DC power flow model?  
    **A:**You need to use h_no_slack.csv. The first row in the file
    shows the bus indices.

# Contact

For any queries, please contact Samer Kababji at
[skababji@gmail.com](skababji@gmail.com)
