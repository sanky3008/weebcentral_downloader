#!/usr/bin/env python3
"""
Download One Piece Chapter 1177 and create a landscape double-page spread PDF
optimized for reMarkable 2.

Usage:
    pip install -r requirements.txt
    pip install PyPDF2   # for PDF post-processing
    python download_ch1177.py

The script will:
1. Download chapter 1177 images from WeebCentral
2. Create a standard PDF
3. Post-process into a landscape PDF with 2 pages per sheet
   - First page is kept single (so double spreads align correctly)
   - Pages are arranged right-to-left within each sheet (manga reading order)
"""

import os
import sys
from PIL import Image
from weebcentral_scraper import WeebCentralScraper

MANGA_URL = "https://weebcentral.com/series/01J76XY7E9FNDZ1DBBM6PBJPFK/One-Piece"
CHAPTER = 1177
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
# reMarkable 2 screen: 1872 x 1404 px at 226 DPI. Landscape = 1872w x 1404h
# We target a slightly larger canvas for print quality
LANDSCAPE_WIDTH = 1872
LANDSCAPE_HEIGHT = 1404


def download_chapter():
    """Download chapter 1177 using the repo's scraper."""
    print(f"=== Downloading One Piece Chapter {CHAPTER} ===")
    scraper = WeebCentralScraper(
        manga_url=MANGA_URL,
        chapter_range=CHAPTER,
        output_dir=OUTPUT_DIR,
        delay=1.0,
        max_threads=4,
        convert_to_pdf=True,
        delete_images_after_conversion=False,
    )
    success = scraper.run()
    if not success:
        print("ERROR: Download failed!")
        sys.exit(1)
    return scraper.output_dir


def find_chapter_images(manga_dir):
    """Find the downloaded chapter image directory."""
    for entry in os.listdir(manga_dir):
        entry_path = os.path.join(manga_dir, entry)
        if os.path.isdir(entry_path) and "1177" in entry:
            return entry_path
    # Fallback: find any directory with images
    for entry in sorted(os.listdir(manga_dir)):
        entry_path = os.path.join(manga_dir, entry)
        if os.path.isdir(entry_path):
            images = [f for f in os.listdir(entry_path)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if images:
                return entry_path
    return None


def is_wide(filepath):
    """Check if an image is landscape/wide (likely a double-page spread)."""
    with Image.open(filepath) as img:
        return img.width > img.height


def create_landscape_spread_pdf(image_dir, output_path):
    """
    Create a landscape PDF with smart double-spread detection.

    - Wide/landscape images (Oda's double spreads) get their own FULL sheet
    - Portrait pages are paired two-per-sheet in manga order (right-to-left)
    - First portrait page is solo on right side to maintain odd/even alignment
    """
    image_files = sorted([
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
    ])

    if not image_files:
        print("ERROR: No images found!")
        return

    print(f"Found {len(image_files)} pages. Detecting spreads...")

    # Classify each page
    wide_pages = set()
    for f in image_files:
        if is_wide(f):
            wide_pages.add(f)
            print(f"   Wide spread detected: {os.path.basename(f)}")

    # Build sheet plan:
    # - Wide images -> solo full sheet
    # - Portrait images -> pair up, first one solo to maintain alignment
    sheets_plan = []  # list of (right_path, left_path) or (wide_path, 'FULL')
    portrait_buffer = []

    def flush_portraits():
        nonlocal portrait_buffer
        if not portrait_buffer:
            return
        i = 0
        while i < len(portrait_buffer):
            right = portrait_buffer[i]
            left = portrait_buffer[i + 1] if i + 1 < len(portrait_buffer) else None
            sheets_plan.append((right, left))
            i += 2
        portrait_buffer = []

    for f in image_files:
        if f in wide_pages:
            flush_portraits()
            sheets_plan.append((f, 'FULL'))
        else:
            portrait_buffer.append(f)

    flush_portraits()

    sheets = []
    half_width = LANDSCAPE_WIDTH // 2

    for right_path, left_path in sheets_plan:
        sheet = Image.new('RGB', (LANDSCAPE_WIDTH, LANDSCAPE_HEIGHT), (255, 255, 255))

        if left_path == 'FULL':
            # Wide spread — scale to fill the entire sheet
            wide_img = Image.open(right_path).convert('RGB')
            wide_img = scale_to_fit(wide_img, LANDSCAPE_WIDTH, LANDSCAPE_HEIGHT)
            x_offset = (LANDSCAPE_WIDTH - wide_img.width) // 2
            y_offset = (LANDSCAPE_HEIGHT - wide_img.height) // 2
            sheet.paste(wide_img, (x_offset, y_offset))
            wide_img.close()
        else:
            # Right half (read first in manga)
            right_img = Image.open(right_path).convert('RGB')
            right_img = scale_to_fit(right_img, half_width, LANDSCAPE_HEIGHT)
            x_offset = half_width + (half_width - right_img.width) // 2
            y_offset = (LANDSCAPE_HEIGHT - right_img.height) // 2
            sheet.paste(right_img, (x_offset, y_offset))
            right_img.close()

            # Left half
            if left_path:
                left_img = Image.open(left_path).convert('RGB')
                left_img = scale_to_fit(left_img, half_width, LANDSCAPE_HEIGHT)
                x_offset = (half_width - left_img.width) // 2
                y_offset = (LANDSCAPE_HEIGHT - left_img.height) // 2
                sheet.paste(left_img, (x_offset, y_offset))
                left_img.close()

        sheets.append(sheet)

    # Save as PDF
    if sheets:
        sheets[0].save(
            output_path,
            "PDF",
            resolution=226.0,
            save_all=True,
            append_images=sheets[1:],
        )
        for s in sheets:
            s.close()

    wide_count = sum(1 for _, lp in sheets_plan if lp == 'FULL')
    paired_count = len(sheets_plan) - wide_count
    print(f"Landscape spread PDF saved: {output_path}")
    print(f"  - {len(sheets)} sheets total")
    print(f"  - {wide_count} full-width double spreads")
    print(f"  - {paired_count} paired portrait sheets")


def scale_to_fit(img, max_width, max_height):
    """Scale image to fit within max dimensions, preserving aspect ratio."""
    ratio = min(max_width / img.width, max_height / img.height)
    if ratio >= 1:
        return img  # Already fits
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.LANCZOS)


def main():
    # Step 1: Download
    manga_dir = download_chapter()
    print(f"Downloaded to: {manga_dir}")

    # Step 2: Find chapter images
    image_dir = find_chapter_images(manga_dir)
    if not image_dir:
        print("ERROR: Could not find chapter image directory!")
        sys.exit(1)
    print(f"Chapter images in: {image_dir}")

    # Step 3: Create landscape spread PDF
    output_pdf = os.path.join(manga_dir, f"One_Piece_Ch{CHAPTER}_Landscape_Spread.pdf")
    create_landscape_spread_pdf(image_dir, output_pdf)

    print("\n=== Done! ===")
    print(f"Standard PDF:   {manga_dir}/Chapter {CHAPTER}.pdf")
    print(f"Landscape PDF:  {output_pdf}")


if __name__ == "__main__":
    main()
