#!/usr/bin/env python3
"""
Codebase Extractor
==================

This script recursively walks through a folder (your app's codebase),
reads the content of every text file, and combines everything into
a single, well-formatted text file.

You can then copy-paste the output file or attach it when chatting with me
so I get the full context of your app in one go.

Usage:
    python extract_codebase.py /path/to/your/app output.txt

Optional flags:
    --ignore-dirs  Comma-separated list of directories to skip
                   (default: .git,__pycache__,node_modules,venv,env,.venv,dist,build)
    --max-size     Maximum file size in MB to include (default: 5)
    --extensions   Only include these file extensions (e.g. .py,.js,.ts,.html,.css)
                   If omitted, tries to read every file as text.
"""

import os
import argparse
from pathlib import Path

def is_binary_file(file_path: str) -> bool:
    """Quick check to see if a file looks binary."""
    try:
        with open(file_path, 'rb') as f:
            # Read first 1024 bytes and look for null bytes (common in binaries)
            chunk = f.read(1024)
            return b'\0' in chunk
    except:
        return True

def extract_codebase(directory: str, output_file: str, ignore_dirs: list, max_size_mb: int, extensions: list = None):
    directory = Path(directory).resolve()
    if not directory.is_dir():
        print(f"Error: Directory '{directory}' does not exist or is not a folder.")
        return

    total_files = 0
    skipped_files = 0

    with open(output_file, 'w', encoding='utf-8') as out:
        # Header
        out.write("=" * 100 + "\n")
        out.write("CODEBASE EXTRACTION\n")
        out.write(f"Source folder: {directory}\n")
        out.write(f"Generated on: {os.getenv('USER', 'unknown')} @ {os.uname().nodename if hasattr(os, 'uname') else 'unknown'}\n")
        out.write("=" * 100 + "\n\n")

        for root, dirs, files in os.walk(directory):
            # Remove ignored directories in-place so os.walk skips them
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]

            for filename in files:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(directory)

                # Filter by extension if requested
                if extensions and file_path.suffix.lower() not in extensions:
                    skipped_files += 1
                    continue

                # Skip very large files
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    if size_mb > max_size_mb:
                        out.write(f"{'='*80}\n")
                        out.write(f"SKIPPED (too large): {rel_path} ({size_mb:.1f} MB)\n")
                        out.write(f"{'='*80}\n\n")
                        skipped_files += 1
                        continue
                except:
                    skipped_files += 1
                    continue

                # Skip obvious binary files
                if is_binary_file(str(file_path)):
                    out.write(f"{'='*80}\n")
                    out.write(f"SKIPPED (binary file): {rel_path}\n")
                    out.write(f"{'='*80}\n\n")
                    skipped_files += 1
                    continue

                # Read and write the file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try a different encoding as fallback
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                    except:
                        out.write(f"{'='*80}\n")
                        out.write(f"SKIPPED (cannot decode): {rel_path}\n")
                        out.write(f"{'='*80}\n\n")
                        skipped_files += 1
                        continue
                except Exception as e:
                    out.write(f"{'='*80}\n")
                    out.write(f"ERROR reading {rel_path}: {e}\n")
                    out.write(f"{'='*80}\n\n")
                    skipped_files += 1
                    continue

                # Write nicely formatted section
                out.write(f"{'='*80}\n")
                out.write(f"FILE: {rel_path}\n")
                out.write(f"Path: {file_path}\n")
                out.write(f"Size: {file_path.stat().st_size / 1024:.1f} KB\n")
                out.write(f"{'='*80}\n\n")
                out.write(content)
                out.write("\n\n")

                total_files += 1

        # Footer summary
        out.write("=" * 100 + "\n")
        out.write("EXTRACTION COMPLETE\n")
        out.write(f"Total files included : {total_files}\n")
        out.write(f"Files skipped        : {skipped_files}\n")
        out.write(f"Output file          : {output_file}\n")
        out.write("=" * 100 + "\n")

    print(f"✅ Success! {total_files} files extracted to '{output_file}'")
    print(f"   (Skipped {skipped_files} files)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract entire codebase into a single text file")
    parser.add_argument("directory", help="Root directory of your app/codebase")
    parser.add_argument("output", help="Output text file (e.g. my_app_codebase.txt)")
    parser.add_argument("--ignore-dirs", default=".git,__pycache__,node_modules,venv,env,.venv,dist,build,.idea,.vscode,__snapshots__",
                        help="Comma-separated directories to ignore (default shown)")
    parser.add_argument("--max-size", type=int, default=5,
                        help="Maximum file size in MB to include (default: 5)")
    parser.add_argument("--extensions", nargs="*", default=None,
                        help="Only include these extensions (e.g. --extensions .py .js .ts .html)")

    args = parser.parse_args()

    ignore_list = [d.strip() for d in args.ignore_dirs.split(",") if d.strip()]

    # Convert extensions to lowercase with leading dot
    if args.extensions:
        ext_list = [e.lower() if e.startswith('.') else '.' + e.lower() for e in args.extensions]
    else:
        ext_list = None

    extract_codebase(
        directory=args.directory,
        output_file=args.output,
        ignore_dirs=ignore_list,
        max_size_mb=args.max_size,
        extensions=ext_list
    )