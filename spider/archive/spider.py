#!/usr/bin/env python3

import argparse
import sys
import time
from dataclasses import dataclass, field
# `Path` class that can make system calls. Path represents a filesystem path, it 
# also offers methods to do system calls on path objects.
from pathlib import Path 
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
REQUEST_TIMEOUT = 10
USER_AGENT = "arachnida/1.0"


@dataclass
class Configuration:
    start_url: str
    allowed_domain: str
    recursive: bool
    max_recurs_depth: int
    path: Path


@dataclass
class CrawlState:
    visited_urls: set[str] = field(default_factory=set)
    successful_page_requests: int = 0
    failed_page_requests: int = 0
    downloaded_images: int = 0
    failed_downloads: int = 0
    next_directory_letters: dict[Path, int] = field(default_factory=dict)


def normalize_url(url: str) -> str:
    """Return a normalized HTTP(S) URL without a fragment."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"unsupported or invalid URL: {url}")

    normalized = parsed._replace(fragment="")
    return urlunparse(normalized)


def base_domain(hostname: str) -> str:
    """Return the base domain used for the crawler's domain boundary."""
    parts = hostname.lower().rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname.lower().rstrip(".")


"""
description=... is a keyword argument passed to the ArgumentParser constructor.
ArgumentParser uses this description when generating command-line help.
"""
def parse_args(argv: Optional[list[str]] = None) -> Configuration:

    parser = argparse.ArgumentParser(
        description="Download images from a web page, optionally recursively."
    )
    parser.add_argument("-r", action="store_true", dest="recursive", help="recursion enabled")
    parser.add_argument("-l", type=int, dest="max_recurs_depth", default=5, help="maximum recursion depth",)
    parser.add_argument("-p", dest="path", default="./data/", help="directory where images are saved",)
    parser.add_argument("url", help="URL to crawl")
    args = parser.parse_args(argv)

    if args.max_recurs_depth < 0:
        parser.error("recursion depth must be non-negative")
    if not args.recursive and args.max_recurs_depth != 5:
        parser.error("-l can only be used with -r")

    try:
        start_url = normalize_url(args.url)
    except ValueError as error:
        parser.error(str(error))

    hostname = urlparse(start_url).hostname
    if hostname is None:
        parser.error(f"URL has no hostname: {start_url}")

    return Configuration(
        start_url=start_url,
        allowed_domain=base_domain(hostname),
        recursive=args.recursive,
        max_recurs_depth=args.max_recurs_depth,
        path=Path(args.path),
    )


def belongs_to_allowed_domain(url: str, allowed_domain: str) -> bool:
    hostname = urlparse(url).hostname
    if hostname is None:
        return False
    hostname = hostname.lower().rstrip(".")
    return hostname == allowed_domain or hostname.endswith(f".{allowed_domain}")


def fetch_page(url: str, state: CrawlState) -> Optional[str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            if not 200 <= response.status < 300:
                state.failed_page_requests += 1
                print(f"Page request failed for {url}: HTTP {response.status}", file=sys.stderr)
                return None
            body = response.read()
    except HTTPError as error:
        state.failed_page_requests += 1
        print(f"Page request failed for {url}: HTTP {error.code}", file=sys.stderr)
        return None
    except (URLError, TimeoutError, OSError) as error:
        state.failed_page_requests += 1
        print(f"Page request failed for {url}: {error}", file=sys.stderr)
        return None

    state.successful_page_requests += 1
    return body.decode("utf-8", errors="replace")


def parse_html(html: str, current_url: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    image_sources: list[str] = []
    for image in soup.find_all("img"):
        source = image.get("src")
        if source:
            image_sources.append(source)

    links: list[str] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        absolute_url = urljoin(current_url, href)
        try:
            links.append(normalize_url(absolute_url))
        except ValueError:
            continue

    return image_sources, links


def is_supported_image(image_source: str) -> bool:
    path = urlparse(image_source).path.lower()
    return Path(path).suffix in SUPPORTED_EXTENSIONS


def create_subdirectory(
        parent_dir: Path, 
        current_depth: int, 
        state: CrawlState
    ) -> Optional[Path]:

    next_letter = state.next_directory_letters.get(parent_dir, 0)
    if next_letter >= 26:
        print(
            f"Cannot create a directory under {parent_dir}: "
            "the a-z limit has been reached.",
            file=sys.stderr,
        )
        return None

    # The / operator is overloaded by Path to join paths
    directory = parent_dir / f"page-{current_depth}{chr(ord('a') + next_letter)}"
    state.next_directory_letters[parent_dir] = next_letter + 1
    directory.mkdir(parents=False, exist_ok=False)
    return directory


def save_page_url(directory: Path, page_url: str) -> None:
    try:
        (directory / "link.txt").write_text(f"{page_url}\n", encoding="utf-8")
    except OSError as error:
        print(f"Could not save page URL {directory / 'link.txt'}: {error}", file=sys.stderr)


def download_image(
    current_url: str,
    image_source: str,
    output_dir: Path,
    state: CrawlState,
) -> None:
    image_url = urljoin(current_url, image_source)
    try:
        image_url = normalize_url(image_url)
    except ValueError:
        state.failed_downloads += 1
        print(f"Invalid image URL: {image_url}", file=sys.stderr)
        return

    if not is_supported_image(image_url):
        return

    request = Request(image_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            if not 200 <= response.status < 300:
                raise OSError(f"HTTP {response.status}")
            content = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        state.failed_downloads += 1
        print(f"Image download failed for {image_url}: {error}", file=sys.stderr)
        return

    suffix = Path(urlparse(image_url).path).suffix.lower()
    filename = f"image-{time.time_ns()}{suffix}"
    output_path = output_dir / filename
    while output_path.exists():
        filename = f"image-{time.time_ns()}{suffix}"
        output_path = output_dir / filename

    try:
        output_path.write_bytes(content)
    except OSError as error:
        state.failed_downloads += 1
        print(f"Could not save image {output_path}: {error}", file=sys.stderr)
        return

    state.downloaded_images += 1


def crawl(
    current_url: str,
    current_depth: int,
    config: Configuration,
    state: CrawlState,
    parent_dir: Path,
) -> None:

    if not config.recursive and current_depth > 0:
        return
    if config.recursive and current_depth > config.max_recurs_depth:
        return
    if not belongs_to_allowed_domain(current_url, config.allowed_domain):
        return
    if current_url in state.visited_urls:
        return
    state.visited_urls.add(current_url)

    html = fetch_page(current_url, state)
    if html is None:
        return

    image_sources, links = parse_html(html, current_url)
    supported_images: list[str] = []
    for image_source in image_sources:
        if is_supported_image(urljoin(current_url, image_source)):
            supported_images.append(image_source)

    current_dir = parent_dir
    if current_depth > 0 and supported_images:
        current_dir = create_subdirectory(parent_dir, current_depth, state)
        # it returns None when it cannot create another subdirectory
        # that means all 26 directory suffixes (a through z) have already been used
        if current_dir is None:
            if config.recursive:
                for link in links:
                    crawl(link, current_depth + 1, config, state, parent_dir)
            return
        save_page_url(current_dir, current_url)

    for image_source in supported_images:
        download_image(current_url, image_source, current_dir, state)

    if config.recursive:
        for link in links:
            crawl(link, current_depth + 1, config, state, current_dir)


def main(argv: Optional[list[str]] = None) -> int:
    config = parse_args(argv)
    config.path.mkdir(parents=True, exist_ok=True)
    state = CrawlState()
    crawl(config.start_url, 0, config, state, config.path)
    print(
        f"Successful pages: {state.successful_page_requests}; "
        f"Failed pages: {state.failed_page_requests}; "
        f"Downloaded images: {state.downloaded_images}; "
        f"Failed downloads: {state.failed_downloads}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
