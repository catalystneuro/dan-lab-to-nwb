"""Validation script to compare paths in data.json against metadata CSV files."""
import datetime
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

import pandas as pd


def load_data_json(data_json_path: Path) -> List[Dict]:
    """Load and parse data.json file.

    Parameters
    ----------
    data_json_path : Path
        Path to data.json file

    Returns
    -------
    List[Dict]
        List of all entries from data.json
    """
    with open(data_json_path, "r") as f:
        data = json.load(f)
    return data


def parse_session_path(path: str) -> Optional[Dict]:
    """Extract session information from a path string.

    Parameters
    ----------
    path : str
        Path string like "Setup - Bing/Bing-202412/M412-250717-153001/..."
        or nested pattern "Setup - WS8/202404/202409/M296-240915-072001"

    Returns
    -------
    Optional[Dict]
        Dictionary with parsed information or None if not a session path
        Keys: 'mouse_id', 'date', 'setup', 'full_path', 'session_name'
    """
    # Try nested month pattern first: Setup - [SetupName]/[YYYYMM]/[YYYYMM]/[MouseID]-YYMMDD-HHMMSS
    nested_pattern = r"^(Setup - ([^/]+))/(\d{6})/(\d{6})/(([^-]+)-(\d{6})-\d+)"
    nested_match = re.match(nested_pattern, path)

    if nested_match:
        setup_prefix = nested_match.group(1)  # "Setup - WS8"
        setup_name = nested_match.group(2)  # "WS8"
        outer_month_folder = nested_match.group(3)  # "202404"
        inner_month_folder = nested_match.group(4)  # "202409"
        session_name = nested_match.group(5)  # "M296-240915-072001"
        mouse_id_raw = nested_match.group(6)  # "M296"
        date_str = nested_match.group(7)  # "240915"
    else:
        # Standard pattern: Setup - [SetupName]/[SetupName-YYYYMM]/[MouseID]-YYMMDD-HHMMSS
        standard_pattern = r"^(Setup - ([^/]+))/[^/]+-(\d{6})/(([^-]+)-(\d{6})-\d+)"
        standard_match = re.match(standard_pattern, path)

        if not standard_match:
            return None

        setup_prefix = standard_match.group(1)  # "Setup - Bing"
        setup_name = standard_match.group(2)  # "Bing"
        month_folder = standard_match.group(3)  # "202412"
        session_name = standard_match.group(4)  # "M412-250717-153001"
        mouse_id_raw = standard_match.group(5)  # "M412" or "M412_PN"
        date_str = standard_match.group(6)  # "250717"

    # Extract primary mouse ID (handle M412_PN -> M412)
    mouse_id = mouse_id_raw.split("_")[0]
    if mouse_id.endswith("R") or mouse_id.endswith("L"):
        mouse_id = mouse_id[:-1]  # ex. M267R --> M267, M267L --> M267
    if mouse_id.startswith("BBB"):
        mouse_id = mouse_id.replace("BBB", "M00")  # ex. BBB8 --> M008

    # Try alternative parsing for subject_id
    parts = mouse_id_raw.split("_")
    if len(parts) > 1:
        alt_mouse_id = parts[1]  # ex. M342_M042 --> M042
        if alt_mouse_id.endswith("R") or alt_mouse_id.endswith("L"):
            alt_mouse_id = alt_mouse_id[:-1]  # ex. M267R --> M267, M267L --> M267
        if alt_mouse_id.startswith("BBB"):
            alt_mouse_id = alt_mouse_id.replace("BBB", "M00")  # ex. BBB8 --> M008
    else:
        # No alternative ID, use the same as primary
        alt_mouse_id = mouse_id

    # Parse date
    try:
        pst = ZoneInfo("US/Pacific")
        date = datetime.datetime.strptime(date_str, "%y%m%d").replace(tzinfo=pst)
    except ValueError:
        return None

    return {
        "mouse_id": mouse_id,
        "alt_mouse_id": alt_mouse_id,
        "date": date,
        "setup": setup_name,
        "full_path": path,
        "session_name": session_name,
    }


def load_metadata_csvs(metadata_folder_path: Path) -> Dict:
    """Load metadata from CSV files.

    Parameters
    ----------
    metadata_folder_path : Path
        Path to metadata folder containing subdirectories with CSV files

    Returns
    -------
    Dict
        Dictionary mapping mouse_id to metadata including dates and setups
        Format: {mouse_id: {'dates': [...], 'setups': [...], 'csv_files': [...], 'sex': str, 'dob': datetime}}
    """
    pst = ZoneInfo("US/Pacific")
    subject_id_to_metadata = {}

    # Search in both metadata subfolders
    metadata_sub_folder_names = ["behavioral sum", "signal sum", "opto-behavioral sum", "opto-signal sum"]

    for sub_folder_name in metadata_sub_folder_names:
        metadata_sub_folder_path = metadata_folder_path / sub_folder_name

        if not metadata_sub_folder_path.exists():
            continue

        for csv_file in metadata_sub_folder_path.glob("*.csv"):
            if csv_file.name.startswith("._"):
                continue

            df = pd.read_csv(csv_file)
            date_column_names = [name for name in df.columns if name.startswith("date")]
            setup_column_names = [name for name in df.columns if name.startswith("setup")]

            for _, row in df.iterrows():
                subject_id = row["mouse ID"]

                if subject_id not in subject_id_to_metadata:
                    subject_id_to_metadata[subject_id] = {
                        "dates": [],
                        "setups": [],
                        "csv_files": [],
                        "sex": None,
                        "dob": None,
                    }

                metadata = subject_id_to_metadata[subject_id]
                metadata["sex"] = "M" if row["M"] == 1 else "F"
                metadata["dob"] = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)

                # Collect all session dates and setups
                for date_column_name, setup_column_name in zip(date_column_names, setup_column_names):
                    if pd.isna(row[date_column_name]) or pd.isna(row[setup_column_name]):
                        continue

                    session_date = datetime.datetime.strptime(row[date_column_name], "%m/%d/%Y").replace(tzinfo=pst)
                    session_setup = row[setup_column_name]

                    # Store date-setup-csv_file tuples
                    if session_date not in metadata["dates"]:
                        metadata["dates"].append(session_date)
                        metadata["setups"].append(session_setup)
                        metadata["csv_files"].append(csv_file.name)

    return subject_id_to_metadata


def validate_sessions(data_entries: List[Dict], metadata: Dict) -> Dict:
    """Validate all session paths against metadata.

    Parameters
    ----------
    data_entries : List[Dict]
        List of entries from data.json
    metadata : Dict
        Metadata dictionary from load_metadata_csvs

    Returns
    -------
    Dict
        Dictionary with categorized sessions:
        {
            'valid': [...],
            'extra': [...],
            'all_sessions': [...]
        }
    """
    valid_sessions = []
    extra_sessions = []
    all_sessions = []

    for entry in data_entries:
        path = entry.get("Path", "")

        # Parse session information
        session_info = parse_session_path(path)

        if session_info is None:
            continue

        all_sessions.append(session_info)

        mouse_id = session_info["mouse_id"]
        alt_mouse_id = session_info["alt_mouse_id"]
        date = session_info["date"]
        setup = session_info["setup"]

        # Check if mouse exists in metadata (try primary ID first, then alternative)
        if mouse_id not in metadata:
            # Try alternative mouse ID
            if alt_mouse_id not in metadata:
                extra_sessions.append({**session_info, "reason": "Mouse ID not in metadata"})
                continue
            else:
                # Use alternative mouse ID
                mouse_id = alt_mouse_id

        # Check if date exists for this mouse
        mouse_metadata = metadata[mouse_id]
        if date not in mouse_metadata["dates"]:
            extra_sessions.append({**session_info, "reason": "Date not in metadata"})
            continue

        # Check if setup matches for this date
        date_index = mouse_metadata["dates"].index(date)
        expected_setup = mouse_metadata["setups"][date_index]

        if setup != expected_setup:
            extra_sessions.append(
                {**session_info, "reason": f"Setup mismatch (expected: {expected_setup}, found: {setup})"}
            )
            continue

        # Session is valid - update mouse_id to the matched one
        session_info_copy = session_info.copy()
        session_info_copy["mouse_id"] = mouse_id
        valid_sessions.append(session_info_copy)

    return {"valid": valid_sessions, "extra": extra_sessions, "all_sessions": all_sessions}


def find_missing_sessions(metadata: Dict, found_sessions: List[Dict]) -> List[Dict]:
    """Find sessions that are in metadata but missing from data.json.

    Parameters
    ----------
    metadata : Dict
        Metadata dictionary from load_metadata_csvs
    found_sessions : List[Dict]
        List of all parsed sessions from data.json

    Returns
    -------
    List[Dict]
        List of missing sessions with mouse_id, date, setup, and csv_file
    """
    # Create a set of (mouse_id, date, setup) tuples for quick lookup
    # Include both primary and alternative mouse IDs
    found_set = set()
    for session in found_sessions:
        found_set.add((session["mouse_id"], session["date"], session["setup"]))
        found_set.add((session["alt_mouse_id"], session["date"], session["setup"]))

    missing_sessions = []

    for mouse_id, mouse_metadata in metadata.items():
        for date, setup, csv_file in zip(
            mouse_metadata["dates"], mouse_metadata["setups"], mouse_metadata["csv_files"]
        ):
            if (mouse_id, date, setup) not in found_set:
                missing_sessions.append(
                    {"mouse_id": mouse_id, "date": date.strftime("%Y-%m-%d"), "setup": setup, "csv_file": csv_file}
                )

    return missing_sessions


def generate_report(validation_results: Dict, missing_sessions: List[Dict], output_path: Path):
    """Generate validation report and save to JSON file.

    Parameters
    ----------
    validation_results : Dict
        Results from validate_sessions
    missing_sessions : List[Dict]
        Results from find_missing_sessions
    output_path : Path
        Path to save the output JSON file
    """
    # Sort sessions by mouse_id and date for better organization
    sorted_valid = sorted(validation_results["valid"], key=lambda s: (s["mouse_id"], s["date"]))

    # Prepare data for JSON serialization
    valid_sessions_list = [s["full_path"] for s in sorted_valid]

    sorted_extra = sorted(validation_results["extra"], key=lambda s: (s["mouse_id"], s["date"]))
    extra_sessions_list = [
        {
            "path": s["full_path"],
            "mouse_id": s["mouse_id"],
            "alt_mouse_id": s["alt_mouse_id"],
            "date": s["date"].strftime("%Y-%m-%d"),
            "setup": s["setup"],
            "reason": s["reason"],
        }
        for s in sorted_extra
    ]

    # Sort missing sessions
    sorted_missing = sorted(missing_sessions, key=lambda s: (s["mouse_id"], s["date"]))

    # Create concise lists for quick scanning
    extra_sessions_concise = [s["path"] for s in extra_sessions_list]
    missing_sessions_concise = [f"{s['mouse_id']} - {s['date']} - {s['setup']}" for s in sorted_missing]

    report = {
        "summary": {
            "total_session_paths": len(validation_results["all_sessions"]),
            "valid": len(validation_results["valid"]),
            "extra": len(validation_results["extra"]),
            "missing": len(sorted_missing),
        },
        "valid_sessions": valid_sessions_list,
        "extra_sessions_concise": extra_sessions_concise,
        "missing_sessions_concise": missing_sessions_concise,
        "missing_sessions": sorted_missing,
        "extra_sessions": extra_sessions_list,
    }

    # Save to file
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("PATH VALIDATION REPORT")
    print("=" * 60)
    print(f"\nTotal session paths found in data.json: {report['summary']['total_session_paths']}")
    print(f"\nValid sessions (in both metadata and data.json): {report['summary']['valid']}")
    print(f"Extra sessions (in data.json but not in metadata): {report['summary']['extra']}")
    print(f"Missing sessions (in metadata but not in data.json): {report['summary']['missing']}")

    if report["summary"]["extra"] > 0:
        print("\n--- Sample Extra Sessions ---")
        for session in extra_sessions_list[:5]:
            print(f"  - {session['path']}")
            print(f"    Reason: {session['reason']}")

    if report["summary"]["missing"] > 0:
        print("\n--- Sample Missing Sessions ---")
        for session in sorted_missing[:5]:
            print(f"  - Mouse: {session['mouse_id']}, Date: {session['date']}, Setup: {session['setup']}")

    print(f"\nFull report saved to: {output_path}")
    print("=" * 60 + "\n")


def main():
    """Main execution function."""
    # Define paths
    project_root = Path(__file__).parent
    data_json_path = project_root / "data.json"
    metadata_folder_path = Path("/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/metadata")
    output_path = project_root / "validation_report.json"

    # Check if data.json exists
    if not data_json_path.exists():
        print(f"Error: data.json not found at {data_json_path}")
        return

    # Check if metadata folder exists
    if not metadata_folder_path.exists():
        print(f"Error: Metadata folder not found at {metadata_folder_path}")
        print("Please update the metadata_folder_path in the script to the correct location.")
        return

    print("Loading data.json...")
    data_entries = load_data_json(data_json_path)

    print("Loading metadata CSVs...")
    metadata = load_metadata_csvs(metadata_folder_path)
    print(f"Found metadata for {len(metadata)} mice")

    print("Validating sessions...")
    validation_results = validate_sessions(data_entries, metadata)

    print("Finding missing sessions...")
    missing_sessions = find_missing_sessions(metadata, validation_results["all_sessions"])

    print("Generating report...")
    generate_report(validation_results, missing_sessions, output_path)


if __name__ == "__main__":
    main()
