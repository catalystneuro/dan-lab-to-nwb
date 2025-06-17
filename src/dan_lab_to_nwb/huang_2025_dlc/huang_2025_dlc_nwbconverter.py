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
