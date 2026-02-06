"""Primary NWBConverter class for this dataset."""
import os
from contextlib import redirect_stdout
from pathlib import Path

import tdt

from dan_lab_to_nwb.huang_2025_001617 import (
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

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        tdt_fp_folder_path = Path(self.data_interface_objects["Optogenetics"].source_data["folder_path"])
        with open(os.devnull, "w") as f, redirect_stdout(f):
            tdt_photometry = tdt.read_block(tdt_fp_folder_path, evtype=["epocs"])
        video_timestamps = tdt_photometry.epocs["Cam1"].onset[:]
        self.data_interface_objects["Video"].set_aligned_timestamps([video_timestamps])
