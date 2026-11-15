import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


def parse_args(argv: Optional[list[str]] = None) -> list[Path]:
    
    parser = argparse.ArgumentParser(
        description="Read supported image files in binary mode."
    )
    parser.add_argument("paths", nargs="+", help="relative paths to image files")
    # parse_args is a method of the ArgumentParser
    args = parser.parse_args(argv)
    paths = []
    for path in args.paths:
        paths.append(Path(path))
    return paths


def display_filesystem_metadata(path: Path) -> None:
    file_stat = path.stat()

    print("-" * 50)
    print("Filesystem metadata")
    print("-" * 50)
    print(f"{'Path':<17} {path}")
    print(f"{'File name':<17} {path.name}")
    print(f"{'Size':<17} {file_stat.st_size} bytes")
    print(
        f"{'Modified':<17} "
        f"{datetime.fromtimestamp(file_stat.st_mtime)}"
    )
    print(
        f"{'Accessed':<17} "
        f"{datetime.fromtimestamp(file_stat.st_atime)}"
    )
    print(
        f"{'Metadata changed':<17} "
        f"{datetime.fromtimestamp(file_stat.st_ctime)}"
    )


def display_image_properties(image: Image.Image) -> None:
    print("-" * 50)
    print("Image properties")
    print("-" * 50)
    print(f"{'Format':<17} {image.format}")
    print(f"{'Size':<17} {image.size}")
    print(f"{'Width':<17} {image.width}")
    print(f"{'Height':<17} {image.height}")
    print(f"{'Palette':<17} {image.palette}")
    print(f"{'Mode':<17} {image.mode}")
    is_animated = getattr(image, "is_animated", False)
    print(f"{'Is animated':<17} {is_animated}")
    frame_count = getattr(image, "n_frames", 1)
    print(f"{'Frames':<17} {frame_count}")


def display_exif_metadata(image: Image.Image) -> None:
    print("-" * 50)
    print("EXIF metadata")
    print("-" * 50)


def process_file(path: Path) -> bool:
    if not path.exists():
        print(f"file does not exist: {path}", file=sys.stderr)
        return False

    if not path.is_file():
        print(f"path is not a file: {path}", file=sys.stderr)
        return False

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"unsupported file format: {path.suffix or '<none>'}", file=sys.stderr)
        return False

    try:
        display_filesystem_metadata(path)
        with Image.open(path) as image:
            display_image_properties(image)
            display_exif_metadata(image)
            print("-" * 50)


    except OSError as error:
        print(f"cannot open file {path}: {error}", file=sys.stderr)
        return False

    return True


def main(argv: Optional[list[str]] = None) -> int:
    paths = parse_args(argv)
    all_succeeded = True
    for path in paths:
        if not process_file(path):
            all_succeeded = False
    if all_succeeded:
        return 0
    else:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
