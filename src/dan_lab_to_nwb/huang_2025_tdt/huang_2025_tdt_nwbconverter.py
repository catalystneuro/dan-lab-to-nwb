"""Primary NWBConverter class for this dataset."""
from dan_lab_to_nwb.huang_2025_tdt import (
    Huang2025OptogeneticInterface,
    Huang2025TdtRecordingInterface,
)
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    ExternalVideoInterface,
    TDTFiberPhotometryInterface,
)


class Huang2025NWBConverter(NWBConverter):
    """Primary conversion class for my extracellular electrophysiology dataset."""

    data_interface_classes = dict(
        EEG=Huang2025TdtRecordingInterface,
        EMG=Huang2025TdtRecordingInterface,
        FiberPhotometry=TDTFiberPhotometryInterface,
        Video=ExternalVideoInterface,
        Optogenetics=Huang2025OptogeneticInterface,
    )
