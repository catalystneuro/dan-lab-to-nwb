from pathlib import Path

from pydantic import FilePath


def reorganize_data(data_dir_path: FilePath):
    data_dir_path = Path(data_dir_path)
    dataset_folder_names = [
        "Bing-202504",
        "WS8-202504",
    ]
    for folder_name in dataset_folder_names:
        dataset_folder = data_dir_path / folder_name
        for sub_folder in dataset_folder.iterdir():
            if not sub_folder.is_dir():
                continue
            tsq_files = list(sub_folder.glob("*.tsq"))
            if len(tsq_files) == 0:
                print(f"No .tsq files were found in {sub_folder.name}, so it is assumed to be already organized.")
                continue
            tsq_file = tsq_files[0]
            session_name = tsq_file.name.split(sub_folder.name)[0].strip("_")

            temp_path = sub_folder.rename(dataset_folder / f"temp_{sub_folder.name}")
            sub_folder.mkdir()
            session_folder_path = sub_folder / session_name
            session_folder_path.mkdir()
            temp_path.rename(session_folder_path / sub_folder.name)

    # Special case for stand-alone example sessions
    example_session_dataset_folder = data_dir_path / "ExampleSessions"
    example_session_dataset_folder.mkdir(exist_ok=True)
    example_sessions = [
        "M301-240917-163001",
        "M301-241108-072001",
    ]
    for folder_name in example_sessions:
        folder_path = data_dir_path / folder_name
        if not folder_path.is_dir():
            continue

        tsq_file = list(folder_path.glob("*.tsq"))[0]
        session_name = tsq_file.name.split(folder_name)[0].strip("_")

        sub_folder = example_session_dataset_folder / folder_name
        sub_folder.mkdir(exist_ok=True)
        session_folder = sub_folder / session_name
        session_folder.mkdir(exist_ok=True)
        folder_path.rename(session_folder / folder_name)


def main():
    data_dir_path = "/Volumes/T7/CatalystNeuro/Dan/Test - TDT data"
    reorganize_data(data_dir_path)


if __name__ == "__main__":
    main()
