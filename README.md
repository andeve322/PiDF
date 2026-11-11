# PiDF, Terminal PDF Splitter for macOS

## Features
Drag a PDF file directly from Finder into your macOS Terminal. 
- **Flexible Interval Syntax**:
  - Multiple ranges: `1-3, 4-6, 7-10`
  - Ranges and single pages: `1-2, 4, 5-10`
  - Open-ended ranges: `5-` (page 5 to the end), `-3` (start to page 3)
  - Also supports `1..3` or `1 to 3`.
- **Automatic Same-Folder Saving**: Output PDFs are saved right next to the original PDF:
  - `document_pages_1-3.pdf`
  - `document_page_4.pdf`
- **Encrypted PDF Support**: Prompts for password if the PDF is password-protected.

---

## Quick Start

### 1. Requirements

Ensure you have Python 3 and `pypdf` installed:

```bash
pip3 install -r requirements.txt
```

### 2. Run the Splitter

You can run it in any of the following ways:

#### Run directly in Terminal
```bash
./pidf.py
# or
python3 pidf.py
```

#### Double-click from Finder
Double-click `pidf.command` in Finder. macOS Terminal will open automatically.

#### Drag onto the command line
```bash
./pidf.py /path/to/my_document.pdf
```

---
