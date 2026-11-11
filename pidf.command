#!/usr/bin/env bash
# macOS Terminal Launcher for PDF Splitter
# Double-clicking this file in Finder opens Terminal and runs the PDF splitter.

cd "$(dirname "$0")" || exit 1
python3 split_pdf.py

