from pathlib import Path

from pydantic import FilePath


def find_tdt_folders(root_folder: Path, max_depth: int = 10) -> list[Path]:
    """
    Recursively find all folders containing TDT data (identified by .tsq files).

    Searches through nested directory structure to find folders that contain
    .tsq files at any depth. If a folder with .tsq files is found to be part
    of an already Neo-compatible structure, returns the top-level folder instead.
    Once a folder with .tsq files is found, does not search its subdirectories
    (assumes TDT data is at leaf level).

    Parameters
    ----------
    root_folder : Path
        Starting directory to search
    max_depth : int, default: 10
        Maximum recursion depth to prevent infinite loops

    Returns
    -------
    list[Path]
        List of paths to folders containing .tsq files (or their top-level
        Neo-compatible folders if already organized)
    """
    tdt_folders = []
    seen_folders = set()  # Track folders we've already added

    def search(folder: Path, depth: int = 0):
        if depth > max_depth:
            return

        try:
            # Check if this folder contains TDT data (.tsq files)
            has_tsq_files = any(folder.glob("*.tsq"))

            if has_tsq_files:
                # Determine which folder to add
                if is_innermost_of_neo_structure(folder):
                    # Return the top-level folder (grandparent) instead
                    folder_to_add = folder.parent.parent
                else:
                    # Regular unorganized TDT folder
                    folder_to_add = folder

                # Only add if we haven't seen this folder before
                folder_path_str = str(folder_to_add.resolve())
                if folder_path_str not in seen_folders:
                    tdt_folders.append(folder_to_add)
                    seen_folders.add(folder_path_str)

                # Stop searching subdirectories - TDT data is here
                return

            # No TDT data here, search subdirectories
            for item in folder.iterdir():
                if item.is_dir() and not item.name.startswith("._"):
                    search(item, depth + 1)

        except (PermissionError, OSError) as e:
            print(f"Warning: Could not access {folder}: {e}")

    search(root_folder)
    return tdt_folders


def extract_session_name(tsq_file_path: Path, tdt_folder_name: str) -> str:
    """
    Extract the session name from a TDT .tsq filename.

    TDT filenames follow the pattern: {session_name}_{subject_folder_name}.tsq
    For example:
        Filename: "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451_M296-241018-072001.tsq"
        Folder:   "M296-241018-072001"
        Returns:  "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451"

    Parameters
    ----------
    tsq_file_path : Path
        Path to the .tsq file
    tdt_folder_name : str
        Name of the folder containing the TDT data

    Returns
    -------
    str
        The extracted session name, or empty string if extraction fails
    """
    filename_stem = tsq_file_path.stem

    # Remove the folder name from the end of the filename
    session_name = filename_stem.replace(f"_{tdt_folder_name}", "").replace(tdt_folder_name, "").strip("_")

    return session_name


def is_innermost_of_neo_structure(folder: Path) -> bool:
    """
    Check if a folder is the innermost part of an already Neo-compatible structure.

    A folder is considered innermost of Neo structure if:
    - It contains .tsq files
    - Its parent is a session folder
    - Its grandparent has the same name as the folder itself

    Example structure this detects:
        M296-241018-072001/              ← grandparent (same name as folder)
            Lindsay_SBO.../              ← parent (session folder)
                M296-241018-072001/      ← folder (contains .tsq files)

    Parameters
    ----------
    folder : Path
        The folder to check

    Returns
    -------
    bool
        True if folder is innermost part of Neo structure, False otherwise
    """
    try:
        # Check if this folder has a grandparent
        if folder.parent is None or folder.parent.parent is None:
            return False

        # Check if grandparent exists and has same name as this folder
        grandparent = folder.parent.parent
        if not grandparent.exists():
            return False

        # Key check: grandparent name should match this folder's name
        if grandparent.name == folder.name:
            return True

        return False

    except (OSError, AttributeError):
        return False


def is_neo_compatible(tdt_folder: Path) -> bool:
    """
    Check if a TDT folder is already organized for Neo data reader compatibility.

    A Neo-compatible folder structure looks like:
        M296-241018-072001/
            Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451/
                M296-241018-072001/  ← actual TDT data here

    Parameters
    ----------
    tdt_folder : Path
        The folder to check

    Returns
    -------
    bool
        True if already Neo-compatible, False otherwise
    """
    # Get non-hidden subdirectories
    subdirs = [d for d in tdt_folder.iterdir() if d.is_dir() and not d.name.startswith("._")]

    # Should have exactly one subdirectory (the session folder)
    if len(subdirs) != 1:
        return False

    session_folder = subdirs[0]
    nested_dirs = [d for d in session_folder.iterdir() if d.is_dir() and not d.name.startswith("._")]

    # That session folder should contain exactly one folder with same name as parent
    if len(nested_dirs) == 1 and nested_dirs[0].name == tdt_folder.name:
        return True

    return False


def make_neo_compatible(tdt_folder: Path, parent_folder: Path):
    """
    Reorganize a TDT folder to be compatible with the Neo data reader.

    Transforms:
        M296-241018-072001/ ← TDT data directly here
    Into:
        M296-241018-072001/
            Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451/ ← session name from .tsq
                M296-241018-072001/ ← TDT data moved here

    Parameters
    ----------
    tdt_folder : Path
        The folder containing TDT data files
    parent_folder : Path
        The parent folder (used for temporary rename location)
    """
    # Skip Mac system files
    if tdt_folder.name.startswith("._"):
        return

    # Special case for BBB8
    if "BBB8" in tdt_folder.name:
        print(f"Applying BBB8 special case - renaming folder to M008")
        new_folder_name = tdt_folder.name.replace("BBB8", "M008")
        new_folder_path = tdt_folder.parent / new_folder_name
        tdt_folder.rename(new_folder_path)
        tdt_folder = new_folder_path

    # Special case for M008: Rename files containing BBB8 to M008
    if "M008" in tdt_folder.name:
        print(f"Applying M008 special case - renaming BBB8 files to M008")
        for file_path in tdt_folder.glob("*BBB8*"):
            if file_path.is_file():
                new_name = file_path.name.replace("BBB8", "M008")
                new_path = file_path.parent / new_name
                file_path.rename(new_path)
                print(f"  Renamed: {file_path.name} → {new_name}")

    # Special case for M363_M367-250724-193627(0725): Remove parenthetical suffix
    if "(0725)" in tdt_folder.name:
        print(f"Applying (0725) special case - removing parenthetical suffix")
        new_folder_name = tdt_folder.name.replace("(0725)", "")
        new_folder_path = tdt_folder.parent / new_folder_name
        tdt_folder.rename(new_folder_path)
        tdt_folder = new_folder_path

    # Special case for M376_M501-251001-071000: Rename files containing M374_M501 to M376_M501
    if tdt_folder.name == "M376_M501-251001-071000":
        print(f"Applying M376_M501 special case - renaming M374_M501 files to M376_M501")
        for file_path in tdt_folder.glob("*M374_M501*"):
            if file_path.is_file():
                new_name = file_path.name.replace("M374_M501", "M376_M501")
                new_path = file_path.parent / new_name
                file_path.rename(new_path)
                print(f"  Renamed: {file_path.name} → {new_name}")

    # Check if already organized
    if is_neo_compatible(tdt_folder):
        print(f"Skipping {tdt_folder.name} - already Neo-compatible")
        return

    # Find .tsq file to extract session name (exclude Mac hidden files)
    tsq_files = [f for f in tdt_folder.glob("*.tsq") if not f.name.startswith("._")]

    if len(tsq_files) == 0:
        print(f"Warning: No .tsq files found in {tdt_folder.name}")
        return

    if len(tsq_files) > 1:
        print(f"Warning: Multiple .tsq files found in {tdt_folder.name}, using first one")

    # Extract session name
    tsq_file = tsq_files[0]
    session_name = extract_session_name(tsq_file, tdt_folder.name)

    if not session_name:
        print(f"Error: Could not extract session name from {tsq_file.name}")
        return

    print(f"Making {tdt_folder.name} Neo-compatible with session '{session_name}'")

    try:
        # Step 1: Move folder to temporary location
        temp_path = tdt_folder.rename(parent_folder / f"temp_{tdt_folder.name}")

        # Step 2: Create new nested structure
        tdt_folder.mkdir()
        session_folder = tdt_folder / session_name
        session_folder.mkdir()

        # Step 3: Move data into final nested location
        temp_path.rename(session_folder / tdt_folder.name)

        print(f"  ✓ Successfully made {tdt_folder.name} Neo-compatible")

    except Exception as e:
        print(f"  ✗ Error making {tdt_folder.name} Neo-compatible: {e}")

        # Attempt to restore original state
        temp_folder_path = parent_folder / f"temp_{tdt_folder.name}"
        if temp_folder_path.exists():
            try:
                temp_folder_path.rename(tdt_folder)
                print(f"  → Restored {tdt_folder.name} to original state")
            except Exception as restore_error:
                print(f"  → Failed to restore: {restore_error}")


def reorganize_data(data_dir_path: FilePath):
    """
    Reorganize TDT data folders to be compatible with the Neo data reader.

    Searches through setup folders for TDT data at any depth and reorganizes
    each folder to match the structure expected by the Neo TDT data reader:
        subject_folder/session_name/subject_folder/

    Parameters
    ----------
    data_dir_path : FilePath
        Path to root directory containing setup folders
    """
    data_dir_path = Path(data_dir_path)

    setup_folders = ["Setup - Bing", "Setup - WS8", "Setup - MollyFP"]

    for setup_name in setup_folders:
        setup_folder = data_dir_path / setup_name

        if not setup_folder.exists():
            print(f"Setup folder '{setup_name}' not found, skipping...")
            continue

        print(f"\n{'='*60}")
        print(f"Processing {setup_name}")
        print(f"{'='*60}")

        # Find all TDT folders at any depth
        tdt_folders = find_tdt_folders(setup_folder)
        print(f"Found {len(tdt_folders)} TDT folders\n")

        # Make each folder Neo-compatible
        for tdt_folder in tdt_folders:
            # Parent folder is where we'll temporarily move the folder during reorganization
            parent_folder = tdt_folder.parent
            make_neo_compatible(tdt_folder, parent_folder)


def main():
    data_dir_path = "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets"
    reorganize_data(data_dir_path)


if __name__ == "__main__":
    main()
