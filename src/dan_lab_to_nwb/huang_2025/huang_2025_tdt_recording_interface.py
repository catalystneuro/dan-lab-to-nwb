"""Primary class for converting TDT Ephys Recordings."""
import numpy as np
from pynwb.file import NWBFile
from spikeinterface.extractors import TdtRecordingExtractor

from neuroconv.datainterfaces import TdtRecordingInterface


class Huang2025TdtRecordingInterface(TdtRecordingInterface):
    """TDT RecordingInterface for huang_2025 conversion."""

    Extractor = TdtRecordingExtractor

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Ecephys"]["Device"] = []  # remove default device
        metadata["Ecephys"]["ElectrodeGroup"] = []  # remove default electrode group
        return metadata

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, **conversion_options):
        # ElectricalSeries is written manually so that it can be split into EEG and EMG
        conversion_options["write_electrical_series"] = False

        electrode_group_name_to_num_channels = {"ElectrodeGroupEEG": 2, "ElectrodeGroupEMG": 2}
        channel_ids = self.recording_extractor.get_channel_ids()
        locations, group_names = [], []
        for electrode_group_meta in metadata["Ecephys"]["ElectrodeGroup"]:
            name = electrode_group_meta["name"]
            num_channels = electrode_group_name_to_num_channels[name]
            location = electrode_group_meta["location"]
            locations.extend([location] * num_channels)
            group_names.extend([name] * num_channels)
        channel_names = ["EEG1", "EEG2", "EMG1", "EMG2"]
        self.recording_extractor.set_property(key="brain_area", ids=channel_ids, values=locations)
        self.recording_extractor.set_property(key="group_name", ids=channel_ids, values=group_names)
        self.recording_extractor.set_property(key="channel_name", ids=channel_ids, values=channel_names)

        super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata, **conversion_options)
        conversion_options.pop("write_electrical_series")
        conversion_options.pop("stub_test")
        add_electrical_series_to_nwbfile(
            recording=self.recording_extractor,
            nwbfile=nwbfile,
            metadata=metadata,
            es_key=self.es_key,
            **conversion_options,
        )


def add_electrical_series_to_nwbfile(
    recording,
    nwbfile,
    metadata=None,
    es_key=None,
    write_scaled=False,
    iterator_type="v2",
    iterator_opts=None,
    always_write_timestamps=False,
):
    """
    Adds traces from recording object as ElectricalSeries to an NWBFile object.

    Parameters
    ----------
    recording : SpikeInterfaceRecording
        A recording extractor from spikeinterface
    nwbfile : NWBFile
        nwb file to which the recording information is to be added
    metadata : dict, optional
        metadata info for constructing the nwb file.
        Should be of the format::

            metadata['Ecephys']['ElectricalSeries'] = dict(
                name=my_name,
                description=my_description
            )
    es_key : str, optional
        Key in metadata dictionary containing metadata info for the specific electrical series
    write_scaled : bool, default: False
        If True, writes the traces in uV with the right conversion.
        If False , the data is stored as it is and the right conversions factors are added to the nwbfile.
    iterator_type: {"v2",  None}, default: 'v2'
        The type of DataChunkIterator to use.
        'v2' is the locally developed SpikeInterfaceRecordingDataChunkIterator, which offers full control over chunking.
        None: write the TimeSeries with no memory chunking.
    iterator_opts: dict, optional
        Dictionary of options for the iterator.
        See https://hdmf.readthedocs.io/en/stable/hdmf.data_utils.html#hdmf.data_utils.GenericDataChunkIterator
        for the full list of options.
    always_write_timestamps : bool, default: False
        Set to True to always write timestamps.
        By default (False), the function checks if the timestamps are uniformly sampled, and if so, stores the data
        using a regular sampling rate instead of explicit timestamps. If set to True, timestamps will be written
        explicitly, regardless of whether the sampling rate is uniform.

    Notes
    -----
    Missing keys in an element of metadata['Ecephys']['ElectrodeGroup'] will be auto-populated with defaults
    whenever possible.
    """
    import pynwb

    from neuroconv.tools.nwb_helpers import get_module
    from neuroconv.tools.spikeinterface.spikeinterface import (
        _get_electrode_table_indices_for_recording,
        _recording_traces_to_hdmf_iterator,
    )

    default_name = "ElectricalSeriesLFP"

    eseries_kwargs = dict(name=default_name, description="Processed data - LFP")

    # Select and/or create module if lfp or processed data is to be stored.
    ecephys_mod = get_module(
        nwbfile=nwbfile,
        name="ecephys",
        description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
    )
    if "LFP" not in ecephys_mod.data_interfaces:
        ecephys_mod.add(pynwb.ecephys.LFP(name="LFP"))

    if metadata is not None and "Ecephys" in metadata and es_key is not None:
        assert es_key in metadata["Ecephys"], f"metadata['Ecephys'] dictionary does not contain key '{es_key}'"
        eseries_kwargs.update(metadata["Ecephys"][es_key])

    # Create a region for the electrodes table
    electrode_table_indices = _get_electrode_table_indices_for_recording(recording=recording, nwbfile=nwbfile)
    electrode_table_region = nwbfile.create_electrode_table_region(
        region=electrode_table_indices,
        description="electrode_table_region",
    )
    eseries_kwargs.update(electrodes=electrode_table_region)

    if not write_scaled:
        add_conversion_to_eseries_kwargs(eseries_kwargs=eseries_kwargs, recording=recording)

    # Iterator
    ephys_data_iterator = _recording_traces_to_hdmf_iterator(
        recording=recording,
        iterator_type=iterator_type,
        iterator_opts=iterator_opts,
        return_scaled=write_scaled,
    )
    eseries_kwargs.update(data=ephys_data_iterator)

    eseries_kwargs = add_timing_to_eseries_kwargs(
        eseries_kwargs=eseries_kwargs,
        recording=recording,
        always_write_timestamps=always_write_timestamps,
    )

    # Create ElectricalSeries object and add it to nwbfile
    es = pynwb.ecephys.ElectricalSeries(**eseries_kwargs)
    ecephys_mod.data_interfaces["LFP"].add_electrical_series(es)


def add_timing_to_eseries_kwargs(eseries_kwargs: dict, recording, always_write_timestamps: bool):
    """
    Add timing information to the eseries_kwargs dictionary.

    Parameters
    ----------
    eseries_kwargs : dict
        The dictionary containing the arguments for creating the ElectricalSeries object.
    recording : SpikeInterfaceRecording
        The recording extractor from spikeinterface.
    always_write_timestamps : bool
        If True, always write timestamps explicitly, regardless of uniform sampling.

    Returns
    -------
    eseries_kwargs : dict
        The updated dictionary with timing information added.
    """
    from neuroconv.utils import (
        calculate_regular_series_rate,
    )

    if always_write_timestamps:
        timestamps = recording.get_times()
        eseries_kwargs.update(timestamps=timestamps)
        return eseries_kwargs

    # If the recording does not already have a vector of timestamps, we simply use the starting time and rate
    if not recording.has_time_vector():
        rate = recording.get_sampling_frequency()
        recording_t_start = recording._recording_segments[0].t_start or 0.0
        eseries_kwargs.update(starting_time=recording_t_start, rate=rate)
        return eseries_kwargs

    timestamps = recording.get_times()
    rate = calculate_regular_series_rate(series=timestamps)
    timestamps_are_regular = rate is not None
    recording_t_start = timestamps[0]
    # If the timestamps are regular, we can use starting_time and rate instead of the full timestamps
    if timestamps_are_regular:
        # Note that we call the sampling frequency again because the estimated rate might be different from the
        # sampling frequency of the recording extractor by some epsilon.
        eseries_kwargs.update(starting_time=recording_t_start, rate=recording.get_sampling_frequency())
        return eseries_kwargs

    # If the timestamps are not regular, we need to use the full timestamps
    eseries_kwargs.update(timestamps=timestamps)
    return eseries_kwargs


def add_conversion_to_eseries_kwargs(eseries_kwargs: dict, recording):
    """
    Add conversion information to the eseries_kwargs dictionary.

    This function determines the conversion factors for the ElectricalSeries object based on the recording extractor.
    In nwb to get traces in Volts we take data*channel_conversion*conversion + offset.

    Parameters
    ----------
    eseries_kwargs : dict
        The dictionary containing the arguments for creating the ElectricalSeries object.
    recording : SpikeInterfaceRecording
        The recording extractor from spikeinterface.

    Returns
    -------
    eseries_kwargs : dict
        The updated dictionary with conversion information added.
    """
    from neuroconv.tools.spikeinterface.spikeinterface import _report_variable_offset

    channel_conversion = recording.get_channel_gains()
    channel_offsets = recording.get_channel_offsets()

    unique_channel_conversion = np.unique(channel_conversion)
    unique_channel_conversion = unique_channel_conversion[0] if len(unique_channel_conversion) == 1 else None

    unique_offset = np.unique(channel_offsets)
    if unique_offset.size > 1:
        channel_ids = recording.get_channel_ids()
        # This prints a user friendly error where the user is provided with a map from offset to channels
        _report_variable_offset(channel_offsets, channel_ids)
    unique_offset = unique_offset[0] if unique_offset[0] is not None else 0

    micro_to_volts_conversion_factor = 1e-6
    if unique_channel_conversion is None:
        eseries_kwargs.update(conversion=micro_to_volts_conversion_factor)
        eseries_kwargs.update(channel_conversion=channel_conversion)
    elif unique_channel_conversion is not None:
        eseries_kwargs.update(conversion=unique_channel_conversion * micro_to_volts_conversion_factor)
    eseries_kwargs.update(offset=unique_offset * micro_to_volts_conversion_factor)

    return eseries_kwargs
