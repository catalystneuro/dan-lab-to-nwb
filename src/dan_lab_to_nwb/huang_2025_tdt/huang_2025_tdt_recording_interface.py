"""Primary class for converting TDT Ephys Recordings."""
import numpy as np
from pynwb.ecephys import ElectricalSeries
from pynwb.file import NWBFile
from spikeinterface.extractors import TdtRecordingExtractor

from neuroconv.datainterfaces import TdtRecordingInterface
from neuroconv.tools.nwb_helpers import get_module


class Huang2025TdtRecordingInterface(TdtRecordingInterface):
    """TDT RecordingInterface for huang_2025 conversion."""

    Extractor = TdtRecordingExtractor

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata["Ecephys"]["Device"] = []  # remove default device
        metadata["Ecephys"]["ElectrodeGroup"] = []  # remove default electrode group
        return metadata

    def add_to_nwbfile(
        self, nwbfile: NWBFile, metadata: dict, group_names: list[str] = ["ElectrodeGroup"], **conversion_options
    ):
        from neuroconv.tools.spikeinterface import (
            _stub_recording,
            add_recording_metadata_to_nwbfile,
        )

        # ElectricalSeries is written manually so that it can be split into EEG and EMG

        electrode_group_name_to_num_channels = {"ElectrodeGroupEEG": 2, "ElectrodeGroupEMG": 2}
        channel_ids = self.recording_extractor.get_channel_ids()
        locations, names = [], []
        for electrode_group_meta in metadata["Ecephys"]["ElectrodeGroup"]:
            name = electrode_group_meta["name"]
            num_channels = electrode_group_name_to_num_channels[name]
            location = electrode_group_meta["location"]
            locations.extend([location] * num_channels)
            names.extend([name] * num_channels)
        channel_names = ["EEG1", "EEG2", "EMG1", "EMG2"]
        self.recording_extractor.set_property(key="brain_area", ids=channel_ids, values=locations)
        self.recording_extractor.set_property(key="group_name", ids=channel_ids, values=names)
        self.recording_extractor.set_property(key="channel_name", ids=channel_ids, values=channel_names)

        add_recording_metadata_to_nwbfile(
            recording=self.recording_extractor,
            nwbfile=nwbfile,
            metadata=metadata,
        )
        stub_test = conversion_options.pop("stub_test")
        if stub_test:
            recording = _stub_recording(recording=self.recording_extractor)
        else:
            recording = self.recording_extractor
        add_electrical_series_to_nwbfile(
            recording=recording,
            nwbfile=nwbfile,
            metadata=metadata,
            es_key=self.es_key,
            group_names=group_names,
            **conversion_options,
        )


def add_electrical_series_to_nwbfile(
    recording: TdtRecordingExtractor,
    nwbfile: NWBFile,
    metadata=None,
    es_key=None,
    group_names=None,
    write_scaled=False,
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
    group_names : list of str, optional
        List of electrode group names to which the channels belong.
    write_scaled : bool, default: False
        If True, writes the traces in uV with the right conversion.
        If False , the data is stored as it is and the right conversions factors are added to the nwbfile.
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
    default_name = "ElectricalSeriesLFP"
    eseries_kwargs = dict(name=default_name, description="Processed data - LFP")
    if metadata is not None and "Ecephys" in metadata and es_key is not None:
        assert es_key in metadata["Ecephys"], f"metadata['Ecephys'] dictionary does not contain key '{es_key}'"
        eseries_kwargs.update(metadata["Ecephys"][es_key])
    group_names = group_names if group_names is not None else ["ElectrodeGroup"]

    # Select and/or create module if lfp or processed data is to be stored.
    ecephys_mod = get_module(
        nwbfile=nwbfile,
        name="ecephys",
        description="Intermediate data from extracellular electrophysiology recordings, e.g., LFP.",
    )

    # Add conversion and offset metadata
    if not write_scaled:
        add_conversion_to_eseries_kwargs(eseries_kwargs=eseries_kwargs, recording=recording)

    # Add timing info (timestamps or starting_time and rate)
    eseries_kwargs = add_timing_to_eseries_kwargs(
        eseries_kwargs=eseries_kwargs,
        recording=recording,
        always_write_timestamps=always_write_timestamps,
    )

    # Create a region for the electrodes table
    electrode_table_indices = []
    for group_name in group_names:
        indices = get_electrode_table_indices_for_group(recording=recording, nwbfile=nwbfile, group_name=group_name)
        electrode_table_indices.extend(indices)
    electrode_table_region = nwbfile.create_electrode_table_region(
        region=electrode_table_indices,
        description="electrode_table_region",
    )
    eseries_kwargs.update(electrodes=electrode_table_region)

    # Iterator
    iterator_opts = iterator_opts if iterator_opts is not None else {}
    iterator_opts["return_scaled"] = write_scaled
    ephys_data_iterator = Huang2025RecordingDataChunkIterator(
        recording=recording,
        channel_indices=electrode_table_indices,
        **iterator_opts,
    )
    eseries_kwargs.update(data=ephys_data_iterator)

    # Create ElectricalSeries object and add it to nwbfile
    es = ElectricalSeries(**eseries_kwargs)
    ecephys_mod.add(es)


def add_timing_to_eseries_kwargs(eseries_kwargs: dict, recording: TdtRecordingExtractor, always_write_timestamps: bool):
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


def _get_electrodes_table_global_ids(nwbfile) -> list[str]:
    """
    Generate a list of global identifiers for channels in the electrode table of an NWB file.

    These identifiers are used to map electrodes across writing operations.

    Parameters
    ----------
    nwbfile : pynwb.NWBFile
        The NWB file from which to extract the electrode table information.

    Returns
    -------
    list[str]
        A list of unique keys, each representing a combination of channel name and
        group name from the electrodes table. If the electrodes table or the
        necessary columns are not present, an empty list is returned.
    """

    if nwbfile.electrodes is None:
        return []

    if "channel_name" not in nwbfile.electrodes.colnames or "group_name" not in nwbfile.electrodes.colnames:
        return []

    channel_names = nwbfile.electrodes["channel_name"][:]
    group_names = nwbfile.electrodes["group_name"][:]
    unique_keys = [f"{ch_name}_{gr_name}" for ch_name, gr_name in zip(channel_names, group_names)]

    return unique_keys


def get_electrode_table_indices_for_group(
    recording: TdtRecordingExtractor, nwbfile: NWBFile, group_name: str
) -> list[int]:
    """
    Get the indices of the electrodes in the NWBFile that correspond to the channels
    in a specific electrode group.

    This function matches the `channel_name` and `group_name` from the recording to
    the global identifiers in the NWBFile's electrodes table, returning the indices
    of these matching electrodes. Only electrodes belonging to the specified group_name
    are included.

    Parameters
    ----------
    recording : BaseRecording
        The recording object from which to extract channel and group names.
    nwbfile : pynwb.NWBFile
        The NWBFile containing the electrodes table to search for matches.
    group_name : str
        Name of the electrode group to get indices for.

    Returns
    -------
    list[int]
        A list of indices corresponding to the positions in the NWBFile's electrodes
        table that match the channels in the specified group.
    """
    from neuroconv.tools.spikeinterface.spikeinterface import (
        _get_channel_name,
        _get_group_name,
    )

    channel_names = _get_channel_name(recording=recording)
    group_names = _get_group_name(recording=recording)
    channel_global_ids = [
        f"{ch_name}_{gr_name}" for ch_name, gr_name in zip(channel_names, group_names) if gr_name == group_name
    ]
    table_global_ids = _get_electrodes_table_global_ids(nwbfile=nwbfile)
    electrode_table_indices = [table_global_ids.index(ch_id) for ch_id in channel_global_ids]

    return electrode_table_indices


from typing import Iterable, Optional

from tqdm import tqdm

from neuroconv.tools.hdmf import GenericDataChunkIterator
from neuroconv.tools.spikeinterface.spikeinterfacerecordingdatachunkiterator import (
    get_electrical_series_chunk_shape,
)


class Huang2025RecordingDataChunkIterator(GenericDataChunkIterator):
    """DataChunkIterator specifically for use in huang 2025 conversion."""

    def __init__(
        self,
        recording: TdtRecordingExtractor,
        channel_indices: list[int],
        segment_index: int = 0,
        return_scaled: bool = False,
        buffer_gb: Optional[float] = None,
        buffer_shape: Optional[tuple] = None,
        chunk_mb: Optional[float] = None,
        chunk_shape: Optional[tuple] = None,
        display_progress: bool = False,
        progress_bar_class: Optional[tqdm] = None,
        progress_bar_options: Optional[dict] = None,
    ):
        """
        Initialize an Iterable object which returns DataChunks with data and their selections on each iteration.
        This iterator differs from the default SpikeInterfaceRecordingDataChunkIterator in that it allows
        users to select a specific subset of channels to iterate over, which is useful for the huang 2025 dataset, in
        which the first two channels correspond to EEG and the last two channels correspond to EMG.

        Parameters
        ----------
        recording : SpikeInterfaceRecording
            The SpikeInterfaceRecording object (RecordingExtractor or BaseRecording) which handles the data access.
        channel_indices : list[int]
            The indices of the channels to include in the iteration. This allows for selecting a subset of channels
            (e.g., EEG and EMG channels) from the recording.
        segment_index : int, optional
            The recording segment to iterate on.
            Defaults to 0.
        return_scaled : bool, optional
            Whether to return the trace data in scaled units (uV, if True) or in the raw data type (if False).
            Defaults to False.
        buffer_gb : float, optional
            The upper bound on size in gigabytes (GB) of each selection from the iteration.
            The buffer_shape will be set implicitly by this argument.
            Cannot be set if `buffer_shape` is also specified.
            The default is 1GB.
        buffer_shape : tuple, optional
            Manual specification of buffer shape to return on each iteration.
            Must be a multiple of chunk_shape along each axis.
            Cannot be set if `buffer_gb` is also specified.
            The default is None.
        chunk_mb : float, optional
            The upper bound on size in megabytes (MB) of the internal chunk for the HDF5 dataset.
            The chunk_shape will be set implicitly by this argument.
            Cannot be set if `chunk_shape` is also specified.
            The default is 10MB, as recommended by the HDF5 group.
            For more details, search the hdf5 documentation for "Improving IO Performance Compressed Datasets".
        chunk_shape : tuple, optional
            Manual specification of the internal chunk shape for the HDF5 dataset.
            Cannot be set if `chunk_mb` is also specified.
            The default is None.
        display_progress : bool, optional
            Display a progress bar with iteration rate and estimated completion time.
        progress_bar_class : dict, optional
            The progress bar class to use.
            Defaults to tqdm.tqdm if the TQDM package is installed.
        progress_bar_options : dict, optional
            Dictionary of keyword arguments to be passed directly to tqdm.
            See https://github.com/tqdm/tqdm#parameters for options.
        """
        self.recording = recording
        self.segment_index = segment_index
        self.return_scaled = return_scaled
        self.channel_ids = recording.get_channel_ids()
        channel_indices = np.asarray(channel_indices, dtype=int)
        self.channel_ids = self.channel_ids[channel_indices]
        super().__init__(
            buffer_gb=buffer_gb,
            buffer_shape=buffer_shape,
            chunk_mb=chunk_mb,
            chunk_shape=chunk_shape,
            display_progress=display_progress,
            progress_bar_class=progress_bar_class,
            progress_bar_options=progress_bar_options,
        )

    def _get_default_chunk_shape(self, chunk_mb: float = 10.0) -> tuple[int, int]:
        assert chunk_mb > 0, f"chunk_mb ({chunk_mb}) must be greater than zero!"

        number_of_channels = len(self.channel_ids)
        number_of_frames = self.recording.get_num_frames(segment_index=self.segment_index)
        dtype = self.recording.get_dtype()

        chunk_shape = get_electrical_series_chunk_shape(
            number_of_channels=number_of_channels, number_of_frames=number_of_frames, dtype=dtype, chunk_mb=chunk_mb
        )

        return chunk_shape

    def _get_data(self, selection: tuple[slice]) -> Iterable:
        return self.recording.get_traces(
            segment_index=self.segment_index,
            channel_ids=self.channel_ids[selection[1]],
            start_frame=selection[0].start,
            end_frame=selection[0].stop,
            return_scaled=self.return_scaled,
        )

    def _get_dtype(self):
        return self.recording.get_dtype()

    def _get_maxshape(self):
        return (self.recording.get_num_samples(segment_index=self.segment_index), len(self.channel_ids))
