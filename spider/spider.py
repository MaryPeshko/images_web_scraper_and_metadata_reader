#!/usr/bin/env python3

import argparse
import sys
import time
from collections import deque
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
    """Return a normalized HTTP(S) URL without a fragment or leading ``www.``."""
    # parsed containe the URL parts:
    # scheme    https
    # netloc    www.42berlin.de
    # path      /de/imprint

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"unsupported or invalid URL: {url}")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError(f"URL has no hostname: {url}")

    canonical_netloc = parsed.netloc
    if hostname.lower().startswith("www."):
        canonical_netloc = canonical_netloc[4:]
    canonical_path = parsed.path
    if canonical_path == "/de":
        canonical_path = "/"
    elif canonical_path.startswith("/de/"):
        canonical_path = canonical_path[3:]
    normalized = parsed._replace(
        netloc=canonical_netloc,
        path=canonical_path,
        fragment="",
    )
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

    image_path = Path(urlparse(image_url).path)
    stem = image_path.stem or "image"
    suffix = image_path.suffix.lower()
    filename = f"{stem}_{time.time_ns()}{suffix}"
    output_path = output_dir / filename
    while output_path.exists():
        filename = f"{stem}_{time.time_ns()}{suffix}"
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
    """
    BFS implementation has a for loop inside a while loop
    while pages_to_visit: keeps processing pages until the queue is empty.
    for link in links: examines every link found on the current page.
    """

    pages_to_visit: deque[tuple[str, int, Path]] = deque(
        [(current_url, current_depth, parent_dir)])
    state.visited_urls.add(current_url)

    while pages_to_visit:
        # tuple unpacking: popleft() returns one tuple from the queue from the front
        page_url, page_depth, page_parent_dir = pages_to_visit.popleft()

        if not belongs_to_allowed_domain(page_url, config.allowed_domain):
            continue

        html = fetch_page(page_url, state)
        if html is None:
            continue

        image_sources, links = parse_html(html, page_url)
        supported_images: list[str] = []
        for image_source in image_sources:
            if is_supported_image(urljoin(page_url, image_source)):
                supported_images.append(image_source)

        page_dir = page_parent_dir
        can_save_images = True
        if page_depth > 0 and supported_images:
            created_dir = create_subdirectory(
                page_parent_dir, page_depth, state
            )
            if created_dir is None:
                can_save_images = False
            else:
                page_dir = created_dir
                save_page_url(page_dir, page_url)

        if can_save_images:
            for image_source in supported_images:
                download_image(page_url, image_source, page_dir, state)

        if not config.recursive or page_depth >= config.max_recurs_depth:
            continue

        # This loop adds newly discovered pages to the end of the queue
        for link in links:
            if link in state.visited_urls:
                continue
            state.visited_urls.add(link)
            pages_to_visit.append((link, page_depth + 1, page_dir))


def main(argv: Optional[list[str]] = None) -> int:
    config = parse_args(argv)
    config.path.mkdir(parents=True, exist_ok=True)
    save_page_url(config.path, config.start_url)
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
