"""Primary NWBConverter class for this dataset."""
from dan_lab_to_nwb.huang_2025_tdt import (
    Huang2025OptogeneticInterface,
    Huang2025TdtRecordingInterface,
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
    )
