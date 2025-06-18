"""Primary class for converting optogenetic stimulation."""
import os
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import tdt
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

    def get_epoc_name(self, series_name: str):
        folder_path = Path(self.source_data["folder_path"])
        file_pattern_to_series_name_to_epoc_name = {
            "pTra_con": {
                "optogenetic_series_VTA_test_pulse": "St1_",
                "optogenetic_series_PFC_test_pulse": "St2_",
                "optogenetic_series_VTA_intense_stimulation": "Wi3_",
            },
            "opto1-Evoke12_2in1": {
                "optogenetic_series_VTA_test_pulse": "St1_",
                "optogenetic_series_PFC_test_pulse": "St2_",
                "optogenetic_series_VTA_intense_stimulation": "LasT",
            },
            "SBOX_R_evoke_2in1": {
                "optogenetic_series_VTA_test_pulse": "St1_",
                "optogenetic_series_PFC_test_pulse": "St2_",
            },
            "TDTb_R_evoke_2in1": {
                "optogenetic_series_VTA_test_pulse": "St1_",
                "optogenetic_series_PFC_test_pulse": "St2_",
            },
        }
        for file_pattern, series_name_to_epoc_name in file_pattern_to_series_name_to_epoc_name.items():
            if file_pattern in folder_path.parent.name:
                return series_name_to_epoc_name.get(series_name)
        raise ValueError(
            f"No matching file pattern found in {folder_path.parent}. Expected one of: {list(file_pattern_to_series_name_to_epoc_name.keys())}"
        )

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict):
        folder_path = Path(self.source_data["folder_path"])
        with open(os.devnull, "w") as f, redirect_stdout(f):
            tdt_photometry = tdt.read_block(folder_path, evtype=["epocs"])

        opto_metadata = metadata["Optogenetics"]
        for series_metadata in opto_metadata["OptogeneticSeries"]:
            series_name = series_metadata["name"]
            epoc_name = self.get_epoc_name(series_name=series_name)
            if epoc_name is None:
                continue
            onset_times = tdt_photometry.epocs[epoc_name].onset
            offset_times = tdt_photometry.epocs[epoc_name].offset
            power = series_metadata["power"]

            # Get timestamps and data from onset and offset times
            timestamps, data = [], []
            for onset_time, offset_time in zip(onset_times, offset_times):
                timestamps.append(onset_time)
                data.append(power)
                timestamps.append(offset_time)
                data.append(0)
            timestamps, data = np.array(timestamps, dtype=np.float64), np.array(data, dtype=np.float64)

            # Extract device and site metadata
            site_name = series_metadata["site_name"]
            site_metadata = next(
                site_meta for site_meta in opto_metadata["OptogeneticStimulusSite"] if site_meta["name"] == site_name
            )
            device_name = site_metadata["device_name"]
            device_metadata = next(
                device_meta for device_meta in opto_metadata["Device"] if device_meta["name"] == device_name
            )

            # Add Device
            if device_name in nwbfile.devices:
                device = nwbfile.devices[device_name]
            else:
                device = Device(**device_metadata)
                nwbfile.add_device(device)

            # Add OptogeneticStimulusSite
            if site_name in nwbfile.ogen_sites:
                site = nwbfile.ogen_sites[site_name]
            else:
                site = OptogeneticStimulusSite(
                    name=site_name,
                    device=device,
                    description=site_metadata["description"],
                    excitation_lambda=site_metadata["excitation_lambda"],
                    location=site_metadata["location"],
                )
                nwbfile.add_ogen_site(site)

            # Add OptogeneticSeries
            series = OptogeneticSeries(
                name=series_name,
                timestamps=timestamps,
                data=data,
                site=site,
                description=series_metadata["description"],
            )
            nwbfile.add_stimulus(series)
