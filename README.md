Help

```bash
python3 spider.py --help
```

Install dependency

```bash
python3 -m pip install -r requirements.txt
```

Added:

- recursive `page-depth-letter` directories;
    - `a`–`z` sibling limit;
- Beautiful Soup HTML parsing;
- crawl/download statistics;

Run it with:

```bash
# no options
python3 spider.py https://example.com
# with options
python3 spider.py -r -l 5 -p ./data/ https://example.com
```


---

**USER_AGENT header**

A custom user agent is useful for transparency, server-side logging, debugging, and complying with crawler policies. It does not bypass access controls or guarantee that a request will be accepted.

If no `User-Agent` header is specified, Python’s `urllib` usually sends its own default identity, such as: `Python-urllib/3.x`

---

The help output is generated dynamically by Python’s standard-library `argparse` module.

---



