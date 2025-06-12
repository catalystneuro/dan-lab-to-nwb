"""Primary class for converting behavior."""
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat
from pynwb.core import DynamicTable
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface
from neuroconv.tools.nwb_helpers import get_module


class Huang2025DlcBehaviorInterface(BaseDataInterface):
    """Behavior interface for huang_2025_dlc conversion"""

    keywords = ["behavior"]

    def __init__(self, labels_file_path: FilePath, behavioral_summary_file_path: FilePath):
        super().__init__(labels_file_path=labels_file_path, behavioral_summary_file_path=behavioral_summary_file_path)

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

        behavioral_summary_file_path = Path(self.source_data["behavioral_summary_file_path"])
        behavioral_summary_df = pd.read_csv(behavioral_summary_file_path)
        session_name = labels_file_path.parent.parent.name.split("-")[-1]  # ex. M407-S1 --> S1
        session_summary_df = behavioral_summary_df[behavioral_summary_df["session"] == session_name]
        assert (
            len(session_summary_df) == 1
        ), f"Expected one summary row for session {session_name}, found {len(session_summary_df)}"

        for label_id, start_time, stop_time in zip(label_ids, start_times, stop_times, strict=True):
            label_name = self.label_id_to_name[label_id]
            nwbfile.add_epoch(start_time=start_time, stop_time=stop_time, tags=[label_name])

        behavioral_summary_table = DynamicTable(
            name="behavioral_summary", description="Summary of behavioral states for the session"
        )
        behavioral_summary_table.add_column(name="t_LM", description="Fraction of time spent in locomotion.")
        behavioral_summary_table.add_column(name="t_NL", description="Fraction of time spent in non-locomotion.")
        behavioral_summary_table.add_column(name="t_QW", description="Fraction of time spent in quiet wakefulness.")
        behavioral_summary_table.add_column(name="t_NREM", description="Fraction of time spent in NREM sleep.")
        behavioral_summary_table.add_column(name="t_REM", description="Fraction of time spent in REM sleep.")
        behavioral_summary_table.add_column(
            name="distance_in_nest", description="Total distance traveled while in the nest in cm."
        )  # TODO: Confirm units
        behavioral_summary_table.add_column(
            name="distance_out_of_nest", description="Total distance traveled while out of the nest in cm."
        )  # TODO: Confirm units
        behavioral_summary_table.add_column(name="time_in_nest", description="Total time spent in the nest in seconds.")
        behavioral_summary_table.add_column(
            name="time_out_of_nest", description="Total time spent out of the nest in seconds."
        )
        behavioral_summary_table.add_row(
            t_LM=session_summary_df["t_LM"].values[0],
            t_NL=session_summary_df["t_NL"].values[0],
            t_QW=session_summary_df["t_QW"].values[0],
            t_NREM=session_summary_df["t_NREM"].values[0],
            t_REM=session_summary_df["t_REM"].values[0],
            distance_in_nest=session_summary_df["distance_in_nest"].values[0],
            distance_out_of_nest=session_summary_df["distance_out_of_nest"].values[0],
            time_in_nest=session_summary_df["time_in_nest"].values[0],
            time_out_of_nest=session_summary_df["time_out_of_nest"].values[0],
        )
        behavior_module = get_module(nwbfile=nwbfile, name="behavior")
        behavior_module.add(behavioral_summary_table)
