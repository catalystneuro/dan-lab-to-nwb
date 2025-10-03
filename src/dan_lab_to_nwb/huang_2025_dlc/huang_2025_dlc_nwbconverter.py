"""Primary NWBConverter class for this dataset."""
from dan_lab_to_nwb.huang_2025_dlc import (
    Huang2025DlcBehaviorInterface,
    Huang2025DlcEcephysMatInterface,
)
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    DeepLabCutInterface,
    ExternalVideoInterface,
)


class Huang2025DLCNWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Video=ExternalVideoInterface,
        DeepLabCut=DeepLabCutInterface,
        Behavior=Huang2025DlcBehaviorInterface,
        Ecephys=Huang2025DlcEcephysMatInterface,
    )

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        video_timestamps = self.data_interface_objects["Video"].get_timestamps()[0]
        self.data_interface_objects["DeepLabCut"].set_aligned_timestamps(video_timestamps)
