#!/usr/bin/env bash
# ==============================================================================
# md-to-report.sh
# Professional Markdown-to-HTML & PDF Report Generator for Pandoc
# Specially styled for Digital Forensics, Incident Response & Technical Audits
# ==============================================================================

set -euo pipefail
IFS=$'
	'

# Script metadata
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_VERSION="2.0.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Default configurations
DEFAULT_CSS="${SCRIPT_DIR}/styles/forensic.css"
CSS_FILE="${DEFAULT_CSS}"
INPUT_FILE=""
OUTPUT_FILE=""
DOC_TITLE=""
TOC=true
TOC_DEPTH=3
NUMBER_SECTIONS=false
EMBED_RESOURCES=true
HIGHLIGHT_STYLE="kate"
GENERATE_PDF=false
PDF_ENGINE=""
OPEN_AFTER=false
VERBOSE=false
QUIET=false
AUTO_NOWRAP=true
LUA_NOWRAP_FILTER="${SCRIPT_DIR}/filters/table-nowrap.lua"

# Temp files tracking for cleanup
TEMP_FILES=()
cleanup() {
    for f in "${TEMP_FILES[@]:-}"; do
        if [[ -f "$f" ]]; then
            rm -f "$f"
        fi
    done
}
trap cleanup EXIT INT TERM

# ------------------------------------------------------------------------------
# Terminal Color Support
# ------------------------------------------------------------------------------
if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    COLOR_RESET='[0m'
    COLOR_BOLD='[1m'
    COLOR_BLUE='[38;5;39m'
    COLOR_GREEN='[38;5;76m'
    COLOR_YELLOW='[38;5;214m'
    COLOR_RED='[38;5;196m'
    COLOR_GRAY='[38;5;245m'
else
    COLOR_RESET=''
    COLOR_BOLD=''
    COLOR_BLUE=''
    COLOR_GREEN=''
    COLOR_YELLOW=''
    COLOR_RED=''
    COLOR_GRAY=''
fi

log_info() {
    if [[ "$QUIET" = false ]]; then
        printf "%b[INFO]%b %s
" "${COLOR_BLUE}" "${COLOR_RESET}" "$*" >&2
    fi
}

log_success() {
    if [[ "$QUIET" = false ]]; then
        printf "%b[SUCCESS]%b %b%s%b
" "${COLOR_GREEN}" "${COLOR_RESET}" "${COLOR_BOLD}" "$*" "${COLOR_RESET}" >&2
    fi
}

log_warn() {
    printf "%b[WARNING]%b %s
" "${COLOR_YELLOW}" "${COLOR_RESET}" "$*" >&2
}

log_error() {
    printf "%b[ERROR]%b %s
" "${COLOR_RED}" "${COLOR_RESET}" "$*" >&2
}

log_verbose() {
    if [[ "$VERBOSE" = true ]] && [[ "$QUIET" = false ]]; then
        printf "%b[DEBUG]%b %s
" "${COLOR_GRAY}" "${COLOR_RESET}" "$*" >&2
    fi
}

die() {
    log_error "$*"
    exit 1
}

# ------------------------------------------------------------------------------
# Help & Documentation
# ------------------------------------------------------------------------------
show_help() {
    cat << HELP_EOF
${COLOR_BOLD}${SCRIPT_NAME} v${SCRIPT_VERSION}${COLOR_RESET}
Transform Markdown documents into professional, publication-quality forensic reports.

${COLOR_BOLD}USAGE:${COLOR_RESET}
    ${SCRIPT_NAME} [OPTIONS] <input.md> [output.html]

${COLOR_BOLD}ARGUMENTS:${COLOR_RESET}
    <input.md>                Source Markdown file to compile.
    [output.html]             Target HTML file (optional, defaults to <input_basename>.html).

${COLOR_BOLD}OPTIONS:${COLOR_RESET}
    -o, --output <file>       Specify target output file path (.html or .pdf).
    -t, --title <string>      Set or override the document title metadata.
    -s, --style <file>        Custom stylesheet to use.
                              Default: ${DEFAULT_CSS}
    
    --toc                     Generate an executive Table of Contents (default).
    --no-toc                  Disable Table of Contents generation.
    --toc-depth <1-6>         Depth of section headings included in TOC (default: 3).
    -N, --number-sections     Auto-number section headings (1, 1.1, 1.2...).
    
    --highlight-style <style> Pandoc syntax highlighting theme.
                              Options: kate (default), breezedark, pygments, tango,
                                       espresso, zenburn, monochrome, haddock, none.
    --embed-resources         Embed all CSS styles and web assets into a single,
                              fully portable, self-contained file (default).
    --no-embed-resources      Link external stylesheets instead of inlining.
    --no-auto-nowrap          Disable automatic unwrapped table timestamp detection.
    
    -p, --pdf                 Attempt direct PDF compilation using available PDF engines
                              (weasyprint, typst, wkhtmltopdf, pdflatex, or browser).
    --pdf-engine <program>    Specify explicit PDF engine for pandoc.
    
    --open                    Open the generated report in your default browser/viewer.
    -v, --verbose             Print detailed execution logs and pandoc flags.
    -q, --quiet               Suppress all informational and success messages.
    -h, --help                Display this comprehensive help screen and exit.
    -V, --version             Display version and exit.

${COLOR_BOLD}EXAMPLES:${COLOR_RESET}
    # Standard compilation with default forensic styling:
    ${SCRIPT_NAME} report.md

    # Custom title and output destination:
    ${SCRIPT_NAME} -t "Case IR-2026-0911A Forensic Analysis" -o final-report.html report.md

    # Numbered sections with custom TOC depth:
    ${SCRIPT_NAME} -N --toc-depth 2 incident-investigation.md

    # Generate directly to PDF and view:
    ${SCRIPT_NAME} --pdf --open report.md

${COLOR_BOLD}PRINTING & EXPORT TIPS:${COLOR_RESET}
    The generated HTML is natively optimized for print media (@media print).
    You can produce pixel-perfect A4/Letter PDFs at any time by opening the HTML in
    any modern browser and selecting "Print" (Ctrl+P) -> "Save as PDF".
    Ensure "Background graphics" is enabled in your browser print settings.
HELP_EOF
}

show_version() {
    echo "${SCRIPT_NAME} version ${SCRIPT_VERSION}"
    if command -v pandoc &>/dev/null; then
        pandoc_ver="$(pandoc --version | head -n 1)"
        echo "Engine: ${pandoc_ver}"
    else
        echo "Engine: Pandoc (NOT INSTALLED)"
    fi
}

# ------------------------------------------------------------------------------
# Argument Parsing
# ------------------------------------------------------------------------------
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -V|--version)
            show_version
            exit 0
            ;;
        -o|--output)
            [[ -n "${2:-}" ]] || die "Option '$1' requires an argument."
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -t|--title)
            [[ -n "${2:-}" ]] || die "Option '$1' requires an argument."
            DOC_TITLE="$2"
            shift 2
            ;;
        -s|--style)
            [[ -n "${2:-}" ]] || die "Option '$1' requires an argument."
            CSS_FILE="$2"
            shift 2
            ;;
        --toc)
            TOC=true
            shift
            ;;
        --no-toc)
            TOC=false
            shift
            ;;
        --toc-depth)
            [[ -n "${2:-}" ]] || die "Option '$1' requires a numerical depth argument."
            TOC_DEPTH="$2"
            shift 2
            ;;
        -N|--number-sections)
            NUMBER_SECTIONS=true
            shift
            ;;
        --highlight-style)
            [[ -n "${2:-}" ]] || die "Option '$1' requires a style name."
            HIGHLIGHT_STYLE="$2"
            shift 2
            ;;
        --embed-resources)
            EMBED_RESOURCES=true
            shift
            ;;
        --no-embed-resources)
            EMBED_RESOURCES=false
            shift
            ;;
        --no-auto-nowrap)
            AUTO_NOWRAP=false
            shift
            ;;
        -p|--pdf)
            GENERATE_PDF=true
            shift
            ;;
        --pdf-engine)
            [[ -n "${2:-}" ]] || die "Option '$1' requires an engine name."
            PDF_ENGINE="$2"
            GENERATE_PDF=true
            shift 2
            ;;
        --open)
            OPEN_AFTER=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        --)
            shift
            while [[ $# -gt 0 ]]; do
                POSITIONAL_ARGS+=("$1")
                shift
            done
            break
            ;;
        -*)
            die "Unrecognized option: '$1'. Use --help for available options."
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Resolve positional arguments
if [[ ${#POSITIONAL_ARGS[@]} -gt 0 ]]; then
    INPUT_FILE="${POSITIONAL_ARGS[0]}"
fi
if [[ ${#POSITIONAL_ARGS[@]} -gt 1 ]] && [[ -z "${OUTPUT_FILE}" ]]; then
    OUTPUT_FILE="${POSITIONAL_ARGS[1]}"
fi
if [[ ${#POSITIONAL_ARGS[@]} -gt 2 ]]; then
    die "Unexpected extra arguments: ${POSITIONAL_ARGS[*]:2}. See --help."
fi

# ------------------------------------------------------------------------------
# Pre-Flight Validation
# ------------------------------------------------------------------------------
# 1. Verify pandoc is installed
if ! command -v pandoc &>/dev/null; then
    die "Pandoc is not installed or not found in system PATH.
Please install Pandoc (https://pandoc.org):
  Debian/Ubuntu: sudo apt install pandoc
  Fedora/RHEL:   sudo dnf install pandoc
  Arch Linux:    sudo pacman -S pandoc
  macOS:         brew install pandoc"
fi

# 2. Verify input file is supplied
if [[ -z "${INPUT_FILE}" ]]; then
    log_error "No input markdown file specified."
    printf "Try '%s --help' for usage information.
" "${SCRIPT_NAME}" >&2
    exit 1
fi

# 3. Verify input file exists, is a regular file, is readable, and non-empty
if [[ ! -e "${INPUT_FILE}" ]]; then
    die "Input file does not exist: '${INPUT_FILE}'"
fi
if [[ ! -f "${INPUT_FILE}" ]]; then
    die "Input path is not a regular file: '${INPUT_FILE}'"
fi
if [[ ! -r "${INPUT_FILE}" ]]; then
    die "Input file is not readable: '${INPUT_FILE}'"
fi
if [[ ! -s "${INPUT_FILE}" ]]; then
    die "Input file is empty (0 bytes): '${INPUT_FILE}'"
fi

# 4. Verify CSS stylesheet exists
if [[ ! -f "${CSS_FILE}" ]]; then
    die "Stylesheet not found at: '${CSS_FILE}'"
fi

# 5. Determine default output file if not set
INPUT_BASENAME="$(basename "${INPUT_FILE}")"
INPUT_NAME="${INPUT_BASENAME%.*}"

if [[ -z "${OUTPUT_FILE}" ]]; then
    if [[ "${GENERATE_PDF}" = true ]]; then
        OUTPUT_FILE="${INPUT_NAME}.pdf"
    else
        OUTPUT_FILE="${INPUT_NAME}.html"
    fi
fi

# Check if target is PDF
if [[ "${OUTPUT_FILE}" == *.pdf ]]; then
    GENERATE_PDF=true
fi

# Ensure parent directory of output exists
OUTPUT_DIR="$(dirname "${OUTPUT_FILE}")"
if [[ ! -d "${OUTPUT_DIR}" ]]; then
    log_verbose "Creating output directory: ${OUTPUT_DIR}"
    mkdir -p "${OUTPUT_DIR}"
fi

# ------------------------------------------------------------------------------
# Pandoc Command Assembly
# ------------------------------------------------------------------------------
log_info "Preparing report compilation: ${INPUT_FILE} -> ${OUTPUT_FILE}"

# Detect Pandoc major version for flag compatibility
PANDOC_MAJOR_VERSION="$(pandoc --version | head -n 1 | awk '{print $2}' | cut -d'.' -f1)"
log_verbose "Detected Pandoc Major Version: ${PANDOC_MAJOR_VERSION}"

PANDOC_ARGS=(
    "--standalone"
    "-f" "markdown+smart+gfm_auto_identifiers+pipe_tables"
)

# Pandoc 3.x uses --embed-resources, 2.x uses --self-contained
if [[ "${EMBED_RESOURCES}" = true ]] && [[ "${GENERATE_PDF}" = false ]]; then
    if [[ "${PANDOC_MAJOR_VERSION}" -ge 3 ]]; then
        PANDOC_ARGS+=("--embed-resources")
    else
        PANDOC_ARGS+=("--self-contained")
    fi
fi

# Stylesheet attachment
PANDOC_ARGS+=("--css" "${CSS_FILE}")

# Table of Contents
if [[ "${TOC}" = true ]]; then
    PANDOC_ARGS+=("--toc" "--toc-depth=${TOC_DEPTH}")
fi

# Number sections
if [[ "${NUMBER_SECTIONS}" = true ]]; then
    PANDOC_ARGS+=("--number-sections")
fi

# Syntax Highlighting
if [[ "${HIGHLIGHT_STYLE}" != "none" ]]; then
    PANDOC_ARGS+=("--highlight-style=${HIGHLIGHT_STYLE}")
fi

# Metadata: Title override
if [[ -n "${DOC_TITLE}" ]]; then
    PANDOC_ARGS+=("--metadata" "title=${DOC_TITLE}")
fi

# Automatic table nowrap filter for timestamps & localized date columns
if [[ "${AUTO_NOWRAP}" = true ]] && [[ -f "${LUA_NOWRAP_FILTER}" ]]; then
    PANDOC_ARGS+=("--lua-filter=${LUA_NOWRAP_FILTER}")
    log_verbose "Using Lua filter for unwrapped timestamps: ${LUA_NOWRAP_FILTER}"
fi

# ------------------------------------------------------------------------------
# Compilation Execution
# ------------------------------------------------------------------------------
if [[ "${GENERATE_PDF}" = true ]]; then
    # Direct PDF generation requested
    log_info "Generating PDF format..."

    # Check for requested or available PDF engines
    CHOSEN_ENGINE=""
    if [[ -n "${PDF_ENGINE}" ]]; then
        if command -v "${PDF_ENGINE}" &>/dev/null; then
            CHOSEN_ENGINE="${PDF_ENGINE}"
        else
            die "Requested PDF engine '${PDF_ENGINE}' is not installed or not in PATH."
        fi
    else
        # Auto-detect engine
        for eng in weasyprint typst wkhtmltopdf xelatex pdflatex; do
            if command -v "$eng" &>/dev/null; then
                CHOSEN_ENGINE="$eng"
                break
            fi
        done
    fi

    if [[ -n "${CHOSEN_ENGINE}" ]]; then
        log_info "Using PDF engine: ${CHOSEN_ENGINE}"
        PANDOC_ARGS+=("--pdf-engine=${CHOSEN_ENGINE}")
        PANDOC_ARGS+=("-o" "${OUTPUT_FILE}" "${INPUT_FILE}")

        log_verbose "Running: pandoc ${PANDOC_ARGS[*]}"
        pandoc "${PANDOC_ARGS[@]}"
    else
        # No native PDF engine found; compile standalone HTML first
        log_warn "No native PDF engine found (weasyprint, typst, wkhtmltopdf, pdflatex)."
        TEMP_HTML="${OUTPUT_FILE%.pdf}.html"
        log_info "Compiling high-fidelity print-ready HTML to: ${TEMP_HTML}"

        HTML_ARGS=("${PANDOC_ARGS[@]}" "-t" "html5" "-o" "${TEMP_HTML}" "${INPUT_FILE}")
        log_verbose "Running: pandoc ${HTML_ARGS[*]}"
        pandoc "${HTML_ARGS[@]}"

        # Check if headless browser can convert HTML to PDF
        CONVERTED_PDF=false
        if command -v chromium &>/dev/null; then
            log_info "Converting HTML to PDF via Chromium headless..."
            chromium --headless --disable-gpu --print-to-pdf="${OUTPUT_FILE}" "file://${PWD}/${TEMP_HTML}" &>/dev/null && CONVERTED_PDF=true
        elif command -v chromium-browser &>/dev/null; then
            log_info "Converting HTML to PDF via Chromium headless..."
            chromium-browser --headless --disable-gpu --print-to-pdf="${OUTPUT_FILE}" "file://${PWD}/${TEMP_HTML}" &>/dev/null && CONVERTED_PDF=true
        elif command -v google-chrome &>/dev/null; then
            log_info "Converting HTML to PDF via Google Chrome headless..."
            google-chrome --headless --disable-gpu --print-to-pdf="${OUTPUT_FILE}" "file://${PWD}/${TEMP_HTML}" &>/dev/null && CONVERTED_PDF=true
        fi

        if [[ "${CONVERTED_PDF}" = false ]]; then
            log_warn "Could not automatically render direct PDF file."
            log_info "Standalone print-ready HTML created at: ${TEMP_HTML}"
            log_info "Tip: Open the HTML in any browser and select 'Print' -> 'Save as PDF' (Ctrl+P)."
            OUTPUT_FILE="${TEMP_HTML}"
        fi
    fi
else
    # HTML5 Compilation
    PANDOC_ARGS+=("-t" "html5" "-o" "${OUTPUT_FILE}" "${INPUT_FILE}")
    log_verbose "Executing: pandoc ${PANDOC_ARGS[*]}"
    pandoc "${PANDOC_ARGS[@]}"
fi

# ------------------------------------------------------------------------------
# Completion & Reporting
# ------------------------------------------------------------------------------
if [[ -f "${OUTPUT_FILE}" ]]; then
    FILE_SIZE="$(du -h "${OUTPUT_FILE}" | awk '{print $1}')"
    log_success "Report generated successfully!"
    printf "  %bOutput:%b    %s (%s)
" "${COLOR_BOLD}" "${COLOR_RESET}" "${OUTPUT_FILE}" "${FILE_SIZE}"
    printf "  %bStyle:%b     %s
" "${COLOR_BOLD}" "${COLOR_RESET}" "${CSS_FILE}"
    printf "  %bPrint:%b     Ready for physical print or browser PDF export (Ctrl+P)
" "${COLOR_BOLD}" "${COLOR_RESET}"
else
    die "Compilation finished but output file was not created: ${OUTPUT_FILE}"
fi

# Open if requested
if [[ "${OPEN_AFTER}" = true ]]; then
    if command -v xdg-open &>/dev/null; then
        xdg-open "${OUTPUT_FILE}" &>/dev/null || true
    elif command -v open &>/dev/null; then
        open "${OUTPUT_FILE}" &>/dev/null || true
    fi
fi

exit 0
