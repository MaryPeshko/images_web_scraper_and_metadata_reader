import argparse
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MiB
MAX_IMAGE_PIXELS = 50_000_000           # 50 million pixels


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
    # image.palette is a Pillow object, not the actual color list.
    # print(f"{'Palette':<17} {image.palette}")
    if image.palette is None:
        palette_info = "None"
    else:
        palette_info = f"{len(image.palette.colors)} colors"

    print(f"{'Palette':<17} {palette_info}")
    
    print(f"{'Mode':<17} {image.mode}")
    is_animated = getattr(image, "is_animated", False)
    print(f"{'Is animated':<17} {is_animated}")
    frame_count = getattr(image, "n_frames", 1)
    print(f"{'Frames':<17} {frame_count}")


def format_gps_coordinate(
    coordinate: tuple[float, float, float],
    reference: str,
) -> str:
    degrees, minutes, seconds = coordinate
    total_minutes = float(minutes) + float(seconds) / 60
    whole_minutes = int(total_minutes)
    seconds = (total_minutes - whole_minutes) * 60
    return (
        f"{int(degrees)}°{whole_minutes:02d}'"
        f"{float(seconds):.1f}\"{reference}"
    )


def display_gps_position(gps_values: dict) -> None:
    latitude = gps_values.get("GPSLatitude")
    latitude_ref = gps_values.get("GPSLatitudeRef")
    longitude = gps_values.get("GPSLongitude")
    longitude_ref = gps_values.get("GPSLongitudeRef")
    if latitude and latitude_ref and longitude and longitude_ref:
        print(
            f"{'GPS position':<24} "
            f"{format_gps_coordinate(latitude, latitude_ref)} "
            f"{format_gps_coordinate(longitude, longitude_ref)}"
        )


def display_exif_metadata(image: Image.Image) -> None:
    print("-" * 50)
    print("EXIF metadata")
    print("-" * 50)

    if image.format == "GIF":
        print("GIF - generally does not contain EXIF metadata.")
        return

    if image.format == "BMP":
        print("BMP - generally does not contain EXIF metadata.")
        return

    exif_data = image.getexif()

    if not exif_data:
        print("No EXIF metadata found.")
        if image.info:
            print("Other image metadata found:")
            # for key, value in image.info.items():
            #     if isinstance(value, bytes):
            #         value_info = f"binary data ({len(value)} bytes)"
            #     else:
            #         value_info = value
            #     print(f"{str(key):<22} {value_info}")
            print("Additional metadata may not be fully decoded.")
            print("For a complete metadata report, use ExifTool")
            print("https://exiftool.org/")
        return

    #  top-level EXIF dictionary
    #  TAGS maps identifiers to human-readable names.
    print("_ " * 6, "top-level EXIF dictionary", "_ " * 6)
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, tag_id)
        print(f"{str(tag_name):<22} {value}")

    # nested Exif data
    ifd_exif = exif_data.get_ifd(IFD.Exif)
    print("_ " * 6, "nested Exif data", "_ " * 11)
    for tag_id, value in ifd_exif.items():
        tag_name = TAGS.get(tag_id, tag_id)
        print(f"{str(tag_name):<24} {value}")

    ifd_gps = exif_data.get_ifd(IFD.GPSInfo)
    if ifd_gps:
        print("_ " * 6, "GPS metadata", "_ " * 14)
        gps_values = {}
        for tag_id, value in ifd_gps.items():
            tag_name = GPSTAGS.get(tag_id, tag_id)
            gps_values[tag_name] = value
            print(f"{str(tag_name):<24} {value}")

        display_gps_position(gps_values)


def check_image_size(image: Image.Image) -> bool:
    pixel_count = image.width * image.height
    if pixel_count > MAX_IMAGE_PIXELS:
        print(
            f"image has too many pixels: {pixel_count} "
            f"(limit: {MAX_IMAGE_PIXELS})",
            file=sys.stderr,
        )
        return False
    return True


def process_file(path: Path, image_number: int) -> bool:
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
        # File-size check
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            print(
                f"file is too large: {file_size} bytes ",
                file=sys.stderr,
            )
            return False

        print(f"Image_{image_number} [{path.name}]")
        display_filesystem_metadata(path)
        
        # The warnings module controls non-fatal warnings raised by Python
        # and libraries such as Pillow. catch_warnings() saves the current
        # warning settings and restores them when this block ends, so our
        # filter does not affect the rest of the program.
        with warnings.catch_warnings():
            # simplefilter("error") changes this specific warning from a
            # printed warning into an exception that we can handle below.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                # Image-dimension check
                if not check_image_size(image):
                    return False
                display_image_properties(image)
                display_exif_metadata(image)
                print("-" * 50)
    except Image.DecompressionBombError as error:
        print(f"decompression bomb rejected for {path}: {error}", file=sys.stderr)
        return False
    except Image.DecompressionBombWarning as error:
        print(f"decompression bomb warning for {path}: {error}", file=sys.stderr)
        return False
    except OSError as error:
        print(f"cannot open file {path}: {error}", file=sys.stderr)
        return False

    return True


def main(argv: Optional[list[str]] = None) -> int:
    paths = parse_args(argv)
    all_succeeded = True
    image_number = 1
    for path in paths:
        if not process_file(path, image_number):
            all_succeeded = False
        image_number += 1
    if all_succeeded:
        return 0
    else:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
