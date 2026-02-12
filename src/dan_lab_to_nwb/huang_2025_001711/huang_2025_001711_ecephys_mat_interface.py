"""Primary class for converting EEG and EMG data from .mat files."""
from copy import deepcopy
from pathlib import Path

import numpy as np
from pydantic import FilePath
from pymatreader import read_mat
from pynwb.ecephys import Device, ElectricalSeries, ElectrodeGroup
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module
from neuroconv.tools.spikeinterface import add_devices_to_nwbfile
from neuroconv.utils import get_base_schema
from neuroconv.utils.dict import DeepDict
from neuroconv.utils.json_schema import get_schema_from_hdmf_class


class Huang2025EcephysMatInterface(BaseDataInterface):
    """
    Data interface for converting EEG and EMG data from MATLAB files to NWB.

    This interface processes electroencephalography (EEG) and electromyography (EMG)
    recordings stored in MATLAB .mat format and converts them to NWB ElectricalSeries.

    Attributes
    ----------
    keywords : list of str
        Keywords describing the data types handled by this interface.
    """

    keywords = ["EEG", "EMG"]

    def __init__(self, eeg_file_path: FilePath, emg_file_path: FilePath, fs_file_path: FilePath):
        """
        Initialize the ecephys interface.

        Parameters
        ----------
        eeg_file_path : FilePath
            Path to .mat file containing EEG data as a 1D array.
        emg_file_path : FilePath
            Path to .mat file containing EMG data as a 1D array.
        fs_file_path : FilePath
            Path to .mat file containing the sampling frequency (in Hz) for both EEG and EMG.
        """
        super().__init__(eeg_file_path=eeg_file_path, emg_file_path=emg_file_path, fs_file_path=fs_file_path)

    def get_metadata_schema(self) -> dict:
        """
        Get the metadata schema for ecephys data.

        Returns
        -------
        dict
            JSON schema dictionary defining the structure for ecephys metadata,
            including Device, ElectrodeGroup, and ElectricalSeries specifications.
        """
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Ecephys"] = get_base_schema(tag="Ecephys")
        metadata_schema["properties"]["Ecephys"]["required"] = ["Device", "ElectrodeGroup"]
        metadata_schema["properties"]["Ecephys"]["properties"] = dict(
            Device=dict(type="array", minItems=1, items={"$ref": "#/properties/Ecephys/definitions/Device"}),
            ElectrodeGroup=dict(
                type="array", minItems=1, items={"$ref": "#/properties/Ecephys/definitions/ElectrodeGroup"}
            ),
            Electrodes=dict(
                type="array",
                minItems=0,
                renderForm=False,
                items={"$ref": "#/properties/Ecephys/definitions/Electrodes"},
            ),
        )
        # Schema definition for arrays
        metadata_schema["properties"]["Ecephys"]["definitions"] = dict(
            Device=get_schema_from_hdmf_class(Device),
            ElectrodeGroup=get_schema_from_hdmf_class(ElectrodeGroup),
            Electrodes=dict(
                type="object",
                additionalProperties=False,
                required=["name"],
                properties=dict(
                    name=dict(type="string", description="name of this electrodes column"),
                    description=dict(type="string", description="description of this electrodes column"),
                ),
            ),
        )

        metadata_schema["properties"]["Ecephys"]["properties"].update(
            {
                "ElectricalSeriesEEG": get_schema_from_hdmf_class(ElectricalSeries),
                "ElectricalSeriesEMG": get_schema_from_hdmf_class(ElectricalSeries),
            },
        )
        return metadata_schema

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: DeepDict):
        """
        Add EEG and EMG data to an NWB file.

        This method loads EEG and EMG data from MATLAB files, creates the necessary
        electrode metadata, and adds the data as ElectricalSeries objects in the
        'ecephys' processing module.

        Parameters
        ----------
        nwbfile : NWBFile
            The NWB file object to add ecephys data to.
        metadata : DeepDict
            Metadata dictionary containing device, electrode group, and electrode
            specifications under metadata['Ecephys'].

        Returns
        -------
        None

        Notes
        -----
        The data is stored with a conversion factor of 1e-6 (microvolts to volts).
        """
        # Load data
        eeg_file_path = Path(self.source_data["eeg_file_path"])
        emg_file_path = Path(self.source_data["emg_file_path"])
        fs_file_path = Path(self.source_data["fs_file_path"])
        eeg_data = read_mat(eeg_file_path)["EEG"]
        eeg_data = eeg_data.reshape(-1, 1)
        emg_data = read_mat(emg_file_path)["EMG"]
        emg_data = emg_data.reshape(-1, 1)
        fs = read_mat(fs_file_path)["SampFreq"]

        # Add Metadata to NWBFile
        add_devices_to_nwbfile(nwbfile=nwbfile, metadata=metadata)
        add_electrode_groups_to_nwbfile(nwbfile=nwbfile, metadata=metadata)
        add_electrodes_to_nwbfile(nwbfile=nwbfile, metadata=metadata)

        # Add ElectricalSeries to NWBFile
        add_electrical_series_to_nwbfile(
            nwbfile=nwbfile,
            metadata=metadata,
            data=eeg_data,
            starting_time=0.0,
            rate=fs,
            es_key="ElectricalSeriesEEG",
            group_names=["ElectrodeGroupEEG"],
        )
        add_electrical_series_to_nwbfile(
            nwbfile=nwbfile,
            metadata=metadata,
            data=emg_data,
            starting_time=0.0,
            rate=fs,
            es_key="ElectricalSeriesEMG",
            group_names=["ElectrodeGroupEMG"],
        )


def add_electrode_groups_to_nwbfile(nwbfile: NWBFile, metadata: DeepDict):
    """
    Add electrode groups to an NWB file.

    Parameters
    ----------
    nwbfile : NWBFile
        The NWB file object to add electrode groups to.
    metadata : DeepDict
        Metadata dictionary containing electrode group specifications
        under metadata['Ecephys']['ElectrodeGroup'].

    Returns
    -------
    None
    """
    for group_metadata in metadata["Ecephys"]["ElectrodeGroup"]:
        if group_metadata["name"] in nwbfile.electrode_groups:
            continue
        device_name = group_metadata["device"]
        device = nwbfile.devices[device_name]
        electrode_group_kwargs = deepcopy(group_metadata)
        electrode_group_kwargs.update(device=device)
        nwbfile.create_electrode_group(**electrode_group_kwargs)


def add_electrodes_to_nwbfile(nwbfile: NWBFile, metadata: DeepDict):
    """
    Add electrode entries to the NWB file's electrodes table.

    Creates one electrode entry for each EEG and EMG channel with unique
    channel names (e.g., 'EEG1', 'EMG1').

    Parameters
    ----------
    nwbfile : NWBFile
        The NWB file object to add electrodes to.
    metadata : DeepDict
        Metadata dictionary containing electrode group specifications
        under metadata['Ecephys']['ElectrodeGroup'].

    Returns
    -------
    None
    """
    electrode_group_name_to_num_channels = {"ElectrodeGroupEEG": 1, "ElectrodeGroupEMG": 1}

    nwbfile.add_electrode_column(name="channel_name", description="unique channel reference")
    for group_metadata in metadata["Ecephys"]["ElectrodeGroup"]:
        group_name = group_metadata["name"]
        if group_name not in electrode_group_name_to_num_channels:
            continue
        group = nwbfile.electrode_groups[group_name]
        location = group_metadata.get("location", "unknown")
        num_channels = electrode_group_name_to_num_channels[group_name]
        for i in range(num_channels):
            channel_name = f"{group_name[-3:]}{i+1}"  #  ex. ElectrodeGroupEEG --> EEG1
            nwbfile.add_electrode(group=group, location=location, channel_name=channel_name)


def add_electrical_series_to_nwbfile(
    nwbfile: NWBFile,
    metadata: DeepDict,
    data: np.ndarray,
    starting_time: float = 0.0,
    rate: float = 1.0,
    es_key: str = None,
    group_names: list[str] = None,
):
    """
    Add an ElectricalSeries object to an NWB file.

    This function creates an ElectricalSeries object containing electrophysiology
    data and adds it to the 'ecephys' processing module.

    Parameters
    ----------
    nwbfile : NWBFile
        The NWB file object to add the electrical series to.
    metadata : DeepDict
        Metadata dictionary containing electrical series specifications
        under metadata['Ecephys'][es_key].
    data : np.ndarray
        The electrical data to store, shape (n_samples, n_channels).
    starting_time : float, default: 0.0
        Start time of the recording in seconds.
    rate : float, default: 1.0
        Sampling rate in Hz.
    es_key : str or None, default: None
        Key to lookup electrical series metadata. If None, uses 'ElectricalSeries'.
    group_names : list of str or None, default: None
        Names of electrode groups to link to this series. If None, uses ['ElectrodeGroup'].

    Returns
    -------
    None
    """
    es_key = es_key if es_key is not None else "ElectricalSeries"
    eseries_kwargs = dict(
        name=es_key,
        description="Processed data - LFP",
        conversion=1e-6,
        offset=0.0,
        starting_time=starting_time,
        rate=rate,
        data=data,
    )
    assert es_key in metadata["Ecephys"], f"metadata['Ecephys'] dictionary does not contain key '{es_key}'"
    eseries_kwargs.update(metadata["Ecephys"][es_key])
    group_names = group_names if group_names is not None else ["ElectrodeGroup"]

    # Select and/or create module if lfp or processed data is to be stored.
    ecephys_mod = get_module(
        nwbfile=nwbfile,
        name="ecephys",
        description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
    )

    # Link to Electrodes table
    electrode_table_indices = []
    for group_name in group_names:
        electrode_group_names = np.asarray(nwbfile.electrodes.group_name.data[:])
        group_indices = np.where(electrode_group_names == group_name)[0]
        electrode_table_indices.extend(group_indices)
    electrode_table_region = nwbfile.create_electrode_table_region(
        region=electrode_table_indices,
        description="electrode_table_region",
    )
    eseries_kwargs.update(electrodes=electrode_table_region)

    # Create ElectricalSeries object and add it to nwbfile
    es = ElectricalSeries(**eseries_kwargs)
    ecephys_mod.add(es)
