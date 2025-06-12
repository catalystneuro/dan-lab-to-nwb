"""Primary class for converting behavior."""
from pathlib import Path

import numpy as np
from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface


class Huang2025DlcBehaviorInterface(BaseDataInterface):
    """Behavior interface for huang_2025_dlc conversion"""

    keywords = ["behavior"]

    def __init__(self, labels_file_path: FilePath):
        super().__init__(labels_file_path=labels_file_path)

        self.label_id_to_name = {
            1: "REM",
            2: "WAKE",
            3: "NREM",
        }

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict):
        labels_file_path = Path(self.source_data["labels_file_path"])
        label_ids = read_mat(filename=labels_file_path)["labels"]
        start_times = np.asarray(np.arange(len(label_ids)), dtype=np.float64)  # TODO: Get start_times for these labels
        stop_times = start_times + 1.0  # TODO: Get stop_times for these labels

        for label_id, start_time, stop_time in zip(label_ids, start_times, stop_times, strict=True):
            label_name = self.label_id_to_name[label_id]
            nwbfile.add_epoch(start_time=start_time, stop_time=stop_time, tags=[label_name])
