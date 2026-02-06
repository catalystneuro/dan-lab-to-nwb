"""
Script to undo the Neo-compatible folder reorganization done by reorganize_data.py.

This allows re-running reorganize_data.py to test special case fixes without
having to delete and re-download the original data.

Transforms:
    M296-241018-072001/
        Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451/
            M296-241018-072001/  ← TDT data here
Back to:
    M296-241018-072001/  ← TDT data directly here
"""

import shutil
from pathlib import Path

from pydantic import FilePath


def find_neo_compatible_folders(root_folder: Path, max_depth: int = 10) -> list[Path]:
    """
    Recursively find all folders that are already in Neo-compatible structure.

    A Neo-compatible folder structure looks like:
        M296-241018-072001/
            Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451/
                M296-241018-072001/  ← actual TDT data here

    Parameters
    ----------
    root_folder : Path
        Starting directory to search
    max_depth : int, default: 10
        Maximum recursion depth to prevent infinite loops

    Returns
    -------
    list[Path]
        List of paths to Neo-compatible top-level folders
    """
    neo_folders = []
    seen_folders = set()

    def search(folder: Path, depth: int = 0):
        if depth > max_depth:
            return

        try:
            # Skip hidden folders
            if folder.name.startswith("._"):
                return

            # Check if this folder is Neo-compatible
            if is_neo_compatible(folder):
                folder_path_str = str(folder.resolve())
                if folder_path_str not in seen_folders:
                    neo_folders.append(folder)
                    seen_folders.add(folder_path_str)
                # Don't search subdirectories - we found a Neo-compatible folder
                return

            # Search subdirectories
            for item in folder.iterdir():
                if item.is_dir() and not item.name.startswith("._"):
                    search(item, depth + 1)

        except (PermissionError, OSError) as e:
            print(f"Warning: Could not access {folder}: {e}")

    search(root_folder)
    return neo_folders


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
    try:
        subdirs = [d for d in tdt_folder.iterdir() if d.is_dir() and not d.name.startswith("._")]
    except (PermissionError, OSError):
        return False

    # Should have exactly one subdirectory (the session folder)
    if len(subdirs) != 1:
        return False

    session_folder = subdirs[0]
    try:
        nested_dirs = [d for d in session_folder.iterdir() if d.is_dir() and not d.name.startswith("._")]
    except (PermissionError, OSError):
        return False

    # That session folder should contain exactly one folder with same name as parent
    if len(nested_dirs) == 1 and nested_dirs[0].name == tdt_folder.name:
        return True

    return False


def unorganize_folder(tdt_folder: Path) -> bool:
    """
    Undo Neo-compatible organization for a single folder.

    Transforms:
        M296-241018-072001/
            Lindsay_SBO.../
                M296-241018-072001/  ← TDT data here
    Back to:
        M296-241018-072001/  ← TDT data directly here

    Parameters
    ----------
    tdt_folder : Path
        The Neo-compatible folder to unorganize

    Returns
    -------
    bool
        True if successful, False otherwise
    """
    try:
        # Get the session folder (only non-hidden subdirectory)
        subdirs = [d for d in tdt_folder.iterdir() if d.is_dir() and not d.name.startswith("._")]
        if len(subdirs) != 1:
            print(f"  Error: Expected 1 subdirectory, found {len(subdirs)}")
            return False

        session_folder = subdirs[0]
        session_name = session_folder.name

        # Get the nested data folder
        nested_dirs = [d for d in session_folder.iterdir() if d.is_dir() and not d.name.startswith("._")]
        if len(nested_dirs) != 1 or nested_dirs[0].name != tdt_folder.name:
            print(f"  Error: Unexpected nested structure")
            return False

        data_folder = nested_dirs[0]

        print(f"Unorganizing {tdt_folder.name}")
        print(f"  Session: {session_name}")

        # Move all files from data_folder to tdt_folder
        files_moved = 0
        for item in data_folder.iterdir():
            if item.name.startswith("._"):
                continue
            dest = tdt_folder / item.name
            if dest.exists():
                print(f"  Warning: {item.name} already exists in destination, skipping")
                continue
            shutil.move(str(item), str(dest))
            files_moved += 1

        print(f"  Moved {files_moved} items")

        # Remove empty nested directories
        try:
            data_folder.rmdir()
            session_folder.rmdir()
            print(f"  Removed empty directories")
        except OSError as e:
            print(f"  Warning: Could not remove empty directories: {e}")

        print(f"  ✓ Successfully unorganized {tdt_folder.name}")
        return True

    except Exception as e:
        print(f"  ✗ Error unorganizing {tdt_folder.name}: {e}")
        return False


def unorganize_data(data_dir_path: FilePath):
    """
    Undo Neo-compatible organization for all TDT folders in the data directory.

    Parameters
    ----------
    data_dir_path : FilePath
        Path to root directory containing setup folders
    """
    data_dir_path = Path(data_dir_path)

    setup_folders = ["Setup - Bing", "Setup - WS8", "Setup - MollyFP"]

    total_found = 0
    total_unorganized = 0

    for setup_name in setup_folders:
        setup_folder = data_dir_path / setup_name

        if not setup_folder.exists():
            print(f"Setup folder '{setup_name}' not found, skipping...")
            continue

        print(f"\n{'='*60}")
        print(f"Processing {setup_name}")
        print(f"{'='*60}")

        # Find all Neo-compatible folders
        neo_folders = find_neo_compatible_folders(setup_folder)
        print(f"Found {len(neo_folders)} Neo-compatible folders\n")
        total_found += len(neo_folders)

        # Unorganize each folder
        for folder in neo_folders:
            if unorganize_folder(folder):
                total_unorganized += 1
            print()

    print(f"\n{'='*60}")
    print(f"Summary: Unorganized {total_unorganized}/{total_found} folders")
    print(f"{'='*60}")


def main():
    data_dir_path = "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets"
    unorganize_data(data_dir_path)


if __name__ == "__main__":
    main()
