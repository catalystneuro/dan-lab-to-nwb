"""Primary NWBConverter class for this dataset."""
from dan_lab_to_nwb.huang_2025 import Huang2025BehaviorInterface
from neuroconv import NWBConverter

from neuroconv.datainterfaces import TDTFiberPhotometryInterface, VideoInterace


class Huang2025NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        Behavior=Huang2025BehaviorInterface,
        FiberPhotometry=TDTFiberPhotometryInterface,
        Video=VideoInterface,
    )
