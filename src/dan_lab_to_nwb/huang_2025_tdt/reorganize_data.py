from pathlib import Path

from pydantic import FilePath


def reorganize_data(data_dir_path: FilePath):
    data_dir_path = Path(data_dir_path)
    dataset_folder_names = ["Setup - Bing", "Setup - WS8", "Setup - MollyFP"]
    for folder_name in dataset_folder_names:
        dataset_folder = data_dir_path / folder_name
        for sub_folder in dataset_folder.iterdir():
            for sub_sub_folder in sub_folder.iterdir():
                if not sub_sub_folder.is_dir():
                    continue
                tsq_files = list(sub_sub_folder.glob("*.tsq"))
                if len(tsq_files) == 0:
                    print(
                        f"No .tsq files were found in {sub_sub_folder.name}, so it is assumed to be already organized."
                    )
                    continue
                tsq_file = tsq_files[0]
                if sub_sub_folder.name == "M364_M366-250808-072000x":
                    sub_sub_folder = sub_sub_folder.rename(sub_sub_folder.parent / "M364_M366-250808-072000")
                session_name = tsq_file.name.split(sub_sub_folder.name)[0].strip("_")

                temp_path = sub_sub_folder.rename(dataset_folder / f"temp_{sub_sub_folder.name}")
                sub_sub_folder.mkdir()
                session_folder_path = sub_sub_folder / session_name
                session_folder_path.mkdir()
                temp_path.rename(session_folder_path / sub_sub_folder.name)


def main():
    data_dir_path = "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets"
    reorganize_data(data_dir_path)


if __name__ == "__main__":
    main()
