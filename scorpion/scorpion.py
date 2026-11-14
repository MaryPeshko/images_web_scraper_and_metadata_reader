import argparse
import sys
from pathlib import Path
from typing import Optional

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
        with path.open("rb") as file:
            data = file.read()
    except OSError as error:
        print(f"cannot open file {path}: {error}", file=sys.stderr)
        return False

    print(f"read {len(data)} bytes from {path}")
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
