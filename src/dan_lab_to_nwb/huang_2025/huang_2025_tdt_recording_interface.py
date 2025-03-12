"""Primary class for converting TDT Ephys Recordings."""
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
