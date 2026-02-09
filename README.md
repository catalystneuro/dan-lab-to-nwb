# dan-lab-to-nwb
NWB conversion scripts for Dan lab data to the [Neurodata Without Borders](https://nwb-overview.readthedocs.io/) data format.

## Installation from Github
We recommend installing the package directly from Github. This option has the advantage that the source code can be modified if you need to amend some of the code we originally provided to adapt to future experimental differences. To install the conversion from GitHub you will need to use `git` ([installation instructions](https://github.com/git-guides/install-git)). We also recommend the installation of `conda` ([installation instructions](https://docs.conda.io/en/latest/miniconda.html)) as it contains all the required machinery in a single and simple install.

From a terminal (note that conda should install one in your system) you can do the following:

```bash
git clone https://github.com/catalystneuro/dan-lab-to-nwb
cd dan-lab-to-nwb
conda env create --file make_env.yml
conda activate dan-lab-to-nwb-env
```

This creates a [conda environment](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html) which isolates the conversion code from your system libraries. We recommend that you run all your conversion related tasks and analysis from the created environment in order to minimize issues related to package dependencies.

Then you can run:

```bash
cd dan-lab-to-nwb
conda env create --file make_env.yml
conda activate dan-lab-to-nwb-env
```

Alternatively, if you want to avoid conda altogether (for example if you use another virtual environment tool) you can install the repository with the following commands using only pip:

```bash
git clone https://github.com/catalystneuro/dan-lab-to-nwb
cd dan-lab-to-nwb
pip install -e .
```

Note:
both of the methods above install the repository in [editable mode](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs).
The dependencies for this environment are stored in the dependencies section of the `pyproject.toml` file.

## Helpful Definitions

This conversion project is comprised primarily by DataInterfaces, NWBConverters, and conversion scripts.

In neuroconv, a [DataInterface](https://neuroconv.readthedocs.io/en/main/user_guide/datainterfaces.html) is a class that specifies the procedure to convert a single data modality to NWB.
This is usually accomplished with a single read operation from a distinct set of files.
For example, in this conversion, the `Huang2025DlcBehaviorInterface` contains the code that converts all of the behavioral data to NWB from MATLAB files containing behavioral state labels and CSV files with summary statistics.

In neuroconv, a [NWBConverter](https://neuroconv.readthedocs.io/en/main/user_guide/nwbconverter.html) is a class that combines many data interfaces and specifies the relationships between them, such as temporal alignment.
This allows users to combine multiple modalities into a single NWB file in an efficient and modular way.

In this conversion project, the conversion scripts determine which sessions to convert,
instantiate the appropriate NWBConverter object,
and convert all of the specified sessions, saving them to an output directory of .nwb files.

## Repository structure
Each conversion is organized in a directory of its own in the `src` directory:

    dan-lab-to-nwb/
    ├── LICENSE
    ├── make_env.yml
    ├── MANIFEST.in
    ├── pyproject.toml
    ├── README.md
    └── src
        └── dan_lab_to_nwb
            ├── __init__.py
            ├── download_utils
            │   ├── __init__.py
            │   ├── reorganize_data.py
            │   ├── unorganize_data.py
            │   └── validate_paths.py
            ├── huang_2025_001711
            │   ├── __init__.py
            │   ├── huang_2025_001711_behavior_interface.py
            │   ├── huang_2025_001711_convert_all_sessions.py
            │   ├── huang_2025_001711_convert_session.py
            │   ├── huang_2025_001711_ecephys_mat_interface.py
            │   ├── huang_2025_001711_metadata.yaml
            │   └── huang_2025_001711_nwbconverter.py
            └── huang_2025_001617
                ├── __init__.py
                ├── huang_2025_001617_convert_all_sessions.py
                ├── huang_2025_001617_convert_session.py
                ├── huang_2025_001617_metadata.yaml
                ├── huang_2025_001617_nwbconverter.py
                ├── huang_2025_001617_optogenetic_interface.py
                └── huang_2025_001617_recording_interface.py

For the conversion `huang_2025_001711` (DeepLabCut pose tracking with EEG/EMG) you can find a directory located in `src/dan_lab_to_nwb/huang_2025_001711`. Inside that conversion directory you can find the following files:

* `__init__.py` : This init file imports all the datainterfaces and NWBConverters so that they can be accessed directly from dan_lab_to_nwb.huang_2025_001711.
* `huang_2025_001711_convert_session.py` : This conversion script defines the `session_to_nwb()` function, which converts a single session of data to NWB.
    When run as a script, this file converts an example session to NWB.
* `huang_2025_001711_convert_all_sessions.py` : This conversion script defines the `dataset_to_nwb()` function, which converts all sessions in the dataset to NWB.
    When run as a script, this file calls `dataset_to_nwb()` with the appropriate arguments.
* `huang_2025_001711_nwbconverter.py` : This module defines the primary conversion class, `Huang2025DLCNWBConverter`, which aggregates all of the various datainterfaces relevant for this conversion.
* `huang_2025_001711_behavior_interface.py` : This module defines `Huang2025DlcBehaviorInterface`, which is the data interface for behavioral state labels (.mat files) and summary statistics (.csv files).
* `huang_2025_001711_ecephys_mat_interface.py` : This module defines `Huang2025DlcEcephysMatInterface`, which is the data interface for EEG and EMG data from .mat files.
* `huang_2025_001711_metadata.yaml` : This metadata .yaml file provides high-level metadata for the nwb files directly as well as useful dictionaries for some of the data interfaces.
    For example:
    - Subject/species is "Mus musculus", which is directly included in the NWB file.
    - Behavior/BehavioralSummaryTable contains column descriptions for the behavioral summary table.

For the conversion `huang_2025_001617` (fiber photometry with optogenetics) you can find a directory located in `src/dan_lab_to_nwb/huang_2025_001617`. Inside that conversion directory you can find the following files:

* `__init__.py` : This init file imports all the datainterfaces and NWBConverters so that they can be accessed directly from dan_lab_to_nwb.huang_2025_001617.
* `huang_2025_001617_convert_session.py` : This conversion script defines the `session_to_nwb()` function, which converts a single session of data to NWB.
    When run as a script, this file converts several example sessions to NWB, representing various edge cases in the dataset.
* `huang_2025_001617_convert_all_sessions.py` : This conversion script defines the `dataset_to_nwb()` function, which converts all sessions in the dataset to NWB.
    When run as a script, this file calls `dataset_to_nwb()` with the appropriate arguments.
* `huang_2025_001617_nwbconverter.py` : This module defines the primary conversion class, `Huang2025NWBConverter`, which aggregates all of the various datainterfaces relevant for this conversion.
* `huang_2025_001617_recording_interface.py` : This module defines `Huang2025TdtRecordingInterface`, which is the data interface for TDT electrophysiology recordings (EEG and EMG).
* `huang_2025_001617_optogenetic_interface.py` : This module defines `Huang2025OptogeneticInterface`, which is the data interface for optogenetic stimulation data from TDT systems.
* `huang_2025_001617_metadata.yaml` : This metadata .yaml file provides high-level metadata for the nwb files, including device specifications, fiber photometry metadata, and optogenetic metadata.

The `download_utils` directory contains utility scripts for reorganizing TDT data folders to be compatible with the Neo data reader:

* `reorganize_data.py` : Script to reorganize TDT folders into a Neo-compatible structure
* `unorganize_data.py` : Script to reverse the reorganization (for backup purposes)
* `validate_paths.py` : Script to validate file paths before conversion

## Running a Conversion

### huang_2025_001711 (DeepLabCut with EEG/EMG)

This conversion processes behavioral video data analyzed with DeepLabCut along with EEG and EMG recordings.

To convert an example session:

1. In `src/dan_lab_to_nwb/huang_2025_001711/huang_2025_001711_convert_session.py`, update the `data_dir_path` and
    `output_dir_path` variables in the `main()` function to appropriate local paths. `data_dir_path` should point to
    the directory containing your raw data. `output_dir_path` can be any valid path on your system where the output
    NWB files will be stored.

2. Run the conversion script:
    ```bash
    python src/dan_lab_to_nwb/huang_2025_001711/huang_2025_001711_convert_session.py
    ```
    Or, if running on a Windows machine:
    ```bash
    python src\\dan_lab_to_nwb\\huang_2025_001711\\huang_2025_001711_convert_session.py
    ```

To convert all sessions in the dataset:

1. Update `data_dir_path` and `output_dir_path` in `src/dan_lab_to_nwb/huang_2025_001711/huang_2025_001711_convert_all_sessions.py`
    as with the example sessions.

2. Run the conversion script:
    ```bash
    python src/dan_lab_to_nwb/huang_2025_001711/huang_2025_001711_convert_all_sessions.py
    ```

### huang_2025_001617 (Fiber Photometry with Optogenetics)

This conversion processes TDT recordings that include fiber photometry, optogenetic stimulation, EEG/EMG, and behavioral video.

To convert example sessions:

1. In `src/dan_lab_to_nwb/huang_2025_001617/huang_2025_001617_convert_session.py`, update the `data_dir_path` and
    `output_dir_path` variables in the `main()` function to appropriate local paths.

2. Before running the conversion, you may need to reorganize the TDT data folders to be compatible with the Neo data reader.
    You can do this by running:
    ```bash
    python src/dan_lab_to_nwb/download_utils/reorganize_data.py
    ```
    Update the `data_dir_path` in that script to point to your data directory first.

3. Run the conversion script:
    ```bash
    python src/dan_lab_to_nwb/huang_2025_001617/huang_2025_001617_convert_session.py
    ```

To convert all sessions in the dataset:

1. Update `data_dir_path` and `output_dir_path` in `src/dan_lab_to_nwb/huang_2025_001617/huang_2025_001617_convert_all_sessions.py`
    as with the example sessions.

2. Run the conversion script:
    ```bash
    python src/dan_lab_to_nwb/huang_2025_001617/huang_2025_001617_convert_all_sessions.py
    ```

Note: The `huang_2025_001617` conversion supports multiprocessing to speed up conversion of large datasets. You can adjust the
`max_workers` parameter in the conversion script to control the number of parallel processes.

## Understanding the Data

### huang_2025_001711 Dataset

This dataset contains:
- **Behavioral video** from camera recordings (Cam1 or Cam2)
- **DeepLabCut pose estimation** tracking animal body parts during behavior
- **Behavioral state labels** classifying each 5-second epoch as REM, WAKE, or NREM sleep
- **Behavioral summary statistics** providing session-level metrics
- **EEG (electroencephalography)** recordings from the brain
- **EMG (electromyography)** recordings from muscles

The data files are organized by subject (e.g., M407) and session (e.g., M407-S1).

### huang_2025_001617 Dataset

This dataset contains:
- **Fiber photometry recordings** measuring fluorescent signals from genetically encoded calcium indicators
- **Optogenetic stimulation** data including test pulses and intense stimulation events
- **EEG and EMG recordings** from TDT (Tucker-Davis Technologies) systems
- **Behavioral video** synchronized with neural recordings
- **Metadata** about viral vectors, optical fibers, light sources, and brain regions

The data is organized across multiple experimental setups (Setup - Bing, Setup - WS8, Setup - MollyFP) with sessions
identified by date and time stamps.

This dataset includes two types of experimental sessions:
- **opto-signal sum**: Sessions with both optogenetic stimulation and fiber photometry recording
- **opto-behavioral sum**: Sessions with optogenetic stimulation focused on behavioral effects (may not include fiber photometry)

## Tips for Using the Code

- **Start with example sessions**: Both conversion scripts include example sessions in their `main()` functions. These
  demonstrate the expected data organization and parameter values.

- **Check your file paths**: The conversion will fail if file paths are incorrect. Make sure all input files exist
  before running the conversion.

- **Use stub_test for development**: Set `stub_test=True` when developing or testing to convert only a small portion
  of the data, which runs much faster.

- **Read the docstrings**: All functions and classes have detailed NumPy-style docstrings explaining their purpose,
  parameters, and return values. Use `help(function_name)` in Python to view these.

- **Modify metadata files**: The `.yaml` metadata files contain high-level information about the experiment. You can
  edit these files to update metadata without changing the Python code.

## Getting Help

If you encounter issues or have questions about the conversion:

1. Check the docstrings in the code for detailed information about each function
2. Review the example sessions in the conversion scripts
3. Consult the [NWB documentation](https://nwb-overview.readthedocs.io/) for information about the NWB format
4. Consult the [NeuroConv documentation](https://neuroconv.readthedocs.io/) for information about data interfaces and converters
