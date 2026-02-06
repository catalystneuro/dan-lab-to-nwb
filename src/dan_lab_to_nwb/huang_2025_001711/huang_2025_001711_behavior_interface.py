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
from neuroconv.utils import get_base_schema


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

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        column_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the column"},
                "description": {"type": "string", "description": "Description of the column"},
            },
            "required": ["name", "description"],
            "additionalProperties": False,
        }
        metadata_schema["properties"]["Behavior"] = get_base_schema(tag="Behavior")
        metadata_schema["properties"]["Behavior"]["required"].append("BehavioralSummaryTable")
        metadata_schema["properties"]["Behavior"]["properties"]["BehavioralSummaryTable"] = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the behavioral summary table"},
                "description": {"type": "string", "description": "Description of the behavioral summary table"},
                "columns": {
                    "type": "array",
                    "items": column_schema,
                    "description": "Columns in the behavioral summary table",
                },
            },
            "required": ["name", "description", "columns"],
            "additionalProperties": False,
        }

        return metadata_schema

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict):
        # Load label data
        labels_file_path = Path(self.source_data["labels_file_path"])
        label_ids = read_mat(filename=labels_file_path)["labels"]
        start_times = np.arange(len(label_ids)) * 5.0
        stop_times = np.concatenate((start_times[1:], [start_times[-1] + 5.0]))

        # Add epochs for each behavior label
        for label_id, start_time, stop_time in zip(label_ids, start_times, stop_times, strict=True):
            label_name = self.label_id_to_name[label_id]
            nwbfile.add_epoch(start_time=start_time, stop_time=stop_time, tags=[label_name])

        # Load behavioral summary data
        behavioral_summary_file_path = Path(self.source_data["behavioral_summary_file_path"])
        behavioral_summary_df = pd.read_csv(behavioral_summary_file_path)
        session_name = labels_file_path.parent.parent.name.split("-")[-1]  # ex. M407-S1 --> S1
        session_summary_df = behavioral_summary_df[behavioral_summary_df["session"] == session_name]
        assert (
            len(session_summary_df) == 1
        ), f"Expected one summary row for session {session_name}, found {len(session_summary_df)}"

        # Get behavioral summary table metadata from metadata
        table_metadata = metadata["Behavior"]["BehavioralSummaryTable"]
        table_name = table_metadata["name"]
        table_description = table_metadata["description"]
        columns_metadata = table_metadata["columns"]

        # Add BehavioralSummaryTable
        behavioral_summary_table = DynamicTable(name=table_name, description=table_description)
        row_data = {}
        for column_meta in columns_metadata:
            behavioral_summary_table.add_column(
                name=column_meta["name"],
                description=column_meta["description"],
            )
            row_data[column_meta["name"]] = session_summary_df[column_meta["name"]].values[0]
        behavioral_summary_table.add_row(**row_data)
        behavior_module = get_module(nwbfile=nwbfile, name="behavior")
        behavior_module.add(behavioral_summary_table)
