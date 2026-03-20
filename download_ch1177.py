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


def create_landscape_spread_pdf(image_dir, output_path):
    """
    Create a landscape PDF with 2 manga pages per sheet.

    - First page is placed alone on the right side of the first sheet
      (this ensures subsequent pages pair correctly for double spreads).
    - Remaining pages are paired: [2,3], [4,5], [6,7], etc.
    - Within each sheet, pages are placed RIGHT then LEFT (manga order):
      right side = earlier page, left side = later page.
    - Each page is scaled to fit its half of the landscape sheet while
      maintaining aspect ratio.
    """
    image_files = sorted([
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif'))
    ])

    if not image_files:
        print("ERROR: No images found!")
        return

    print(f"Found {len(image_files)} pages. Creating landscape spread PDF...")

    # Build page pairs: first page alone, then pairs of 2
    # Page 1 alone (on right side), then [2,3], [4,5], etc.
    pairs = []
    pairs.append((image_files[0], None))  # First page solo (right side only)

    i = 1
    while i < len(image_files):
        right_page = image_files[i]
        left_page = image_files[i + 1] if i + 1 < len(image_files) else None
        pairs.append((right_page, left_page))
        i += 2

    sheets = []
    half_width = LANDSCAPE_WIDTH // 2

    for right_path, left_path in pairs:
        # Create landscape canvas (white background)
        sheet = Image.new('RGB', (LANDSCAPE_WIDTH, LANDSCAPE_HEIGHT), (255, 255, 255))

        # Place right page (manga: this is read first)
        right_img = Image.open(right_path).convert('RGB')
        right_img = scale_to_fit(right_img, half_width, LANDSCAPE_HEIGHT)
        # Center in right half
        x_offset = half_width + (half_width - right_img.width) // 2
        y_offset = (LANDSCAPE_HEIGHT - right_img.height) // 2
        sheet.paste(right_img, (x_offset, y_offset))
        right_img.close()

        # Place left page if exists
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
            resolution=226.0,  # reMarkable 2 DPI
            save_all=True,
            append_images=sheets[1:],
        )
        # Clean up
        for s in sheets:
            s.close()

    print(f"Landscape spread PDF saved: {output_path}")
    print(f"  - {len(sheets)} sheets total")
    print(f"  - First page is solo (right side)")
    print(f"  - Remaining pages paired for double-spread viewing")


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
