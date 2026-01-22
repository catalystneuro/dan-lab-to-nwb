"""Primary script to run to convert all sessions in a dataset using session_to_nwb."""
import datetime
import shutil
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Union
from zoneinfo import ZoneInfo

import pandas as pd
from pydantic import DirectoryPath
from pymatreader import read_mat
from tqdm import tqdm

from dan_lab_to_nwb.huang_2025_tdt.huang_2025_tdt_convert_session import session_to_nwb


def dataset_to_nwb(
    *,
    data_dir_path: DirectoryPath,
    output_dir_path: DirectoryPath,
    max_workers: int = 1,
    verbose: bool = True,
):
    """Convert the entire dataset to NWB.

    Parameters
    ----------
    data_dir_path : DirectoryPath
        The path to the directory containing the raw data.
    output_dir_path : DirectoryPath
        The path to the directory where the NWB files will be saved.
    max_workers : int, optional
        The number of workers to use for parallel processing, by default 1
    verbose : bool, optional
        Whether to print verbose output, by default True
    """
    data_dir_path = Path(data_dir_path)
    session_to_nwb_kwargs_per_session = get_session_to_nwb_kwargs_per_session(
        data_dir_path=data_dir_path,
    )

    futures = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for session_to_nwb_kwargs in session_to_nwb_kwargs_per_session:
            session_to_nwb_kwargs["output_dir_path"] = output_dir_path
            session_to_nwb_kwargs["verbose"] = verbose
            nwbfile_name = get_nwbfile_name(session_to_nwb_kwargs=session_to_nwb_kwargs)
            nwbfile_stem = Path(nwbfile_name).stem
            exception_file_path = output_dir_path / f"ERROR_{nwbfile_stem}.txt"
            futures.append(
                executor.submit(
                    safe_session_to_nwb,
                    session_to_nwb_kwargs=session_to_nwb_kwargs,
                    exception_file_path=exception_file_path,
                )
            )
        for _ in tqdm(as_completed(futures), total=len(futures)):
            pass


def safe_session_to_nwb(*, session_to_nwb_kwargs: dict, exception_file_path: Union[Path, str]):
    """Convert a session to NWB while handling any errors by recording error messages to the exception_file_path.

    Parameters
    ----------
    session_to_nwb_kwargs : dict
        The arguments for session_to_nwb.
    exception_file_path : Path
        The path to the file where the exception messages will be saved.
    """
    exception_file_path = Path(exception_file_path)
    try:
        session_to_nwb(**session_to_nwb_kwargs)
    except Exception as e:
        with open(exception_file_path, mode="w") as f:
            f.write(f"session_to_nwb_kwargs: \n {pformat(session_to_nwb_kwargs)}\n\n")
            f.write(traceback.format_exc())


def get_nwbfile_name(*, session_to_nwb_kwargs: dict) -> str:
    """Get the NWB file name based on the session_to_nwb_kwargs.

    Parameters
    ----------
    session_to_nwb_kwargs : dict
        The kwargs for session_to_nwb, which should contain the path to the info file.

    Returns
    -------
    str
        The NWB file name.
    """
    info_file_path = session_to_nwb_kwargs["info_file_path"]
    info = read_mat(filename=info_file_path)["Info"]
    session_id = info["blockname"]
    subject_id = session_to_nwb_kwargs["subject_id"]
    nwbfile_name = f"sub-{subject_id}_ses-{session_id}.nwb"
    return nwbfile_name


def read_excel_metadata(*, metadata_folder_path: DirectoryPath):
    """Read metadata from Excel files in the specified folder.

    Parameters
    ----------
    metadata_folder_path : DirectoryPath
        The path to the folder containing the metadata Excel files.

    Returns
    -------
    dict
        A dictionary mapping subject IDs to their metadata.
    """
    pst = ZoneInfo("US/Pacific")
    subject_id_to_metadata = {}
    metadata_folder_path = Path(metadata_folder_path)
    metadata_sub_folder_names = ["behavioral sum", "signal sum"]
    for sub_folder_name in metadata_sub_folder_names:
        metadata_sub_folder_path = metadata_folder_path / sub_folder_name
        for excel_file in metadata_sub_folder_path.glob("*.csv"):
            if excel_file.name.startswith("._"):
                continue
            df = pd.read_csv(excel_file)
            date_column_names = [name for name in df.columns if name.startswith("date")]
            setup_column_names = [name for name in df.columns if name.startswith("setup")]
            for _, row in df.iterrows():
                subject_id = row["mouse ID"]
                if subject_id not in subject_id_to_metadata:
                    subject_id_to_metadata[subject_id] = {}
                metadata = subject_id_to_metadata[subject_id]
                metadata["sex"] = "M" if row["M"] == 1 else "F"
                metadata["dob"] = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
                if "session_dates" not in metadata:
                    metadata["session_dates"] = []
                for date_column_name in date_column_names:
                    if pd.isna(row[date_column_name]):
                        continue
                    session_date = datetime.datetime.strptime(row[date_column_name], "%m/%d/%Y").replace(tzinfo=pst)
                    metadata["session_dates"].append(session_date)
                if "session_setups" not in metadata:
                    metadata["session_setups"] = []
                for setup_column_name in setup_column_names:
                    if pd.isna(row[setup_column_name]):
                        continue
                    session_setup = row[setup_column_name]
                    metadata["session_setups"].append(session_setup)
    return subject_id_to_metadata


def get_session_to_nwb_kwargs_per_session(
    *,
    data_dir_path: DirectoryPath,
):
    """Get the kwargs for session_to_nwb for each session in the dataset.

    Parameters
    ----------
    data_dir_path : DirectoryPath
        The path to the directory containing the raw data.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries containing the kwargs for session_to_nwb for each session.
    """
    pst = ZoneInfo("US/Pacific")
    sessions_to_skip = []

    data_dir_path = Path(data_dir_path)
    metadata_folder_path = data_dir_path / "metadata"
    subject_id_to_metadata = read_excel_metadata(metadata_folder_path=metadata_folder_path)
    session_to_nwb_kwargs_per_session = []
    dataset_folder_names = [
        "Setup - Bing",
        "Setup - WS8",
        "Setup - MollyFP",
    ]
    for folder_name in dataset_folder_names:
        dataset_folder = data_dir_path / folder_name
        for sub_folder in dataset_folder.iterdir():
            if not sub_folder.is_dir():
                continue
            for outer_session_folder in sub_folder.iterdir():
                # ex. M323-250120-142001 --> M323, M412_PN-250429-143001 --> M412_PN
                subject_id = outer_session_folder.name.split("-")[0]
                subject_id = subject_id.split("_")[0]  # ex. M323 --> M323, M412_PN --> M412
                if subject_id.endswith("R") or subject_id.endswith("L"):
                    subject_id = subject_id[:-1]  # ex. M267R --> M267, M267L --> M267
                if subject_id.startswith("BBB"):
                    subject_id = subject_id.replace("BBB", "M00")  # ex. BBB8 --> M008
                session_date_str = outer_session_folder.name.split("-")[1]  # ex. M323-250120-142001 --> 250120
                session_date = datetime.datetime.strptime(session_date_str, "%y%m%d").replace(tzinfo=pst)
                if not outer_session_folder.is_dir():
                    continue
                if outer_session_folder.name in sessions_to_skip:
                    continue
                if subject_id not in subject_id_to_metadata:
                    continue
                subject_metadata = subject_id_to_metadata[subject_id]
                if session_date not in subject_metadata["session_dates"]:
                    continue
                sex = subject_metadata["sex"]
                dob = subject_metadata["dob"]
                for session_folder in outer_session_folder.iterdir():
                    if not session_folder.is_dir():
                        continue
                    for segment_folder in session_folder.iterdir():
                        if not segment_folder.is_dir():
                            continue
                        info_file_path = segment_folder / "Info.mat"
                        video_file_path = next(segment_folder.glob("*.avi"))
                        tdt_fp_folder_path = segment_folder
                        tdt_ephys_folder_path = session_folder
                        session_to_nwb_kwargs = dict(
                            info_file_path=info_file_path,
                            video_file_path=video_file_path,
                            tdt_fp_folder_path=tdt_fp_folder_path,
                            tdt_ephys_folder_path=tdt_ephys_folder_path,
                            subject_id=subject_id,
                            sex=sex,
                            dob=dob,
                        )
                        session_to_nwb_kwargs_per_session.append(session_to_nwb_kwargs)

    return session_to_nwb_kwargs_per_session


if __name__ == "__main__":

    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb/huang_2025_tdt")
    max_workers = 10
    verbose = False

    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)

    dataset_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        max_workers=max_workers,
        verbose=verbose,
    )
