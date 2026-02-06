#!/bin/bash

# Configuration
REMOTE="remote:data/Dan-CN-data-share/FP and opto datasets"
VALIDATION_REPORT="/Users/pauladkisson/Documents/CatalystNeuro/DanConv/dan-lab-to-nwb/download_utils/validation_report.json"
DEST_DIR="."
LOG_FILE="download_log.txt"

# Parse command line arguments
DRY_RUN=false
CHECK_SIZE=false
LIMIT=0
SETUP_FILTER=""
LIST_SETUPS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --check-size)
            CHECK_SIZE=true
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --setup)
            SETUP_FILTER="$2"
            shift 2
            ;;
        --list-setups)
            LIST_SETUPS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--check-size] [--limit N] [--setup \"Setup Name\"] [--list-setups]"
            echo "  --dry-run         Show what would be downloaded without downloading"
            echo "  --check-size      Calculate total size of sessions to download"
            echo "  --limit N         Only process first N sessions (for testing)"
            echo "  --setup \"Name\"    Filter sessions by setup name (e.g., \"Setup - Bing\")"
            echo "  --list-setups     List all available setup names and exit"
            exit 1
            ;;
    esac
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Initialize counters
total_sessions=0
downloaded=0
skipped=0
failed=0

echo "============================================"
echo "  Valid Sessions Download Script"
echo "============================================"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}  [DRY RUN MODE - No files will be downloaded]${NC}"
fi
if [ "$CHECK_SIZE" = true ]; then
    echo -e "${YELLOW}  [CHECK SIZE MODE - Calculating total size]${NC}"
fi
if [ $LIMIT -gt 0 ]; then
    echo -e "${YELLOW}  [LIMIT MODE - Processing only first $LIMIT sessions]${NC}"
fi
if [ -n "$SETUP_FILTER" ]; then
    echo -e "${YELLOW}  [SETUP FILTER - Only '$SETUP_FILTER' sessions]${NC}"
fi
echo ""

# 1. Check dependencies
echo "Checking dependencies..."

if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is not installed${NC}"
    echo "Please install jq: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi

if ! command -v rclone &> /dev/null; then
    echo -e "${RED}Error: rclone is not installed${NC}"
    echo "Please install rclone: https://rclone.org/install/"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies OK${NC}"
echo ""

# 2. Check if validation_report.json exists
if [ ! -f "$VALIDATION_REPORT" ]; then
    echo -e "${RED}Error: $VALIDATION_REPORT not found${NC}"
    echo "Please run the validation script first to generate the report."
    exit 1
fi

echo -e "${GREEN}✓ Validation report found${NC}"
echo ""

# 2.5. List setups if requested
if [ "$LIST_SETUPS" = true ]; then
    echo "============================================"
    echo "  Available Setups"
    echo "============================================"
    echo ""

    # Extract unique setup names (first directory component)
    jq -r '.valid_sessions[]' "$VALIDATION_REPORT" | cut -d'/' -f1 | sort -u | while IFS= read -r setup; do
        # Count sessions for this setup
        count=$(jq -r '.valid_sessions[]' "$VALIDATION_REPORT" | grep -c "^$setup/")
        echo "  $setup ($count sessions)"
    done

    echo ""
    echo "============================================"
    echo ""
    echo "Usage: $0 --setup \"Setup Name\""
    echo "Example: $0 --setup \"Setup - Bing\" --dry-run"
    exit 0
fi

# 3. Parse validation report and count sessions
echo "Reading valid sessions from $VALIDATION_REPORT..."
# Store sessions in temp file for compatibility with older bash
temp_sessions=$(mktemp)
jq -r '.valid_sessions[]' "$VALIDATION_REPORT" > "$temp_sessions"

# Read into array
sessions=()
while IFS= read -r session; do
    sessions+=("$session")
done < "$temp_sessions"
rm "$temp_sessions"

# Filter by setup if specified
if [ -n "$SETUP_FILTER" ]; then
    echo "Filtering sessions for setup: $SETUP_FILTER"
    filtered_sessions=()
    for session in "${sessions[@]}"; do
        if [[ "$session" == "$SETUP_FILTER"* ]]; then
            filtered_sessions+=("$session")
        fi
    done
    sessions=("${filtered_sessions[@]}")

    # Warn if no sessions match the filter
    if [ ${#sessions[@]} -eq 0 ]; then
        echo -e "${YELLOW}Warning: No sessions found for setup '$SETUP_FILTER'${NC}"
        echo "Use --list-setups to see available setup names"
        exit 0
    fi

    echo -e "${GREEN}Found ${#sessions[@]} sessions for this setup${NC}"
    echo ""
fi

total_sessions=${#sessions[@]}

if [ $total_sessions -eq 0 ]; then
    echo -e "${YELLOW}No valid sessions found in report.${NC}"
    exit 0
fi

# Apply limit if specified
if [ $LIMIT -gt 0 ] && [ $LIMIT -lt $total_sessions ]; then
    sessions=("${sessions[@]:0:$LIMIT}")
    total_sessions=$LIMIT
fi

echo -e "${GREEN}Found $total_sessions valid sessions to download${NC}"
echo ""

# 4. Initialize log file
if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN started at $(date)" > "$LOG_FILE"
else
    echo "Download started at $(date)" > "$LOG_FILE"
fi
echo "Total sessions: $total_sessions" >> "$LOG_FILE"
if [ $LIMIT -gt 0 ]; then
    echo "Limit: $LIMIT sessions" >> "$LOG_FILE"
fi
if [ -n "$SETUP_FILTER" ]; then
    echo "Setup filter: $SETUP_FILTER" >> "$LOG_FILE"
fi
echo "----------------------------------------" >> "$LOG_FILE"

# 4.5. Check size if requested
if [ "$CHECK_SIZE" = true ]; then
    echo "Calculating total size of sessions..."
    echo ""

    total_bytes=0
    current=0

    for session in "${sessions[@]}"; do
        current=$((current + 1))
        echo "[$current/$total_sessions] Checking size: $session"

        # Use rclone size to get the size of this session
        size_output=$(rclone size "$REMOTE/$session" --drive-shared-with-me --json 2>/dev/null)

        if [ $? -eq 0 ]; then
            # Extract bytes from JSON output
            session_bytes=$(echo "$size_output" | jq -r '.bytes')

            # Check if bytes is valid (not null or empty)
            if [ "$session_bytes" != "null" ] && [ -n "$session_bytes" ] && [ "$session_bytes" -gt 0 ] 2>/dev/null; then
                total_bytes=$((total_bytes + session_bytes))

                # Convert to human readable for display
                if [ "$session_bytes" -ge 1099511627776 ]; then
                    session_size=$(awk "BEGIN {printf \"%.2f TB\", $session_bytes / 1099511627776}")
                elif [ "$session_bytes" -ge 1073741824 ]; then
                    session_size=$(awk "BEGIN {printf \"%.2f GB\", $session_bytes / 1073741824}")
                elif [ "$session_bytes" -ge 1048576 ]; then
                    session_size=$(awk "BEGIN {printf \"%.2f MB\", $session_bytes / 1048576}")
                else
                    session_size=$(awk "BEGIN {printf \"%.2f KB\", $session_bytes / 1024}")
                fi
                echo "  Size: $session_size"
            else
                echo -e "  ${YELLOW}⚠ Could not determine size (empty or invalid)${NC}"
            fi
        else
            echo -e "  ${YELLOW}⚠ Could not determine size${NC}"
        fi
    done

    # Convert total bytes to human readable
    if [ $total_bytes -gt 0 ]; then
        # Calculate in different units using awk
        total_kb=$(awk "BEGIN {printf \"%.2f\", $total_bytes / 1024}")
        total_mb=$(awk "BEGIN {printf \"%.2f\", $total_bytes / 1048576}")
        total_gb=$(awk "BEGIN {printf \"%.2f\", $total_bytes / 1073741824}")
        total_tb=$(awk "BEGIN {printf \"%.2f\", $total_bytes / 1099511627776}")

        echo ""
        echo "============================================"
        echo "  Size Summary"
        echo "============================================"
        if [ -n "$SETUP_FILTER" ]; then
            echo "Setup:          $SETUP_FILTER"
        fi
        echo "Total sessions: $total_sessions"
        if (( $(awk "BEGIN {print ($total_gb >= 1000)}") )); then
            echo "Total size:     $total_tb TB"
        elif (( $(awk "BEGIN {print ($total_gb >= 1)}") )); then
            echo "Total size:     $total_gb GB"
        else
            echo "Total size:     $total_mb MB"
        fi
        echo "============================================"
    fi

    exit 0
fi

# 5. Download sessions
echo "Starting downloads..."
echo ""

current=0
for session in "${sessions[@]}"; do
    current=$((current + 1))

    echo "[$current/$total_sessions] Processing: $session"

    # Check if session already exists locally
    if [ -d "$session" ]; then
        echo -e "  ${YELLOW}→ Already exists, skipping${NC}"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] SKIPPED: $session" >> "$LOG_FILE"
        skipped=$((skipped + 1))
        echo ""
        continue
    fi

    # Download the session
    if [ "$DRY_RUN" = true ]; then
        echo -e "  ${YELLOW}→ [DRY RUN] Would download from: $REMOTE/$session${NC}"
        echo -e "  ${YELLOW}→ [DRY RUN] Would save to: $DEST_DIR/$session${NC}"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] DRY-RUN: $session" >> "$LOG_FILE"
        downloaded=$((downloaded + 1))
    else
        echo "  → Downloading..."
        if rclone copy "$REMOTE/$session" "$DEST_DIR/$session" --drive-shared-with-me -P; then
            echo -e "  ${GREEN}✓ Success${NC}"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $session" >> "$LOG_FILE"
            downloaded=$((downloaded + 1))
        else
            echo -e "  ${RED}✗ Failed${NC}"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] FAILED: $session" >> "$LOG_FILE"
            failed=$((failed + 1))
        fi
    fi

    echo ""
done

# 6. Print summary
echo "============================================"
echo "  Download Summary"
if [ "$DRY_RUN" = true ]; then
    echo "  (DRY RUN - No files downloaded)"
fi
echo "============================================"
if [ -n "$SETUP_FILTER" ]; then
    echo "Setup:              $SETUP_FILTER"
fi
echo "Total sessions:     $total_sessions"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}Would download:     $downloaded${NC}"
else
    echo -e "${GREEN}Downloaded:         $downloaded${NC}"
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
    echo "Summary: $downloaded would download, $skipped skipped" >> "$LOG_FILE"
else
    echo "Download completed at $(date)" >> "$LOG_FILE"
    echo "Summary: $downloaded downloaded, $skipped skipped, $failed failed" >> "$LOG_FILE"
fi

# Exit with error code if any downloads failed
if [ $failed -gt 0 ]; then
    exit 1
fi

exit 0
