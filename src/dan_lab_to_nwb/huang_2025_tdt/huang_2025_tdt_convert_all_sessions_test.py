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
    sessions_to_skip = [
        "M405_M407-250412-081001(done)",
        "M404_M409-250406-141501(done)",
        "M404_M409-250405-151801(done)",
        "M405_M407-250412-142001(done)",
        "M404-M409-250406-153701 (M404 bad signal, done)",
        "M405_M407-250413-081001(done)",
        "M405_M407-250413-152101(done)",
        "M409_M404-250407-153704 (done)",
        "M405_M407-250414-081001(done)",
    ]

    data_dir_path = Path(data_dir_path)
    session_to_nwb_kwargs_per_session = []
    dataset_folder_names = [
        "Bing-202504",
        "WS8-202504",
        "ExampleSessions",
    ]
    for folder_name in dataset_folder_names:
        dataset_folder = data_dir_path / folder_name
        for outer_session_folder in dataset_folder.iterdir():
            if not outer_session_folder.is_dir():
                continue
            if outer_session_folder.name in sessions_to_skip:
                continue
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
                    )
                    session_to_nwb_kwargs_per_session.append(session_to_nwb_kwargs)

    return session_to_nwb_kwargs_per_session


if __name__ == "__main__":

    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/Test - TDT data")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb/huang_2025_tdt")
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
