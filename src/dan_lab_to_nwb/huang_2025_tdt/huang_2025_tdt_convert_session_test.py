"""Primary script to run to convert an entire session of data using the NWBConverter.
This script converts the testing example sessions provided in the Test - TDT data folder.
"""
import datetime
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat

from dan_lab_to_nwb.huang_2025_tdt import Huang2025NWBConverter
from dan_lab_to_nwb.huang_2025_tdt.huang_2025_tdt_convert_session import session_to_nwb
from neuroconv.utils import dict_deep_update, load_dict_from_file


def main():
    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/Test - TDT data")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb/huang_2025_tdt")
    stub_test = True

    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)

    # Example Session with "pTra_con" type optogenetics
    info_file_path = (
        data_dir_path
        / "ExampleSessions"
        / "M301-241108-072001"
        / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001"
        / "M301-241108-072001"
        / "Info.mat"
    )
    video_file_path = (
        data_dir_path
        / "ExampleSessions"
        / "M301-241108-072001"
        / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001"
        / "M301-241108-072001"
        / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001_M301-241108-072001_Cam1.avi"
    )
    tdt_fp_folder_path = (
        data_dir_path
        / "ExampleSessions"
        / "M301-241108-072001"
        / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001"
        / "M301-241108-072001"
    )
    tdt_ephys_folder_path = (
        data_dir_path / "ExampleSessions" / "M301-241108-072001" / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001"
    )
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        tdt_fp_folder_path=tdt_fp_folder_path,
        tdt_ephys_folder_path=tdt_ephys_folder_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )

    # Example Session with "opto" type optogenetics
    info_file_path = (
        data_dir_path
        / "ExampleSessions"
        / "M301-240917-163001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559"
        / "M301-240917-163001"
        / "Info.mat"
    )
    video_file_path = (
        data_dir_path
        / "ExampleSessions"
        / "M301-240917-163001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559"
        / "M301-240917-163001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559_M301-240917-163001_Cam1.avi"
    )
    tdt_fp_folder_path = (
        data_dir_path
        / "ExampleSessions"
        / "M301-240917-163001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559"
        / "M301-240917-163001"
    )
    tdt_ephys_folder_path = (
        data_dir_path / "ExampleSessions" / "M301-240917-163001" / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559"
    )
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        tdt_fp_folder_path=tdt_fp_folder_path,
        tdt_ephys_folder_path=tdt_ephys_folder_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )

    # Example Session with "SBOX_R" type optogenetics
    info_file_path = (
        data_dir_path
        / "WS8-202504"
        / "M315-250417-082001"
        / "Lindsay_SBOX_R_evoke_2in1-250416-184040"
        / "M315-250417-082001"
        / "Info.mat"
    )
    video_file_path = (
        data_dir_path
        / "WS8-202504"
        / "M315-250417-082001"
        / "Lindsay_SBOX_R_evoke_2in1-250416-184040"
        / "M315-250417-082001"
        / "Lindsay_SBOX_R_evoke_2in1-250416-184040_M315-250417-082001_Cam1.avi"
    )
    tdt_fp_folder_path = (
        data_dir_path
        / "WS8-202504"
        / "M315-250417-082001"
        / "Lindsay_SBOX_R_evoke_2in1-250416-184040"
        / "M315-250417-082001"
    )
    tdt_ephys_folder_path = (
        data_dir_path / "WS8-202504" / "M315-250417-082001" / "Lindsay_SBOX_R_evoke_2in1-250416-184040"
    )
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        tdt_fp_folder_path=tdt_fp_folder_path,
        tdt_ephys_folder_path=tdt_ephys_folder_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )

    # Example Session with "TDTb_R" type optogenetics
    info_file_path = (
        data_dir_path
        / "Bing-202504"
        / "M412-250421-072001"
        / "Lindsay_TDTb_R_evoke_2in1-250421-000320"
        / "M412-250421-072001"
        / "Info.mat"
    )
    video_file_path = (
        data_dir_path
        / "Bing-202504"
        / "M412-250421-072001"
        / "Lindsay_TDTb_R_evoke_2in1-250421-000320"
        / "M412-250421-072001"
        / "Lindsay_TDTb_R_evoke_2in1-250421-000320_M412-250421-072001_Cam1.avi"
    )
    tdt_fp_folder_path = (
        data_dir_path
        / "Bing-202504"
        / "M412-250421-072001"
        / "Lindsay_TDTb_R_evoke_2in1-250421-000320"
        / "M412-250421-072001"
    )
    tdt_ephys_folder_path = (
        data_dir_path / "Bing-202504" / "M412-250421-072001" / "Lindsay_TDTb_R_evoke_2in1-250421-000320"
    )
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        tdt_fp_folder_path=tdt_fp_folder_path,
        tdt_ephys_folder_path=tdt_ephys_folder_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )


if __name__ == "__main__":
    main()
