## The first recursive pattern: depth-first traversal.

Later I replaced depth-first recursive traversal descriptions with BFS queue behavior.

spider
├── imports
├── configuration definition
├── CrawlState definition
├── parse_args()
├── normalize_url()
├── fetch_page()
├── parse_html()
├── download_image()
├── crawl()
└── main()

A configuration object:
- `start_url` - the starting page; its crawl depth is 0.
- `allowed_domain` - the domain boundary for recursive crawling, derived from `start_url`. Hostnames under the same base domain are allowed; for example, `example.com`, `www.example.com`, and `cdn.example.com` are treated as belonging to the same domain.
- `recursive` bool - whether recursive crawling is enabled. If no `-r` argument is provided, process only the starting page.
- `max_recurs_depth` - maximum crawl depth when recursion is enabled. The default value is 5 and it can be set by `-r -l [N]`.
- `path` - a string. it has a default value `./data/` but also it can be specified.

`CrawlState` is runtime state for one execution:
- `visited_urls` - a set of normalized page URLs already processed. It is shared by all recursive calls.
- `successful_page_requests` - count of successful page requests.
- `failed_page_requests` - count of failed page requests.
- `downloaded_images` - count of successfully saved images.
- `failed_downloads` - count of images that could not be saved.

```python
    from dataclasses import dataclass, field

    @dataclass
    class CrawlState:
        visited_urls: set[str] = field(default_factory=set)
        successful_page_requests: int = 0
        failed_page_requests: int = 0
        downloaded_images: int = 0
        failed_downloads: int = 0
```

I want to have such funcions.

- `main` - entry point. Only coordinates the application: parse command-line arguments, build the configuration, handle only top-level application errors.

    - `parse_args` - parsing and and validate command-line arguments, error handling of the wrong type of the arguments.
        - It should validate that a URL is provided and call `normalize_url` for the starting URL. Normalization prevents equivalent URLs from being crawled repeatedly: https://example.com/page and https://example.com/page#section. The fragment #section does not identify a different HTTP document, so it should usually be removed.
        - `-l` is an integer,
        - recursion depth is non-negative,
        - `-p` specifies the output directory, using `./data/` when omitted,
        - `-l` is used with `-r`; without `-r`, only the starting page is processed and no links are followed.
    
    The function should **return** parsed configuration `config`.

    -  Create the runtime state object after parsing the arguments. `CrawlState` is a class, and `CrawlState()` creates an object.

    - `normalize_url` - return a canonical absolute URL for comparisons and requests. Remove the fragment, and ensure the URL has a supported HTTP scheme. Use it for the starting URL and for links after resolving them with `urljoin`.

    - `crawl(current_url, current_depth, config, state, parent_dir)` - Process one page and recursively crawl links.

    First call:  `crawl(config.start_url, 0, config, state, config.path)`

    1. If recursion is disabled, process only the initial URL. Otherwise, check the depth limit using `max_recurs_depth`. The initial call starts at `current_depth` 0. Stop when `current_depth > max_recurs_depth`.
    
       `config.start_url` has already been normalized by `parse_args`. Every recursive call receives a URL that was resolved and normalized by `parse_html`, so `crawl` does not repeat normalization.
    
    2. Check its domain. Continue only if the normalized `current_url` belongs to the `allowed_domain` domain. Stop if it is outside the allowed domain.

    3. Stop if already visited. Check whether `current_url` is in `visited_urls`; if it is not, add it before making the request. This prevents circular links from causing repeated requests.

    4. `fetch_page()` - perform the HTTP request, set a timeout and handle HTTP/network errors. Check the status code of the response to the URL: if it is not a 2xx code, display an error with the status code; if it is a 2xx response with a body, send the body to the next function for parsing. Updates the request counters in `CrawlState` object.

    5. `parse_html()` - Extract image sources and page links. It receives HTML content and the current page URL. The current page URL is needed to resolve relative links.
    
    It should extract: image `src` values and anchor `href` values.

    This function uses Beautiful Soup to parse the HTML page. It searches for all `<img>` elements and links to the `src` of these images. It should return structured results, such as a collection of image sources and page links. It should not itself perform network requests, downloads, or domain filtering.

    Every returned image source is passed to `download_image()` function. This function does not create directories.

    For each anchor link, first resolve the possibly relative `href` with `urljoin(current_url, href)`, then call `normalize_url` on the resulting absolute URL. Return these normalized page links to `crawl`; `crawl` performs the domain check. This keeps URL conversion separate from crawl policy.

    6. Create the sub-directory in `crawl()`.

        After `fetch_page()` succeeds and `parse_html()` returns its results, `crawl()` checks whether the page contains at least one supported image source. The starting page (depth 0) uses `config.path` directly. For a page at depth greater than 0 with supported images, `crawl()` creates a sub-directory inside the current `parent_dir`. This happens before calling `download_image()` and before recursively crawling the page links.

        If the page has no supported image sources, `crawl()` does not create a sub-directory. Its child pages continue to use the current `parent_dir`. The starting page is an exception: `config.path` is the root directory and its images are saved directly there.

        ```python
        current_dir = parent_dir

        if current_depth > 0 and has_supported_images(image_sources):
            current_dir = create_subdirectory(parent_dir, current_depth)
        ```

    7. `download_image()`.

        - For each image source returned by `parse_html`, this function takes the current page URL and image source as arguments, then resolves the source with `urljoin`.
        - Validate the image URL and extension. We are interested in the images with such extenstions - `.jpg/jpeg`, `.png`, `.gif`, `.bmp`.
        - Request the binary content. Handle HTTP and network errors, and count unsuccessful image requests as failed downloads.
        - Save the image in the output directory created and provided by `crawl()`. If `crawl()` cannot create a directory because the `a`-to-`z` limit was reached, it does not call `download_image()` for that page.
        - Choose a safe output filename. Two different URLs may have the same basename, such as `logo.png`; avoid overwriting an existing file by appending a timestamp to each file to create a unique name.
        - Write the response bytes. (Save as a file) 
        - Image file-save success and failures are counted in `downloaded_images` and `failed_downloads` respectively.

    8. Continue crawling. If recursive crawling is enabled, iterate over the normalized page links returned by `parse_html`.

    ```python
    for link in links:
        crawl(link, current_depth + 1, config, state, current_dir)
    ```

## Folder structure

1. Represent the structure as a recursive relationship:

root/
├── page-1a/
│   ├── image-1.jpg
│   └── page-2a/
│       └── image-2.png
└── page-1b/

The name of the folder represents the level of the recursive call: **depth + letter**. For example, `page-1a` is a qualifying page at depth 1 and `page-2a` is a qualifying child at depth 2. The letter identifies the qualifying child order under the same parent: `a`, `b`, `c`, and so on.

Only letters from `a` through `z` are available for children of one parent. If no folder name is available after `z`, do not create a directory, print a message, and continue crawling the page links without saving that page’s images.

config.path is the root directory, and the starting page saves directly there.

2. Create the subdirectory inside crawl(). 

The directory decision belongs to crawl() because only crawl() knows whether the page request succeeded, whether the page contains images, and where the page sits in the recursion tree.

3. Define the no-images behavior

If a successful page has no supported images:

root/
└── page-with-images/
    └── child-with-images/

My desired folder structure treats links **according to their relationship to the start page**:

start
├── about-us  -> page-1a
└── events    -> page-1b

Expected behavior: direct links from the same page should be siblings.

The no-image page should not create a directory. Its children should be placed under the nearest qualifying ancestor.
