"""Primary class for converting optogenetic stimulation."""
import copy
import os
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import tdt
from hdmf.common import DynamicTableRegion, VectorData, VectorIndex
from ndx_ophys_devices import (
    Effector,
    ExcitationSource,
    ExcitationSourceModel,
    FiberInsertion,
    OpticalFiber,
    OpticalFiberModel,
    ViralVector,
    ViralVectorInjection,
)
from ndx_optogenetics import (
    OptogeneticEffectors,
    OptogeneticExperimentMetadata,
    # OptogeneticEpochsTable,
    OptogeneticPulsesTable,
    OptogeneticSitesTable,
    OptogeneticViruses,
    OptogeneticVirusInjections,
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
            "opto1_E_2": ["St1_", "St2_", "LasT"],
            "opto1_E12_2in1": ["St1_", "St2_", "LasT"],
            "SBOX_R_evoke_2in1": ["St1_", "St2_"],
            "TDTb_R_evoke_2in1": ["St1_", "St2_"],
        }
        self.epoc_name_to_stimulus_type = {
            "St1_": "test_pulse",
            "St2_": "test_pulse",
            "Wi3_": "intense_stimulation",
            "LasT": "intense_stimulation",
        }
        self.epoc_name_to_optogenetic_sites_table_row = {
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
            nwbfile.add_device_model(excitation_source_model)
        for excitation_source_metadata in opto_metadata["ExcitationSources"]:
            model_name = excitation_source_metadata["model"]
            if model_name in nwbfile.device_models:
                excitation_source_metadata["model"] = nwbfile.device_models[model_name]
            else:
                raise ValueError(
                    f"Excitation source model '{model_name}' not found in NWBFile devices. "
                    "Ensure that ExcitationSourceModels has a model with this name."
                )
            excitation_source = ExcitationSource(**excitation_source_metadata)
            nwbfile.add_device(excitation_source)
        for optical_fiber_model_metadata in opto_metadata["OpticalFiberModels"]:
            optical_fiber_model = OpticalFiberModel(**optical_fiber_model_metadata)
            nwbfile.add_device_model(optical_fiber_model)
        for optical_fiber_metadata in opto_metadata["OpticalFibers"]:
            model_name = optical_fiber_metadata["model"]
            if model_name in nwbfile.device_models:
                optical_fiber_metadata["model"] = nwbfile.device_models[model_name]
            else:
                raise ValueError(
                    f"Optical fiber model '{model_name}' not found in NWBFile devices. "
                    "Ensure that OpticalFiberModels has a model with this name."
                )
            insertion_metadata = optical_fiber_metadata["fiber_insertion"]
            fiber_insertion = FiberInsertion(**insertion_metadata)
            optical_fiber_metadata["fiber_insertion"] = fiber_insertion
            optical_fiber = OpticalFiber(**optical_fiber_metadata)
            nwbfile.add_device(optical_fiber)

        name_to_virus = {}
        for virus_metadata in opto_metadata["OptogeneticViruses"]:
            virus = ViralVector(**virus_metadata)
            name_to_virus[virus.name] = virus
        if len(name_to_virus) > 0:
            optogenetic_viruses = OptogeneticViruses(viral_vectors=list(name_to_virus.values()))
        else:
            optogenetic_viruses = None

        name_to_virus_injection = {}
        for virus_injection_metadata in opto_metadata["OptogeneticVirusInjections"]:
            if virus_injection_metadata["viral_vector"] in name_to_virus:
                virus_injection_metadata["viral_vector"] = name_to_virus[virus_injection_metadata["viral_vector"]]
            else:
                raise ValueError(
                    f"Virus '{virus_injection_metadata['viral_vector']}' not found in NWBFile viruses. "
                    "Ensure that OptogeneticViruses has a virus with this name."
                )
            virus_injection = ViralVectorInjection(**virus_injection_metadata)
            name_to_virus_injection[virus_injection.name] = virus_injection
        if len(name_to_virus_injection) > 0:
            optogenetic_virus_injections = OptogeneticVirusInjections(
                viral_vector_injections=list(name_to_virus_injection.values())
            )
        else:
            optogenetic_virus_injections = None

        name_to_effector = {}
        for effector_metadata in opto_metadata["OptogeneticEffectors"]:
            if effector_metadata["viral_vector_injection"] in name_to_virus_injection:
                if effector_metadata["viral_vector_injection"] in name_to_virus_injection:
                    effector_metadata["viral_vector_injection"] = name_to_virus_injection[
                        effector_metadata["viral_vector_injection"]
                    ]
                else:
                    raise ValueError(
                        f"Viral vector injection '{effector_metadata['viral_vector_injection']}' not found in NWBFile virus injections. "
                        "Ensure that OptogeneticVirusInjections has an injection with this name."
                    )
            effector = Effector(**effector_metadata)
            name_to_effector[effector.name] = effector
        if len(name_to_effector) > 0:
            optogenetic_effectors = OptogeneticEffectors(effectors=list(name_to_effector.values()))
        else:
            raise ValueError(
                "No optogenetic effectors found in metadata. Ensure that OptogeneticEffectors has at least one effector."
            )

        optogenetic_sites_table = OptogeneticSitesTable(
            description=opto_metadata["OptogeneticSitesTable"]["description"]
        )
        for row_metadata in opto_metadata["OptogeneticSitesTable"]["rows"]:
            row_metadata.pop("name")  # dict_deep_update requires a 'name' key, but we don't need it in the NWBFile
            excitation_source_name = row_metadata["excitation_source"]
            if excitation_source_name in nwbfile.devices:
                excitation_source = nwbfile.devices[excitation_source_name]
            else:
                raise ValueError(
                    f"Excitation source '{excitation_source_name}' not found in NWBFile devices. "
                    "Ensure that ExcitationSources has a source with this name."
                )
            optical_fiber_name = row_metadata["optical_fiber"]
            if optical_fiber_name in nwbfile.devices:
                optical_fiber = nwbfile.devices[optical_fiber_name]
            else:
                raise ValueError(
                    f"Optical fiber '{optical_fiber_name}' not found in NWBFile devices. "
                    "Ensure that OpticalFibers has a fiber with this name."
                )
            if "effector" in row_metadata:
                effector_name = row_metadata["effector"]
                if effector_name in name_to_effector:
                    effector = name_to_effector[effector_name]
                else:
                    raise ValueError(
                        f"Effector '{effector_name}' not found in NWBFile effectors. "
                        "Ensure that OptogeneticEffectors has an effector with this name."
                    )
            else:
                raise ValueError(
                    "Effector is required in OptogeneticSitesTable rows. "
                    "Ensure that OptogeneticEffectors has an effector for each site."
                )
            optogenetic_sites_table.add_row(
                excitation_source=excitation_source,
                optical_fiber=optical_fiber,
                effector=effector,
            )

        optogenetic_experiment_metadata = OptogeneticExperimentMetadata(
            optogenetic_sites_table=optogenetic_sites_table,
            optogenetic_viruses=optogenetic_viruses,
            optogenetic_virus_injections=optogenetic_virus_injections,
            optogenetic_effectors=optogenetic_effectors,
            stimulation_software=opto_metadata["stimulation_software"],
        )
        nwbfile.add_lab_meta_data(optogenetic_experiment_metadata)

        power_in_mW = opto_metadata["ExcitationSources"][0]["power_in_W"] * 1000  # Convert from Watts to mW
        wavelength_in_nm = opto_metadata["excitation_wavelength_in_nm"]

        column_name_to_data = {}
        column_name_to_description = {}
        colnames = [
            "start_time",
            "stop_time",
            "power_in_mW",
            "wavelength_in_nm",
        ]
        for col in OptogeneticPulsesTable.__columns__:
            if col["name"] not in colnames:
                continue
            column_name_to_data[col["name"]] = []
            column_name_to_description[col["name"]] = col["description"]
        colnames.append("stimulus_type")
        column_name_to_data["stimulus_type"] = []
        column_name_to_description[
            "stimulus_type"
        ] = "Type of optogenetic stimulus (e.g., 'test_pulse', 'intense_stimulation')"

        optogenetic_sites_data = []
        for epoc_name in self.epoc_names:
            stimulus_type = self.epoc_name_to_stimulus_type[epoc_name]
            onset_times = tdt_photometry.epocs[epoc_name].onset
            offset_times = tdt_photometry.epocs[epoc_name].offset
            row = self.epoc_name_to_optogenetic_sites_table_row[epoc_name]

            for onset_time, offset_time in zip(onset_times, offset_times, strict=True):
                column_name_to_data["start_time"].append(onset_time)
                column_name_to_data["stop_time"].append(offset_time)
                column_name_to_data["power_in_mW"].append(power_in_mW)
                column_name_to_data["wavelength_in_nm"].append(wavelength_in_nm)
                column_name_to_data["stimulus_type"].append(stimulus_type)

                optogenetic_sites_data.append(row)

        columns = [
            VectorData(name=colname, description=column_name_to_description[colname], data=column_name_to_data[colname])
            for colname in colnames
        ]
        optogenetic_sites = DynamicTableRegion(
            name="optogenetic_sites",
            description="Region of the optogenetic sites table corresponding to this pulse.",
            data=optogenetic_sites_data,
            table=optogenetic_sites_table,
        )
        colnames.append("optogenetic_sites")
        columns.append(optogenetic_sites)
        optogenetic_sites_index = VectorIndex(
            name="optogenetic_sites_index",
            target=optogenetic_sites,
            data=np.arange(1, len(optogenetic_sites_data) + 1),
        )
        columns.append(optogenetic_sites_index)
        opto_pulses_table = OptogeneticPulsesTable(
            name="optogenetic_pulses",
            description="Metadata about optogenetic stimulation parameters per pulse",
            colnames=colnames,
            columns=columns,
        )
        nwbfile.add_time_intervals(opto_pulses_table)
