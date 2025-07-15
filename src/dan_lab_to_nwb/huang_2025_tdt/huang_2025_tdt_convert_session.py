"""Primary script to run to convert an entire session for of data using the NWBConverter."""
import datetime
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat

from dan_lab_to_nwb.huang_2025_tdt import Huang2025NWBConverter
from neuroconv.utils import dict_deep_update, load_dict_from_file


def session_to_nwb(
    *,
    info_file_path: FilePath,
    output_dir_path: DirectoryPath,
    video_file_path: FilePath,
    tdt_fp_folder_path: DirectoryPath,
    tdt_ephys_folder_path: DirectoryPath,
    stub_test: bool = False,
    verbose: bool = True,
):
    info_file_path = Path(info_file_path)
    video_file_path = Path(video_file_path)
    tdt_fp_folder_path = Path(tdt_fp_folder_path)
    tdt_ephys_folder_path = Path(tdt_ephys_folder_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    source_data = dict()
    conversion_options = dict()

    # # Add TDT EEG and EMG
    # source_data["EEG"] = dict(folder_path=tdt_ephys_folder_path, gain=1.0, stream_id="4", es_key="ElectricalSeriesEEG")
    # conversion_options["EEG"] = dict(stub_test=stub_test, group_names=["ElectrodeGroupEEG"])
    # source_data["EMG"] = dict(folder_path=tdt_ephys_folder_path, gain=1.0, stream_id="4", es_key="ElectricalSeriesEMG")
    # conversion_options["EMG"] = dict(stub_test=stub_test, group_names=["ElectrodeGroupEMG"])

    # # Add Fiber Photometry
    # source_data["FiberPhotometry"] = dict(folder_path=tdt_fp_folder_path)
    # conversion_options["FiberPhotometry"] = dict(stub_test=stub_test)

    # # Add Video
    # if "Cam1" in video_file_path.name:
    #     video_name = "Video1"
    # elif "Cam2" in video_file_path.name:
    #     video_name = "Video2"
    # source_data["Video"] = dict(file_paths=[video_file_path], video_name=video_name)
    # conversion_options["Video"] = dict()

    # Add Optogenetics
    source_data["Optogenetics"] = dict(folder_path=tdt_fp_folder_path)
    conversion_options["Optogenetics"] = dict()

    converter = Huang2025NWBConverter(source_data=source_data, verbose=verbose)
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "huang_2025_tdt_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    info = read_mat(filename=info_file_path)["Info"]
    session_id = info["blockname"]
    subject_id = info["Subject"]
    pst = ZoneInfo("US/Pacific")
    session_start_time = datetime.datetime.strptime(info["Start"], "%I:%M:%S%p %m/%d/%Y").replace(tzinfo=pst)
    nwbfile_path = output_dir_path / f"sub-{subject_id}_ses-{session_id}.nwb"
    metadata["NWBFile"]["session_id"] = session_id
    metadata["Subject"]["subject_id"] = subject_id
    metadata["NWBFile"]["session_start_time"] = session_start_time

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)

    if verbose:
        print(f"Session {session_id} for subject {subject_id} converted successfully to NWB format at {nwbfile_path}")


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
