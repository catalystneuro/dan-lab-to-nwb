"""Primary script to run to convert all sessions in a dataset using session_to_nwb."""
import shutil
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Union

from pydantic import DirectoryPath
from pymatreader import read_mat
from tqdm import tqdm

from dan_lab_to_nwb.huang_2025_001711.huang_2025_dlc_convert_session import (
    session_to_nwb,
)


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
    subject_id = info["Subject"]
    nwbfile_name = f"sub-{subject_id}_ses-{session_id}.nwb"
    return nwbfile_name


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

    data_dir_path = Path(data_dir_path)
    session_to_nwb_kwargs_per_session = []
    for subject_folder in data_dir_path.iterdir():
        if not subject_folder.is_dir():
            continue
        behavioral_summary_file_path = subject_folder / f"{subject_folder.name}_beh_summary.csv"
        for session_folder in subject_folder.iterdir():
            if not session_folder.is_dir():
                continue
            check_FP_folder = session_folder / "check_FP"
            info_file_path = check_FP_folder / "Info.mat"
            video_file_path = next(session_folder.glob("*.avi"))
            dlc_file_path = next(session_folder.glob("*DLC*.h5"))
            labels_file_path = check_FP_folder / "labels.mat"
            eeg_file_path = check_FP_folder / "EEG.mat"
            emg_file_path = check_FP_folder / "EMG.mat"
            fs_file_path = check_FP_folder / "SampFreq.mat"
            session_to_nwb_kwargs = dict(
                info_file_path=info_file_path,
                video_file_path=video_file_path,
                dlc_file_path=dlc_file_path,
                labels_file_path=labels_file_path,
                behavioral_summary_file_path=behavioral_summary_file_path,
                eeg_file_path=eeg_file_path,
                emg_file_path=emg_file_path,
                fs_file_path=fs_file_path,
            )
            session_to_nwb_kwargs_per_session.append(session_to_nwb_kwargs)

    return session_to_nwb_kwargs_per_session


if __name__ == "__main__":

    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/Test - video analysis")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb/huang_2025_dlc")
    max_workers = 4
    verbose = False

    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)

    dataset_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        max_workers=max_workers,
        verbose=verbose,
    )
