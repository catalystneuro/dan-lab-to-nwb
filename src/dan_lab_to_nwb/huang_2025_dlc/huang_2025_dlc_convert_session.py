"""Primary script to run to convert an entire session for of data using the NWBConverter."""
import datetime
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat

from dan_lab_to_nwb.huang_2025_dlc import Huang2025DLCNWBConverter
from neuroconv.utils import dict_deep_update, load_dict_from_file


def session_to_nwb(
    *,
    info_file_path: FilePath,
    output_dir_path: DirectoryPath,
    video_file_path: FilePath,
    dlc_file_path: FilePath,
    labels_file_path: FilePath,
    stub_test: bool = False,
    verbose: bool = True,
):
    info_file_path = Path(info_file_path)
    video_file_path = Path(video_file_path)
    dlc_file_path = Path(dlc_file_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    source_data = dict()
    conversion_options = dict()

    # Add Video
    if "Cam1" in video_file_path.name:
        video_name = "Video1"
    elif "Cam2" in video_file_path.name:
        video_name = "Video2"
    source_data["Video"] = dict(file_paths=[video_file_path], video_name=video_name)
    conversion_options["Video"] = dict()

    # Add DeepLabCut
    source_data["DeepLabCut"] = dict(file_path=dlc_file_path)
    conversion_options["DeepLabCut"] = dict()

    # Add Behavior
    source_data["Behavior"] = dict(labels_file_path=labels_file_path)
    conversion_options["Behavior"] = dict()

    converter = Huang2025DLCNWBConverter(source_data=source_data, verbose=verbose)
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "huang_2025_dlc_metadata.yaml"
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
    metadata["PoseEstimation"]["PoseEstimationContainers"]["PoseEstimationDeepLabCut"]["original_videos"] = [
        str(video_file_path)
    ]

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)

    if verbose:
        print(f"Session {session_id} for subject {subject_id} converted successfully to NWB format at {nwbfile_path}")


def main():
    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/Test - video analysis")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb/huang_2025_dlc")
    stub_test = True

    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)

    # Example Session
    info_file_path = data_dir_path / "M407" / "M407-S1" / "check_FP" / "Info.mat"
    video_file_path = (
        data_dir_path / "M407" / "M407-S1" / "Lindsay_SBOX_2animals_R-250411-223215_M405_M407-250412-081001_Cam2.avi"
    )
    dlc_file_path = (
        data_dir_path
        / "M407"
        / "M407-S1"
        / "Lindsay_SBOX_2animals_R-250411-223215_M405_M407-250412-081001_Cam2DLC_resnet50_Box2BehaviorSep10shuffle1_100000.h5"
    )
    # /Volumes/T7/CatalystNeuro/Dan/Test - video analysis/M407/M407-S1/check_FP/labels.mat
    labels_file_path = data_dir_path / "M407" / "M407-S1" / "check_FP" / "labels.mat"
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        dlc_file_path=dlc_file_path,
        labels_file_path=labels_file_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )


if __name__ == "__main__":
    main()
