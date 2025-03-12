"""Primary script to run to convert an entire session for of data using the NWBConverter."""
import datetime
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat

from dan_lab_to_nwb.huang_2025 import Huang2025NWBConverter
from neuroconv.utils import dict_deep_update, load_dict_from_file


def session_to_nwb(
    info_file_path: FilePath,
    video_file_path: FilePath,
    tdt_fp_folder_path: DirectoryPath,
    tdt_ephys_folder_path: DirectoryPath,
    output_dir_path: DirectoryPath,
    stub_test: bool = False,
):
    info_file_path = Path(info_file_path)
    video_file_path = Path(video_file_path)
    tdt_fp_folder_path = Path(tdt_fp_folder_path)
    tdt_ephys_folder_path = Path(tdt_ephys_folder_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    source_data = dict()
    conversion_options = dict()

    # Add TDT LFP
    source_data["Recording"] = dict(folder_path=tdt_ephys_folder_path, gain=1.0, stream_id="4")
    conversion_options["Recording"] = dict(stub_test=stub_test, write_as="lfp")

    # Add Fiber Photometry
    source_data["FiberPhotometry"] = dict(folder_path=tdt_fp_folder_path)
    conversion_options["FiberPhotometry"] = dict(stub_test=stub_test)

    # Add Video
    source_data["Video"] = dict(file_paths=[video_file_path], metadata_key_name="VideoCamera1")
    conversion_options["Video"] = dict(stub_test=stub_test)

    # Add Optogenetics
    source_data["Optogenetics"] = dict(folder_path=tdt_fp_folder_path)
    conversion_options["Optogenetics"] = dict()

    converter = Huang2025NWBConverter(source_data=source_data)
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "huang_2025_metadata.yaml"
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

    # Overwrite video metadata
    metadata["Behavior"]["VideoCamera1"] = editable_metadata["Behavior"]["VideoCamera1"]

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)


def main():
    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/Test - TDT data")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb")
    stub_test = True

    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)

    # Example Session with "pTra_con" type optogenetics
    info_file_path = data_dir_path / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001" / "M301-241108-072001" / "Info.mat"
    video_file_path = (
        data_dir_path
        / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001"
        / "M301-241108-072001"
        / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001_M301-241108-072001_Cam1.avi"
    )
    tdt_fp_folder_path = data_dir_path / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001" / "M301-241108-072001"
    tdt_ephys_folder_path = data_dir_path / "Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001"
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        tdt_fp_folder_path=tdt_fp_folder_path,
        tdt_ephys_folder_path=tdt_ephys_folder_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )

    # Example Session with "opto" type optogenetics
    info_file_path = data_dir_path / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559" / "M301-240917-163001" / "Info.mat"
    video_file_path = (
        data_dir_path
        / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559"
        / "M301-240917-163001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559_M301-240917-163001_Cam1.avi"
    )
    tdt_fp_folder_path = data_dir_path / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559" / "M301-240917-163001"
    tdt_ephys_folder_path = data_dir_path / "Lindsay_SBO_opto1-Evoke12_2in1-240914-155559"
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
