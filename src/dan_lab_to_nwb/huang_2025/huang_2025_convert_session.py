"""Primary script to run to convert an entire session for of data using the NWBConverter."""
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat

from dan_lab_to_nwb.huang_2025 import Huang2025NWBConverter
from neuroconv.utils import dict_deep_update, load_dict_from_file


def session_to_nwb(info_file_path: FilePath, output_dir_path: DirectoryPath, stub_test: bool = False):
    info_file_path = Path(info_file_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    source_data = dict()
    conversion_options = dict()

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

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)


if __name__ == "__main__":

    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/Test - TDT data")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb")
    stub_test = False

    # Example Session
    info_file_path = data_dir_path / "M301-241108-072001" / "Info.mat"
    session_to_nwb(
        info_file_path=info_file_path,
        output_dir_path=output_dir_path,
        stub_test=stub_test,
    )
