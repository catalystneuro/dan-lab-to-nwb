#!/bin/bash

# Pre-convert AVI videos to H.264 MP4 for NWB browser compatibility.
# NWB visualization widgets use the HTML5 <video> element, which only supports
# browser-native codecs (H.264, VP8/VP9, AV1). This script re-encodes all .avi
# files to H.264 .mp4 so they render correctly in NWB widgets.
#
# Usage:
#   ./convert_videos_to_h264.sh <data_dir> [<data_dir2> ...] [--dry-run] [--delete-originals]
#
# Arguments:
#   <data_dir>           One or more directories to scan recursively for .avi files
#
# Options:
#   --dry-run            Show what would be converted without running ffmpeg
#   --delete-originals   Delete the original .avi file after successful conversion
#
# Examples:
#   ./convert_videos_to_h264.sh "/Volumes/T7/CatalystNeuro/Dan/Test - video analysis"
#   ./convert_videos_to_h264.sh "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets" \
#                               "/Volumes/T7/CatalystNeuro/Dan/Test - video analysis" \
#                               --delete-originals

LOG_FILE="convert_videos_h264.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Parse arguments: collect directories and flags separately
DRY_RUN=false
DELETE_ORIGINALS=false
DATA_DIRS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --delete-originals)
            DELETE_ORIGINALS=true
            shift
            ;;
        --*)
            echo "Unknown option: $1"
            echo "Usage: $0 <data_dir> [<data_dir2> ...] [--dry-run] [--delete-originals]"
            exit 1
            ;;
        *)
            DATA_DIRS+=("$1")
            shift
            ;;
    esac
done

if [ ${#DATA_DIRS[@]} -eq 0 ]; then
    echo "Error: at least one data directory is required."
    echo ""
    echo "Usage: $0 <data_dir> [<data_dir2> ...] [--dry-run] [--delete-originals]"
    echo ""
    echo "Examples:"
    echo "  $0 \"/Volumes/T7/CatalystNeuro/Dan/Test - video analysis\""
    echo "  $0 \"/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets\" \\"
    echo "     \"/Volumes/T7/CatalystNeuro/Dan/Test - video analysis\" --delete-originals"
    exit 1
fi

echo "============================================"
echo "  AVI → H.264 MP4 Conversion Script"
echo "============================================"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}  [DRY RUN MODE - No files will be converted]${NC}"
fi
if [ "$DELETE_ORIGINALS" = true ]; then
    echo -e "${YELLOW}  [DELETE ORIGINALS - .avi files will be removed after conversion]${NC}"
fi
echo ""

# Check dependencies
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg is not installed${NC}"
    echo "Please install ffmpeg: brew install ffmpeg (macOS)"
    exit 1
fi
echo -e "${GREEN}✓ ffmpeg found${NC}"
echo ""

# Check data directories exist
for dir in "${DATA_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}Warning: Directory not found, skipping: $dir${NC}"
    fi
done
echo ""

# Initialize counters
converted=0
skipped=0
failed=0
deleted=0

# Initialize log
if [ "$DRY_RUN" = true ]; then
    echo "Dry run started at $(date)" > "$LOG_FILE"
else
    echo "Conversion started at $(date)" > "$LOG_FILE"
fi
if [ "$DELETE_ORIGINALS" = true ]; then
    echo "Mode: delete originals after conversion" >> "$LOG_FILE"
fi

# Process a directory: find all .avi files (skip macOS resource forks) and convert
convert_directory() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        return
    fi

    echo "Scanning: $dir"
    echo ""

    while IFS= read -r -d $'\0' avi_file; do
        mp4_file="${avi_file%.avi}.mp4"

        echo "  File: $(basename "$avi_file")"

        # Skip if .mp4 already exists
        if [ -f "$mp4_file" ]; then
            echo -e "  ${YELLOW}→ Skipping (already converted)${NC}"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIPPED: $avi_file" >> "$LOG_FILE"
            skipped=$((skipped + 1))
            echo ""
            continue
        fi

        if [ "$DRY_RUN" = true ]; then
            echo -e "  ${YELLOW}→ [DRY RUN] Would convert to: $(basename "$mp4_file")${NC}"
            if [ "$DELETE_ORIGINALS" = true ]; then
                echo -e "  ${YELLOW}→ [DRY RUN] Would delete: $(basename "$avi_file")${NC}"
            fi
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] DRY-RUN: $avi_file" >> "$LOG_FILE"
            converted=$((converted + 1))
        else
            echo "  → Converting..."
            if ffmpeg -i "$avi_file" -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a copy "$mp4_file" -loglevel warning; then
                echo -e "  ${GREEN}✓ Done: $(basename "$mp4_file")${NC}"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $avi_file" >> "$LOG_FILE"
                converted=$((converted + 1))
                if [ "$DELETE_ORIGINALS" = true ]; then
                    rm "$avi_file"
                    echo -e "  ${GREEN}✓ Deleted original: $(basename "$avi_file")${NC}"
                    echo "[$(date '+%Y-%m-%d %H:%M:%S')] DELETED: $avi_file" >> "$LOG_FILE"
                    deleted=$((deleted + 1))
                fi
            else
                echo -e "  ${RED}✗ Failed${NC}"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED: $avi_file" >> "$LOG_FILE"
                # Remove incomplete output if it exists
                [ -f "$mp4_file" ] && rm "$mp4_file"
                failed=$((failed + 1))
            fi
        fi
        echo ""
    done < <(find "$dir" -name "*.avi" -not -name "._*" -print0 | sort -z)
}

for dir in "${DATA_DIRS[@]}"; do
    convert_directory "$dir"
done

# Summary
echo "============================================"
echo "  Conversion Summary"
if [ "$DRY_RUN" = true ]; then
    echo "  (DRY RUN - No files converted)"
fi
echo "============================================"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Would convert:      $converted${NC}"
    if [ "$DELETE_ORIGINALS" = true ]; then
        echo -e "${YELLOW}Would delete:       $converted${NC}"
    fi
else
    echo -e "${GREEN}Converted:          $converted${NC}"
    if [ "$DELETE_ORIGINALS" = true ]; then
        echo -e "${GREEN}Originals deleted:  $deleted${NC}"
    fi
fi
echo -e "${YELLOW}Skipped (existed):  $skipped${NC}"
if [ "$DRY_RUN" = false ]; then
    echo -e "${RED}Failed:             $failed${NC}"
fi
echo ""
echo "Log file: $LOG_FILE"
echo "============================================"

# Write summary to log
echo "----------------------------------------" >> "$LOG_FILE"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run completed at $(date)" >> "$LOG_FILE"
    echo "Summary: $converted would convert, $skipped skipped" >> "$LOG_FILE"
else
    echo "Conversion completed at $(date)" >> "$LOG_FILE"
    echo "Summary: $converted converted, $skipped skipped, $failed failed, $deleted originals deleted" >> "$LOG_FILE"
fi

if [ $failed -gt 0 ]; then
    exit 1
fi

exit 0
