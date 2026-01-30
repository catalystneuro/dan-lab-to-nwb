"""Primary script to run to convert all sessions in a dataset using session_to_nwb."""
import datetime
import shutil
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Literal, Union
from zoneinfo import ZoneInfo

import pandas as pd
from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat
from tqdm import tqdm

from dan_lab_to_nwb.huang_2025_tdt.huang_2025_tdt_convert_session import session_to_nwb
from dan_lab_to_nwb.huang_2025_tdt.reorganize_data import find_tdt_folders


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
        setup="Bing",
        metadata_subfolder_name="opto-behavioral sum",
    )
    for kwargs in session_to_nwb_kwargs_per_session:
        kwargs["skip_fiber_photometry"] = True

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


def collect_excel_metadata(*, metadata_folder_path: DirectoryPath):
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
    sheet_name_to_subject_id_to_metadata: dict[str, dict[str, dict]] = {}
    metadata_folder_path = Path(metadata_folder_path)
    for excel_file in metadata_folder_path.glob("*.csv"):
        if excel_file.name.startswith("._"):
            continue
        subject_id_to_metadata = read_metadata(excel_file)
        sheet_name_to_subject_id_to_metadata[excel_file.stem] = subject_id_to_metadata
    return sheet_name_to_subject_id_to_metadata


def read_metadata(excel_file: FilePath) -> dict[str, dict]:
    """Read metadata from a single csv file.

    Parameters
    ----------
    pst : ZoneInfo
        The Pacific time zone info.
    excel_file : Path
        The path to the metadata csv file.

    Returns
    -------
    dict
        A dictionary mapping subject IDs to their metadata.
    """
    subject_id_to_metadata = {}
    pst = ZoneInfo("US/Pacific")
    df = pd.read_csv(excel_file)
    date_column_names = [name for name in df.columns if name.startswith("date")]
    setup_column_names = [name for name in df.columns if name.startswith("setup")]
    record_fiber_column_names = [name for name in df.columns if name.startswith("Record fiber")]
    has_record_fiber = bool(len(record_fiber_column_names))
    for _, row in df.iterrows():
        subject_id = row["mouse ID"]
        if subject_id not in subject_id_to_metadata:
            subject_id_to_metadata[subject_id] = {}
        metadata = subject_id_to_metadata[subject_id]
        metadata["sex"] = "M" if row["M"] == 1 else "F"
        metadata["dob"] = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
        metadata["optogenetic_site_name"] = row["Stim region"]
        virus_volume_column_names = [name for name in df.columns if name.startswith("virus volume")]
        optogenetic_virus_volume_column_name = virus_volume_column_names[0]
        optogenetic_virus_volume_in_nL = float(
            row[optogenetic_virus_volume_column_name].replace("nL", "")
        )  # 300nL --> 300.0
        metadata["optogenetic_virus_volume_in_uL"] = optogenetic_virus_volume_in_nL / 1000.0
        if "Record region" in df.columns:
            metadata["fiber_photometry_site_name"] = row["Record region"]
            fiber_photometry_virus_volume_column_name = virus_volume_column_names[1]
            fiber_photometry_virus_volume_in_nL = float(
                row[fiber_photometry_virus_volume_column_name].replace("nL", "")
            )  # 300nL --> 300.0
            metadata["fiber_photometry_virus_volume_in_uL"] = fiber_photometry_virus_volume_in_nL / 1000.0
        if "session_dates" not in metadata:
            metadata["session_dates"] = []
        if "session_setups" not in metadata:
            metadata["session_setups"] = []
        if "record_fibers" not in metadata and has_record_fiber:
            metadata["record_fibers"] = []
        for index, date_column_name in enumerate(date_column_names):
            setup_column_name = setup_column_names[index]
            if pd.isna(row[date_column_name]):
                continue
            assert not pd.isna(
                row[setup_column_name]
            ), f"Setup missing for subject {subject_id} on date {row[date_column_name]}"
            session_date = datetime.datetime.strptime(row[date_column_name], "%m/%d/%Y").replace(tzinfo=pst)
            session_setup = row[setup_column_name]
            metadata["session_setups"].append(session_setup)
            metadata["session_dates"].append(session_date)

            if has_record_fiber:
                record_fiber_column_name = record_fiber_column_names[index]
                assert not pd.isna(
                    row[record_fiber_column_name]
                ), f"Record fiber missing for subject {subject_id} on date {row[date_column_name]}"
                record_fiber = int(row[record_fiber_column_name])
                metadata["record_fibers"].append(record_fiber)
    return subject_id_to_metadata


def get_session_to_nwb_kwargs_per_session(
    *,
    data_dir_path: DirectoryPath,
    setup: Literal["Bing", "WS8", "MollyFP"],
    metadata_subfolder_name: Literal["opto-signal sum", "opto-behavioral sum"],
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
    metadata_subfolder_path = metadata_folder_path / metadata_subfolder_name
    sheet_name_to_subject_id_to_metadata = collect_excel_metadata(metadata_folder_path=metadata_subfolder_path)

    session_to_nwb_kwargs_per_session = []
    setup_folder_name = f"Setup - {setup}"
    setup_folder = data_dir_path / setup_folder_name
    tdt_folders = find_tdt_folders(root_folder=setup_folder)

    for sheet_name, subject_id_to_metadata in sheet_name_to_subject_id_to_metadata.items():
        for subject_id, metadata in subject_id_to_metadata.items():
            for index, session_date in enumerate(metadata["session_dates"]):
                session_setup = metadata["session_setups"][index]
                if "record_fibers" in metadata:
                    record_fiber = metadata["record_fibers"][index]
                else:
                    record_fiber = None
                if session_setup != setup:
                    continue

                outer_session_folder_name = f"{subject_id}-{session_date.strftime('%y%m%d')}"
                matched = False
                for tdt_folder in tdt_folders:
                    if subject_id in tdt_folder.name and session_date.strftime("%y%m%d") in tdt_folder.name:
                        matched = True
                        session_folder = next(p for p in tdt_folder.iterdir())
                        inner_session_folder = next(p for p in session_folder.iterdir())

                        info_file_path = inner_session_folder / "Info.mat"
                        tdt_fp_folder_path = inner_session_folder
                        tdt_ephys_folder_path = session_folder
                        sex = metadata["sex"]
                        dob = metadata["dob"]
                        optogenetic_site_name = metadata["optogenetic_site_name"]
                        optogenetic_virus_volume_in_uL = metadata["optogenetic_virus_volume_in_uL"]
                        fiber_photometry_site_name = metadata.get("fiber_photometry_site_name", None)
                        fiber_photometry_virus_volume_in_uL = metadata.get("fiber_photometry_virus_volume_in_uL", None)

                        # Handle double-subject sessions
                        is_double_subject = len(tdt_folder.name.split("-")[0].split("_")) > 1
                        if is_double_subject:
                            if subject_id == tdt_folder.name.split("-")[0].split("_")[0]:
                                subject_number = 1
                            else:
                                subject_number = 2
                        else:
                            subject_number = 1
                        cam_number = subject_number
                        stream_number = subject_number
                        video_file_path = next(inner_session_folder.glob(f"*Cam{cam_number}.avi"))
                        stream_name = f"LFP{stream_number}"
                        if record_fiber is None:
                            record_fiber = subject_number

                        session_to_nwb_kwargs = dict(
                            info_file_path=info_file_path,
                            video_file_path=video_file_path,
                            tdt_fp_folder_path=tdt_fp_folder_path,
                            tdt_ephys_folder_path=tdt_ephys_folder_path,
                            subject_id=subject_id,
                            sex=sex,
                            dob=dob,
                            optogenetic_site_name=optogenetic_site_name,
                            fiber_photometry_site_name=fiber_photometry_site_name,
                            stream_name=stream_name,
                            record_fiber=record_fiber,
                            optogenetic_virus_volume_in_uL=optogenetic_virus_volume_in_uL,
                            fiber_photometry_virus_volume_in_uL=fiber_photometry_virus_volume_in_uL,
                        )
                        session_to_nwb_kwargs_per_session.append(session_to_nwb_kwargs)
                if not matched:
                    raise ValueError(
                        f"No matching TDT folder found for {outer_session_folder_name} in sheet {sheet_name}"
                    )

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
