"""Primary class for converting optogenetic stimulation."""
import copy
import os
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import tdt
from ndx_optogenetics import (
    ExcitationSource,
    ExcitationSourceModel,
    OpticalFiber,
    OpticalFiberLocationsTable,
    OpticalFiberModel,
    OptogeneticEpochsTable,
    OptogeneticExperimentMetadata,
    OptogeneticVirus,
    OptogeneticViruses,
    OptogeneticVirusInjection,
    OptogeneticVirusInjections,
)
from pydantic import DirectoryPath
from pynwb.device import Device
from pynwb.file import NWBFile
from pynwb.ogen import OptogeneticSeries, OptogeneticStimulusSite

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
        for file_pattern, epoc_names in file_pattern_to_epoc_names.items():
            if file_pattern in folder_path.parent.name:
                self.epoc_names = epoc_names
                return
        raise ValueError(
            f"No matching file pattern found in {folder_path.parent}. Expected one of: {list(file_pattern_to_epoc_names.keys())}"
        )

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict):
        print("add_to_nwbfile()")
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

        optogenetic_viruses = OptogeneticViruses(optogenetic_virus=[])
        optogenetic_virus_injections = OptogeneticVirusInjections(optogenetic_virus_injections=[])
        optogenetic_experiment_metadata = OptogeneticExperimentMetadata(
            optical_fiber_locations_table=optical_fiber_locations_table,
            stimulation_software=opto_metadata["stimulation_software"],
            optogenetic_viruses=optogenetic_viruses,
            optogenetic_virus_injections=optogenetic_virus_injections,
        )
        nwbfile.add_lab_meta_data(optogenetic_experiment_metadata)
        print("Added optogenetic experiment metadata to NWBFile")

        power_in_mW = opto_metadata["ExcitationSources"][0]["power_in_W"] * 1000  # Convert from Watts to mW

        column_name_to_data = dict(
            start_time=[],
            stop_time=[],
            stimulation_on=[],
            pulse_length_in_ms=[],
            period_in_ms=[],
            number_pulses_per_pulse_train=[],
            number_trains=[],
            intertrain_interval_in_ms=[],
            power_in_mW=[],
        )
        stimulus_types = []
        for epoc_name in self.epoc_names:
            print(f"Processing epoc: {epoc_name}")
            stimulus_type = self.epoc_name_to_stimulus_type[epoc_name]
            onset_times = tdt_photometry.epocs[epoc_name].onset
            offset_times = tdt_photometry.epocs[epoc_name].offset

            for onset_time, offset_time in zip(onset_times, offset_times, strict=True):
                pulse_length_in_ms = (offset_time - onset_time) * 1000  # Convert to milliseconds
                # opto_epochs_table.add_row(
                #     stimulus_type=stimulus_type,
                #     start_time=onset_time,
                #     stop_time=offset_time,
                #     stimulation_on=True,
                #     pulse_length_in_ms=pulse_length_in_ms,
                #     period_in_ms=pulse_length_in_ms,
                #     number_pulses_per_pulse_train=1,
                #     number_trains=1,
                #     intertrain_interval_in_ms=0.0,
                #     power_in_mW=power_in_mW,
                # )
                column_name_to_data["start_time"].append(onset_time)
                column_name_to_data["stop_time"].append(offset_time)
                column_name_to_data["stimulation_on"].append(True)
                column_name_to_data["pulse_length_in_ms"].append(pulse_length_in_ms)
                column_name_to_data["period_in_ms"].append(pulse_length_in_ms)
                column_name_to_data["number_pulses_per_pulse_train"].append(1)
                column_name_to_data["number_trains"].append(1)
                column_name_to_data["intertrain_interval_in_ms"].append(0.0)
                column_name_to_data["power_in_mW"].append(power_in_mW)
                stimulus_types.append(stimulus_type)

        stimulus_types = np.array(stimulus_types, dtype="S")
        colnames = list(column_name_to_data.keys())
        columns = [{"name": colname, "data": column_name_to_data[colname]} for colname in colnames]
        # colnames.append("stimulus_type")
        # columns.append({"name": "stimulus_type", "data": stimulus_types, "description": "Type of optogenetic stimulus (e.g., 'test_pulse', 'intense_stimulation')"})
        opto_epochs_table = OptogeneticEpochsTable(
            name="optogenetic_epochs",
            description="Metadata about optogenetic stimulation parameters per epoch",
            colnames=colnames,
            columns=columns,
        )
        nwbfile.add_time_intervals(opto_epochs_table)
