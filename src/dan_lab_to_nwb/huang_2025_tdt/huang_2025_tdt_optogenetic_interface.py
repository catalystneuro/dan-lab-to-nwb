"""Primary class for converting optogenetic stimulation."""
import copy
import os
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import tdt
from hdmf.common import DynamicTableRegion, VectorData
from ndx_optogenetics import (
    ExcitationSource,
    ExcitationSourceModel,
    OpticalFiber,
    OpticalFiberLocationsTable,
    OpticalFiberModel,
    OptogeneticEpochsTable,
    OptogeneticExperimentMetadata,
)
from pydantic import DirectoryPath
from pynwb.file import NWBFile

from neuroconv.basedatainterface import BaseDataInterface


class Huang2025OptogeneticInterface(BaseDataInterface):
    """Optogenetic interface for huang_2025 conversion"""

    keywords = ["optogenetics"]

    def __init__(self, folder_path: DirectoryPath):
        super().__init__(folder_path=folder_path)

        folder_path = Path(folder_path)
        file_pattern_to_epoc_names = {
            "pTra_con": ["St1_", "St2_", "Wi3_"],
            "opto1-Evoke12_2in1": ["St1_", "St2_", "LasT"],
        }
        self.epoc_name_to_stimulus_type = {
            "St1_": "test_pulse",
            "St2_": "test_pulse",
            "Wi3_": "intense_stimulation",
            "LasT": "intense_stimulation",
        }
        self.epoc_name_to_optical_fiber_locations_table_row = {
            "St1_": 0,
            "St2_": 1,
            "Wi3_": 0,
            "LasT": 0,
        }
        for file_pattern, epoc_names in file_pattern_to_epoc_names.items():
            if file_pattern in folder_path.parent.name:
                self.epoc_names = epoc_names
                return
        raise ValueError(
            f"No matching file pattern found in {folder_path.parent}. Expected one of: {list(file_pattern_to_epoc_names.keys())}"
        )

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict):
        folder_path = Path(self.source_data["folder_path"])
        with open(os.devnull, "w") as f, redirect_stdout(f):
            tdt_photometry = tdt.read_block(folder_path, evtype=["epocs"])

        opto_metadata = copy.deepcopy(metadata["Optogenetics"])
        for excitation_source_model_metadata in opto_metadata["ExcitationSourceModels"]:
            excitation_source_model = ExcitationSourceModel(**excitation_source_model_metadata)
            nwbfile.add_device(excitation_source_model)
        for excitation_source_metadata in opto_metadata["ExcitationSources"]:
            model_name = excitation_source_metadata["model"]
            if model_name in nwbfile.devices:
                excitation_source_metadata["model"] = nwbfile.devices[model_name]
            else:
                raise ValueError(
                    f"Excitation source model '{model_name}' not found in NWBFile devices. "
                    "Ensure that ExcitationSourceModels has a model with this name."
                )
            excitation_source = ExcitationSource(**excitation_source_metadata)
            nwbfile.add_device(excitation_source)
        for optical_fiber_model_metadata in opto_metadata["OpticalFiberModels"]:
            optical_fiber_model = OpticalFiberModel(**optical_fiber_model_metadata)
            nwbfile.add_device(optical_fiber_model)
        for optical_fiber_metadata in opto_metadata["OpticalFibers"]:
            model_name = optical_fiber_metadata["model"]
            if model_name in nwbfile.devices:
                optical_fiber_metadata["model"] = nwbfile.devices[model_name]
            else:
                raise ValueError(
                    f"Optical fiber model '{model_name}' not found in NWBFile devices. "
                    "Ensure that OpticalFiberModels has a model with this name."
                )
            optical_fiber = OpticalFiber(**optical_fiber_metadata)
            nwbfile.add_device(optical_fiber)
        optical_fiber_locations_table = OpticalFiberLocationsTable(
            description=opto_metadata["OpticalFiberLocationsTable"]["description"],
            reference=opto_metadata["OpticalFiberLocationsTable"]["reference"],
        )
        for row_metadata in opto_metadata["OpticalFiberLocationsTable"]["rows"]:
            row_metadata.pop("name")  # dict_deep_update requires a 'name' key, but we don't need it in the NWBFile
            excitation_source_name = row_metadata["excitation_source"]
            if excitation_source_name in nwbfile.devices:
                row_metadata["excitation_source"] = nwbfile.devices[excitation_source_name]
            else:
                raise ValueError(
                    f"Excitation source '{excitation_source_name}' not found in NWBFile devices. "
                    "Ensure that ExcitationSources has a source with this name."
                )
            optical_fiber_name = row_metadata["optical_fiber"]
            if optical_fiber_name in nwbfile.devices:
                row_metadata["optical_fiber"] = nwbfile.devices[optical_fiber_name]
            else:
                raise ValueError(
                    f"Optical fiber '{optical_fiber_name}' not found in NWBFile devices. "
                    "Ensure that OpticalFibers has a fiber with this name."
                )
            optical_fiber_locations_table.add_row(**row_metadata)

        optogenetic_experiment_metadata = OptogeneticExperimentMetadata(
            optical_fiber_locations_table=optical_fiber_locations_table,
            stimulation_software=opto_metadata["stimulation_software"],
        )
        nwbfile.add_lab_meta_data(optogenetic_experiment_metadata)

        power_in_mW = opto_metadata["ExcitationSources"][0]["power_in_W"] * 1000  # Convert from Watts to mW

        column_name_to_data = {}
        column_name_to_description = {}
        colnames = [
            "start_time",
            "stop_time",
            "stimulation_on",
            "pulse_length_in_ms",
            "period_in_ms",
            "number_pulses_per_pulse_train",
            "number_trains",
            "intertrain_interval_in_ms",
            "power_in_mW",
        ]
        for col in OptogeneticEpochsTable.__columns__:
            if col["name"] not in colnames:
                continue
            column_name_to_data[col["name"]] = []
            column_name_to_description[col["name"]] = col["description"]
        colnames.append("stimulus_type")
        column_name_to_data["stimulus_type"] = []
        column_name_to_description[
            "stimulus_type"
        ] = "Type of optogenetic stimulus (e.g., 'test_pulse', 'intense_stimulation')"

        optical_fiber_locations_table_region_data = []
        for epoc_name in self.epoc_names:
            stimulus_type = self.epoc_name_to_stimulus_type[epoc_name]
            onset_times = tdt_photometry.epocs[epoc_name].onset
            offset_times = tdt_photometry.epocs[epoc_name].offset
            row = self.epoc_name_to_optical_fiber_locations_table_row[epoc_name]

            for onset_time, offset_time in zip(onset_times, offset_times, strict=True):
                pulse_length_in_ms = (offset_time - onset_time) * 1000  # Convert to milliseconds
                column_name_to_data["start_time"].append(onset_time)
                column_name_to_data["stop_time"].append(offset_time)
                column_name_to_data["stimulation_on"].append(True)
                column_name_to_data["pulse_length_in_ms"].append(pulse_length_in_ms)
                column_name_to_data["period_in_ms"].append(pulse_length_in_ms)
                column_name_to_data["number_pulses_per_pulse_train"].append(1)
                column_name_to_data["number_trains"].append(1)
                column_name_to_data["intertrain_interval_in_ms"].append(0.0)
                column_name_to_data["power_in_mW"].append(power_in_mW)
                column_name_to_data["stimulus_type"].append(stimulus_type)

                optical_fiber_locations_table_region_data.append(row)

        columns = [
            VectorData(name=colname, description=column_name_to_description[colname], data=column_name_to_data[colname])
            for colname in colnames
        ]
        optical_fiber_locations_table_region = DynamicTableRegion(
            name="optical_fiber_locations_table_region",
            description="Region of the optical fiber locations table corresponding to this epoch.",
            data=optical_fiber_locations_table_region_data,
            table=optical_fiber_locations_table,
        )
        colnames.append("optical_fiber_locations_table_region")
        columns.append(optical_fiber_locations_table_region)
        opto_epochs_table = OptogeneticEpochsTable(
            name="optogenetic_epochs",
            description="Metadata about optogenetic stimulation parameters per epoch",
            colnames=colnames,
            columns=columns,
        )
        nwbfile.add_time_intervals(opto_epochs_table)
