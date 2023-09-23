# Detecting and Tracking Roosts in Weather Radar Data
This repo implements a machine learning system for detecting and tracking roosts 
in weather surveillance radar data.
Roost detection is based on [Detectron2](https://github.com/darkecology/detectron2) using PyTorch.

#### Repository Overview
- **checkpoints** is for trained model checkpoints
- **development** is for developing detection models
- **src** is for system implementation
    - **data**
        - **downloader** downloads radar scans based on station and day; 
        scan keys and directories for downloaded scans are based on UTC dates
        - **renderer** renders numpy arrays from downloaded scans, visualizes arrays, 
        and deletes the scans after rendering; 
        directories for rendered arrays and images are based on UTC dates
    - **detection**
    - **evaluation** contains customized evaluation adapted from pycocotools v2.0.2
    - **tracking**
    - **utils** contains various utils, scripts to postprocess roost tracks, and scripts to generate visualization
- **tools** is for system deployment
    - **demo.py** downloads radar scans, renders arrays to be processed by models and some channels as images for 
      visualization, detects and tracks roosts in them, and postprocesses the results.
      - **demo.sbatch** defines a slurm job which calls **demo.py**.
      - **launch_demo.py** makes multiple calls to **sbatch demo.sbatch** to submit slurm jobs, and 
        is by default for detecting swallows.
      - **launch_demo_bats.py** is for bats.
    - **gen_deploy_station_days_scripts.py** can create a **launch\*.py** file and corresponding **\*.sbatch** files, 
      when we want each slurm job to include multiple calls to **demo.py** (e.g., process several time periods at 
      a station within one slurm job). 
    - **publish_images.sh** sends images generated during system deployment to a server where we archive data
    - (outdated) **demo.ipynb** is for interactively running the system and not actively maintained
    - (customization) **demo_tiff.py**, **demo_tiff.sbatch**, **launch_demo_tiff.py** are customized given 
      rendered arrays as tiff files.
    - (depreciated) **add_local_time_to_output_files.py** takes in scans*.txt and tracks*.txt files produced by 
      system deployment and append local time to each line. Now the system should handle it automatically.
    - (depreciated) **post_hoc_counting** takes in tracks* files and compute estimated numbers of animals in 
      each bounding box. Now the system should handle it automatically.

#### Installation
1. See Detectron2 requirements
[here](https://detectron2.readthedocs.io/en/latest/tutorials/install.html).
Find a compatible pytorch version
[here](https://pytorch.org/get-started/previous-versions/).
To run detection with GPU, check the cuda version at, for example, `/usr/local/cuda`, or potentially by `nvcc -V`. 
    ```bash
    conda create -n roostsys python=3.8
    conda activate roostsys
    
    # for development and inference with gpus, use the gpu version of torch; we assume cuda 11.3 here
    conda install pytorch==1.10.0 torchvision==0.11.0 cudatoolkit=11.3 -c pytorch -c conda-forge
    # for inference with cpus, use the cpu version of torch
    # conda install pytorch==1.10.0 torchvision==0.11.0 cpuonly -c pytorch
    
    git clone https://github.com/darkecology/roost-system.git
    cd roost-system
    pip install -e .
   ```

2. (Optional) Jupyter notebook.
- `pip install jupyter`
- Add the python environment to jupyter:
    ```bash
    conda install -c anaconda ipykernel
    python -m ipykernel install --user --name=roostsys
    ```
- To check which environments are in jupyter as kernels and to delete one:
    ```bash
    jupyter kernelspec list
    jupyter kernelspec uninstall roostsys
    ```
- Run jupyter notebook on a server: `jupyter notebook --no-browser --port=9991`
- Monitor from local: `ssh -N -f -L localhost:9990:localhost:9991 username@server`
- Enter `localhost:9990` from a local browser tab

#### Develop a detection model
- **development** contains all training and evaluation scripts.
- To prepare a training dataset (i.e. rendering arrays from radar scans and 
generating json files to define datasets with annotations), refer to 
**Installation** and **Dataset Preparation** in the README of 
[wsrdata](https://github.com/darkecology/wsrdata.git).
- Before training, optionally run **try_load_arrays.py** to make sure there's no broken npz files.

Latest model checkpoints are available
[here](https://drive.google.com/drive/folders/1ApVX-PFYVzRn4lgTZPJNFDHnUbhfcz6E?usp=sharing).
- v1: Beginning of Summer 2021 Zezhou model.
- v2: End of Summer 2021 Wenlong model with 48 AP. Better backbone, anchors, and other config.
- v3: End of Winter 2021 Gustavo model with 55 AP. Adapter layer and temporal features.

#### Deploy the system
A Colab notebook for running small-scale inference is 
[here](https://colab.research.google.com/drive/1UD6qtDSAzFRUDttqsUGRhwNwS0O4jGaY?usp=sharing).
Large-scale deployment can be run on CPU servers as follows.
1. Under **checkpoints**, download a trained detection checkpoint.

2. [Configure AWS](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) by
`aws configure`
in order to download radar scans. 
Enter `AWS Access Key ID` and `AWS Secret Access Key` as prompted,
`us-east-1` for `Default region name`, and nothing for `Default output format`.
Review the updated AWS config.
    ```bash
    vim ~/.aws/credentials
    vim ~/.aws/config
    ```

3. Modify **demo.py** for system customization. 
For example, DET_CFG can be changed to adopt a new detector.

4. Make sure the environment is activated. Then consider two deployment scenarios.
   1. In the first, we process consecutive days at stations, i.e. we launch one job for 
   each set of continuous days at a station. Modify VARIABLES in **tools/launch_demo.py**.
   Then under **tools**, run `python launch_demo.py` 
   to submit jobs to slurm and process multiple batches of data. 

   2. In the second, we process scattered days at stations, i.e. we launch one job for 
   all days from each station. Modify VARIABLES in **tools/gen_deploy_station_days_scripts.py**. 
   Under **tools**, run `python gen_deploy_station_days_scripts.py` and then 
   `bash scripts/launch_deploy_station_days_scripts.sh`. Each output txt file save scans or tracks 
   for one station-day: need to manually combine txt files for station-days from each same station.

   3. GOTCHA 1: EXPERIMENT_NAME needs to be carefully chosen; 
  it'll correspond to the dataset name later used in the web UI.
   
   4. GOTCHA 2: If there are previous batches processed under this EXPERIMENT_NAME 
   (i.e. dataset to be loaded to the website), we can move previously processed data at 
   the output directory to another location before saving newly processed data to this 
   EXPERIMENT_NAME output directory. Thereby when we copy newly processed data to the server 
   that hosts the web UI, previous data won't need to be copied again.

#### Notes about array, image, and annotation directions
- geometric direction: large y is North (row 0 is South), large x is East
- image direction: large y is South (row 0 is North), large x is East
1. Rendering
   1. [Render arrays](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/data/renderer.py#L13) 
   for the model to process in the **geographic** direction
   2. [Render png images](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/data/renderer.py#L161) 
   for visualization in the **image** direction
   3. Generate the list of scans with successfully rendered arrays
2. Detector in the **geographic** direction
   1. During training and evaluation, doesn’t use our defined
   [Detector class](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/system.py#L27) 
      1. [dataloader](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/development/experiments_v2/train_roost_detector.py#L220): 
      XYXY
   2. During deployment, use our defined 
   [Detector class](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/system.py#L27) 
   which wraps a Predictor. The run function of this Detector [flips the y axis](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/detection/detector.py#L115) of predicted boxes to get the **image** direction and outputs [predicted boxes](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/detection/detector.py#L118) in xyr where xy are center coordinates
4. For rain removal post-processing using dualpol arrays, 
[flip the y axis](https://github.com/darkecology/roost-system/blob/b27ffd17e773dfeaedac2a79d453395614e8b679/src/roosts/utils/postprocess.py#L188) 
to operate in the **image** direction
5. Generate the list of predicted tracks to accompany png images in the **image** direction


#### User Interface Visualization
In the generated csv files that can be imported to a user interface for visualization, 
the following information could be used to further filter the tracks: 
- track length
- detection scores (-1 represents that the bbox is not from detector, instead, our tracking algorithm)
- bbox sizes
- the minutes from sunrise/sunset of the first bbox in a track

#### Reference
[1] [Detecting and Tracking Communal Bird Roosts in Weather Radar Data.](https://people.cs.umass.edu/~zezhoucheng/roosts/radar-roosts-aaai20.pdf)
Zezhou Cheng, Saadia Gabriel, Pankaj Bhambhani, Daniel Sheldon, Subhransu Maji, Andrew Laughlin and David Winkler.
AAAI, 2020 (oral presentation, AI for Social Impact Track).

[2] Using Spatio-Temporal Information in Weather Radar Data to Detect and Track Communal Bird Roosts. 
Gustavo Perez, Wenlong Zhao, Zezhou Cheng, Maria Carolina T. D. Belotti, Yuting Deng, 
Victoria F. Simons, Elske Tielens, Jeffrey F. Kelly, 
Kyle G. Horton, Subhransu Maji, Daniel Sheldon. Preprint.