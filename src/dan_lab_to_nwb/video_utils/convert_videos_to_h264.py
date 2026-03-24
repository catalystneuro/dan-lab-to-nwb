#!/usr/bin/env python3
"""Pre-convert AVI videos to H.264 MP4 for NWB browser compatibility.

NWB visualization widgets use the HTML5 <video> element, which only supports
browser-native codecs (H.264, VP8/VP9, AV1). This script re-encodes all .avi
files to H.264 .mp4 so they render correctly in NWB widgets.

Usage:
    python convert_videos_to_h264.py <data_dir> [<data_dir2> ...] [--dry-run] [--delete-originals]

Arguments:
    <data_dir>           One or more directories to scan recursively for .avi files

Options:
    --dry-run            Show what would be converted without running ffmpeg
    --delete-originals   Delete the original .avi file after successful conversion

Examples:
    python convert_videos_to_h264.py "/Volumes/T7/CatalystNeuro/Dan/Test - video analysis"
    python convert_videos_to_h264.py "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets" \\
                                     "/Volumes/T7/CatalystNeuro/Dan/Test - video analysis" \\
                                     --delete-originals
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = "convert_videos_h264.log"

# Enable ANSI color codes on Windows 10+
if os.name == "nt":
    os.system("")

GREEN = "\033[0;32m" if sys.stdout.isatty() else ""
YELLOW = "\033[1;33m" if sys.stdout.isatty() else ""
RED = "\033[0;31m" if sys.stdout.isatty() else ""
NC = "\033[0m" if sys.stdout.isatty() else ""


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Pre-convert AVI videos to H.264 MP4 for NWB browser compatibility.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("data_dirs", nargs="+", metavar="data_dir", help="Directories to scan recursively for .avi files")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be converted without running ffmpeg")
    parser.add_argument("--delete-originals", action="store_true", help="Delete the original .avi file after successful conversion")
    return parser.parse_args()


def log(log_file_handle, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file_handle.write(f"[{timestamp}] {message}\n")
    log_file_handle.flush()


def convert_directory(data_dir, dry_run, delete_originals, log_file_handle, counters):
    if not data_dir.is_dir():
        return

    print(f"Scanning: {data_dir}")
    print()

    avi_files = sorted(f for f in data_dir.rglob("*.avi") if not f.name.startswith("._"))

    for avi_file in avi_files:
        mp4_file = avi_file.with_suffix(".mp4")

        print(f"  File: {avi_file.name}")

        if mp4_file.exists():
            print(f"  {YELLOW}→ Skipping (already converted){NC}")
            log(log_file_handle, f"SKIPPED: {avi_file}")
            counters["skipped"] += 1
            print()
            continue

        if dry_run:
            print(f"  {YELLOW}→ [DRY RUN] Would convert to: {mp4_file.name}{NC}")
            if delete_originals:
                print(f"  {YELLOW}→ [DRY RUN] Would delete: {avi_file.name}{NC}")
            log(log_file_handle, f"DRY-RUN: {avi_file}")
            counters["converted"] += 1
        else:
            print("  → Converting...")
            result = subprocess.run(
                [
                    "ffmpeg", "-nostdin",
                    "-i", str(avi_file),
                    "-c:v", "libx264",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-preset", "fast",
                    "-c:a", "copy",
                    str(mp4_file),
                    "-loglevel", "warning",
                ],
                stdin=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                print(f"  {GREEN}✓ Done: {mp4_file.name}{NC}")
                log(log_file_handle, f"SUCCESS: {avi_file}")
                counters["converted"] += 1
                if delete_originals:
                    avi_file.unlink()
                    print(f"  {GREEN}✓ Deleted original: {avi_file.name}{NC}")
                    log(log_file_handle, f"DELETED: {avi_file}")
                    counters["deleted"] += 1
            else:
                print(f"  {RED}✗ Failed{NC}")
                log(log_file_handle, f"FAILED: {avi_file}")
                if mp4_file.exists():
                    mp4_file.unlink()
                counters["failed"] += 1

        print()


def main():
    arguments = parse_arguments()
    dry_run = arguments.dry_run
    delete_originals = arguments.delete_originals
    data_dirs = [Path(directory) for directory in arguments.data_dirs]

    print("============================================")
    print("  AVI → H.264 MP4 Conversion Script")
    print("============================================")
    if dry_run:
        print(f"{YELLOW}  [DRY RUN MODE - No files will be converted]{NC}")
    if delete_originals:
        print(f"{YELLOW}  [DELETE ORIGINALS - .avi files will be removed after conversion]{NC}")
    print()

    if shutil.which("ffmpeg") is None:
        print(f"{RED}Error: ffmpeg is not installed{NC}")
        print("Please install ffmpeg:")
        print("  macOS:   brew install ffmpeg")
        print("  Windows: winget install ffmpeg  (or: choco install ffmpeg)")
        sys.exit(1)
    print(f"{GREEN}✓ ffmpeg found{NC}")
    print()

    for directory in data_dirs:
        if not directory.is_dir():
            print(f"{YELLOW}Warning: Directory not found, skipping: {directory}{NC}")
    print()

    counters = {"converted": 0, "skipped": 0, "failed": 0, "deleted": 0}

    with open(LOG_FILE, "w") as log_file_handle:
        if dry_run:
            log_file_handle.write(f"Dry run started at {datetime.now()}\n")
        else:
            log_file_handle.write(f"Conversion started at {datetime.now()}\n")
        if delete_originals:
            log_file_handle.write("Mode: delete originals after conversion\n")

        for directory in data_dirs:
            convert_directory(directory, dry_run, delete_originals, log_file_handle, counters)

        print("============================================")
        print("  Conversion Summary")
        if dry_run:
            print("  (DRY RUN - No files converted)")
        print("============================================")

        if dry_run:
            print(f"{YELLOW}Would convert:      {counters['converted']}{NC}")
            if delete_originals:
                print(f"{YELLOW}Would delete:       {counters['converted']}{NC}")
        else:
            print(f"{GREEN}Converted:          {counters['converted']}{NC}")
            if delete_originals:
                print(f"{GREEN}Originals deleted:  {counters['deleted']}{NC}")

        print(f"{YELLOW}Skipped (existed):  {counters['skipped']}{NC}")
        if not dry_run:
            print(f"{RED}Failed:             {counters['failed']}{NC}")

        print()
        print(f"Log file: {LOG_FILE}")
        print("============================================")

        log_file_handle.write("----------------------------------------\n")
        if dry_run:
            log_file_handle.write(f"Dry run completed at {datetime.now()}\n")
            log_file_handle.write(f"Summary: {counters['converted']} would convert, {counters['skipped']} skipped\n")
        else:
            log_file_handle.write(f"Conversion completed at {datetime.now()}\n")
            log_file_handle.write(
                f"Summary: {counters['converted']} converted, {counters['skipped']} skipped, "
                f"{counters['failed']} failed, {counters['deleted']} originals deleted\n"
            )

    if counters["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
