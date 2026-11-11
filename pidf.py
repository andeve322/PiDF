#!/usr/bin/env python3
"""
macOS Interactive PDF Splitter
Drag and drop a PDF file into the terminal, select page intervals,
and split files will be saved in the same directory as the original PDF.
"""

import sys
import os
import shlex
import re
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("\n\033[91mError: 'pypdf' is not installed.\033[0m")
    print("Please install it by running:")
    print("    pip3 install pypdf\n")
    sys.exit(1)


# Terminal ANSI Colors
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def supports_color() -> bool:
    """Check if standard output supports ANSI colors."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(text: str, code: str) -> str:
    return f"{code}{text}{Colors.RESET}" if supports_color() else text


def clean_input_path(raw: str) -> Path:
    """
    Clean and resolve a path string, handling macOS drag-and-drop artifacts:
    - Escaped spaces: 'My\\ File.pdf'
    - Escaped parentheses: 'File\\(1\\).pdf'
    - Surrounding single/double quotes
    - Trailing spaces
    - Tilde (~) expansion
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty path provided.")

    # 1. Direct check with quotes removed
    candidate_raw = raw.strip("'\"")
    direct = Path(os.path.expanduser(candidate_raw)).resolve()
    if direct.exists():
        return direct

    # 2. Try POSIX shell splitting (handles quoted and backslash-escaped strings)
    try:
        parts = shlex.split(raw)
        if parts:
            p_shlex = Path(os.path.expanduser(parts[0])).resolve()
            if p_shlex.exists():
                return p_shlex
    except Exception:
        pass

    # 3. Handle manual backslash escaping common in macOS drag-and-drop
    # Replace backslash-escaped characters: '\ ' -> ' ', '\(' -> '(', etc.
    unescaped = re.sub(r"\\(.)", r"\1", candidate_raw)
    p_unescaped = Path(os.path.expanduser(unescaped)).resolve()
    if p_unescaped.exists():
        return p_unescaped

    # Fallback to resolved unescaped path even if it might not exist yet
    return p_unescaped


def parse_intervals(interval_str: str, total_pages: int) -> list[tuple[int, int]]:
    """
    Parses human-friendly interval strings into a list of (start_page, end_page) 1-based tuples.
    Supports formats like:
      - '1-3, 4-6, 7-10'
      - '1, 3-5, 8'
      - '1-3; 4-6'
      - '1..3, 4 to 6'
      - '1-4, 5-end'
      - '-3, 4-'
    """
    cleaned = interval_str.replace(";", ",").strip()
    if not cleaned:
        raise ValueError("No intervals entered.")

    chunks = [c.strip() for c in cleaned.split(",") if c.strip()]
    if not chunks:
        raise ValueError("No intervals entered.")

    parsed: list[tuple[int, int]] = []

    for chunk in chunks:
        # Standardize separators: '..', ' to ', ' - ' -> '-'
        norm = chunk.replace("..", "-")
        norm = re.sub(r"\s+to\s+", "-", norm, flags=re.IGNORECASE)
        parts = [p.strip() for p in norm.split("-")]

        if len(parts) == 1:
            # Single page, e.g. "5"
            try:
                page = int(parts[0])
            except ValueError:
                raise ValueError(f"Invalid page number: '{parts[0]}'")

            if not (1 <= page <= total_pages):
                raise ValueError(
                    f"Page {page} is out of range. Document has {total_pages} page(s)."
                )
            parsed.append((page, page))

        elif len(parts) == 2:
            p_start, p_end = parts[0], parts[1]

            # Start page handling (empty or 'start' defaults to 1)
            if p_start == "" or p_start.lower() in ("start", "begin"):
                start = 1
            else:
                try:
                    start = int(p_start)
                except ValueError:
                    raise ValueError(f"Invalid start page: '{p_start}'")

            # End page handling (empty or 'end'/'last' defaults to total_pages)
            if p_end == "" or p_end.lower() in ("end", "last"):
                end = total_pages
            else:
                try:
                    end = int(p_end)
                except ValueError:
                    raise ValueError(f"Invalid end page: '{p_end}'")

            # Validate bounds
            if not (1 <= start <= total_pages):
                raise ValueError(
                    f"Start page {start} is out of range (1 - {total_pages})."
                )
            if not (1 <= end <= total_pages):
                raise ValueError(
                    f"End page {end} is out of range (1 - {total_pages})."
                )
            if start > end:
                raise ValueError(
                    f"Start page {start} cannot be greater than end page {end}."
                )

            parsed.append((start, end))
        else:
            raise ValueError(f"Could not parse interval format: '{chunk}'")

    return parsed


def format_file_size(num_bytes: int) -> str:
    """Format bytes into readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:3.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def get_unique_output_path(base_path: Path) -> Path:
    """Generate a unique path if file already exists by appending (1), (2), etc."""
    if not base_path.exists():
        return base_path
    parent = base_path.parent
    stem = base_path.stem
    ext = base_path.suffix
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1


def split_pdf_intervals(
    pdf_path: Path, intervals: list[tuple[int, int]]
) -> list[Path]:
    """
    Splits the PDF into multiple files based on intervals.
    Saves to the same directory as the original PDF.
    """
    reader = PdfReader(str(pdf_path))
    output_dir = pdf_path.parent
    stem = pdf_path.stem
    created_files: list[Path] = []

    for start, end in intervals:
        writer = PdfWriter()
        # pypdf uses 0-based page indexing
        for page_idx in range(start - 1, end):
            writer.add_page(reader.pages[page_idx])

        # Generate output filename
        if start == end:
            filename = f"{stem}_page_{start}.pdf"
        else:
            filename = f"{stem}_pages_{start}-{end}.pdf"

        out_path = output_dir / filename
        out_path = get_unique_output_path(out_path)

        with open(out_path, "wb") as f_out:
            writer.write(f_out)

        created_files.append(out_path)

    return created_files


def print_banner():
    banner = f"""
{Colors.CYAN}{Colors.BOLD}╔═══════════════════════════════════════════════════════════╗
║           PiDF - Split Your PDFs, Easy as Pi              ║
╚═══════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def process_pdf(pdf_path: Path):
    """Handles page count, interval input, and splitting for a single PDF."""
    if not pdf_path.exists():
        print(color(f"\n❌ Error: File not found: {pdf_path}", Colors.RED))
        return

    if not pdf_path.suffix.lower() == ".pdf":
        print(color(f"\n⚠️  Warning: '{pdf_path.name}' does not have a .pdf extension.", Colors.YELLOW))

    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            print(color("\n🔒 This PDF is password protected.", Colors.YELLOW))
            pwd = input("Enter password: ")
            if not reader.decrypt(pwd):
                print(color("❌ Incorrect password.", Colors.RED))
                return
        total_pages = len(reader.pages)
    except Exception as e:
        print(color(f"\n❌ Error opening PDF: {e}", Colors.RED))
        return

    print("\n" + "─" * 59)
    print(f"📄 {color('File:', Colors.BOLD)}   {pdf_path.name}")
    print(f"📁 {color('Path:', Colors.BOLD)}   {pdf_path.parent}")
    print(f"📊 {color('Pages:', Colors.BOLD)}  {color(str(total_pages), Colors.GREEN)} total page(s)")
    print("─" * 59)

    # Prompt for intervals with retry loop
    while True:
        print(f"\n{color('Enter page intervals to split:', Colors.CYAN)}")
        print(color("  Examples:", Colors.DIM))
        if total_pages >= 6:
            print(color(f"    • Multiple ranges:  1-3, 4-6, 7-{total_pages}", Colors.DIM))
            print(color(f"    • Ranges & singles: 1-2, 4, 5-{total_pages}", Colors.DIM))
        else:
            print(color("    • e.g. 1, 2, 3 or 1-2, 3", Colors.DIM))
        print(color("  (or type 'b' to choose another file, 'q' to quit)", Colors.DIM))

        try:
            user_input = input(f"\n{color('Intervals > ', Colors.BOLD)}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if user_input.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            sys.exit(0)
        if user_input.lower() in ("b", "back"):
            return

        if not user_input:
            print(color("Please enter at least one interval.", Colors.YELLOW))
            continue

        try:
            intervals = parse_intervals(user_input, total_pages)
            break
        except ValueError as err:
            print(color(f"❌ {err}", Colors.RED))
            print(color("Please try again.", Colors.YELLOW))

    print(f"\n⚡ Splitting into {len(intervals)} file(s)...")

    try:
        created = split_pdf_intervals(pdf_path, intervals)
        print(color("\n✅ Successfully created the following PDF(s):", Colors.GREEN + Colors.BOLD))
        for p in created:
            size_str = format_file_size(p.stat().st_size)
            print(f"   • {color(p.name, Colors.BOLD)}  {color(f'({size_str})', Colors.DIM)}")
        print(f"\n📂 Saved in: {color(str(pdf_path.parent), Colors.CYAN)}")
    except Exception as e:
        print(color(f"\n❌ Error during splitting: {e}", Colors.RED))


def main():
    print_banner()

    # If a path was passed via CLI argument
    if len(sys.argv) > 1:
        raw_arg = sys.argv[1]
        try:
            pdf_path = clean_input_path(raw_arg)
            process_pdf(pdf_path)
        except Exception as e:
            print(color(f"❌ Invalid path: {e}", Colors.RED))

    # Interactive loop
    while True:
        print("\n" + "═" * 59)
        print(color("Drag & drop your PDF into this window (or type path, 'q' to quit):", Colors.BOLD))
        try:
            raw_input = input(f"{color('PDF File > ', Colors.CYAN)}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if raw_input.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break

        if not raw_input:
            continue

        try:
            pdf_path = clean_input_path(raw_input)
            process_pdf(pdf_path)
        except Exception as e:
            print(color(f"❌ Error with input: {e}", Colors.RED))


if __name__ == "__main__":
    main()

