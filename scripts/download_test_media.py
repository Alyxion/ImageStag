#!/usr/bin/env python3
"""Download test media files for StreamView component testing.

Downloads Big Buck Bunny 1080p if not already present.

Usage:
    python scripts/download_test_media.py

    # Or with custom output directory:
    python scripts/download_test_media.py --output /path/to/media
"""

import argparse
import sys
import urllib.request
from pathlib import Path

# Test media URLs
MEDIA_FILES = {
    "big_buck_bunny_1080p_h264.mov": {
        "url": "https://download.blender.org/peach/bigbuckbunny_movies/big_buck_bunny_1080p_h264.mov",
        "size_mb": 691,
        "description": "Big Buck Bunny 1080p H.264 (~691 MB)",
    },
}

DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "tmp" / "media"


def download_file(url: str, dest: Path, description: str) -> bool:
    """Download a file with progress reporting.

    :param url: URL to download from
    :param dest: Destination path
    :param description: Human-readable description for progress
    :return: True if successful, False otherwise
    """
    print(f"Downloading {description}...")
    print(f"  URL: {url}")
    print(f"  Destination: {dest}")

    try:
        # Create a custom opener that shows progress
        def report_progress(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0:
                downloaded = block_num * block_size
                percent = min(100, downloaded * 100 // total_size)
                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                print(
                    f"\r  Progress: {percent}% ({downloaded_mb:.1f} / {total_mb:.1f} MB)",
                    end="",
                    flush=True,
                )

        urllib.request.urlretrieve(url, dest, reporthook=report_progress)
        print()  # Newline after progress
        print(f"  Downloaded successfully: {dest.stat().st_size / (1024*1024):.1f} MB")
        return True

    except Exception as e:
        print(f"\n  Error downloading: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download test media files for StreamView testing"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-download even if file exists",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    args.output.mkdir(parents=True, exist_ok=True)

    print(f"Test media directory: {args.output}")
    print()

    success_count = 0
    skip_count = 0
    fail_count = 0

    for filename, info in MEDIA_FILES.items():
        dest = args.output / filename

        if dest.exists() and not args.force:
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"Skipping {filename} (already exists, {size_mb:.1f} MB)")
            skip_count += 1
            continue

        if download_file(info["url"], dest, info["description"]):
            success_count += 1
        else:
            fail_count += 1

    print()
    print(f"Summary: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
