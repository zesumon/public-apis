#!/usr/bin/env python3
"""Script to validate URLs in the README.md file.

Checks that all API links in the README are reachable and returns
a non-error HTTP status code.
"""

import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests

README_PATH = "README.md"
TIMEOUT = 10  # seconds
MAX_WORKERS = 10
RETRY_COUNT = 2
SLEEP_BETWEEN_RETRIES = 2  # seconds

# Status codes that are considered acceptable (not broken links)
ACCEPTABLE_STATUS_CODES = {
    200, 201, 204, 301, 302, 307, 308, 401, 403, 405, 429
}


def extract_urls(filepath: str) -> list[str]:
    """Extract all URLs from a markdown file."""
    url_pattern = re.compile(
        r'https?://[^\s\)\]\>"]+',
        re.IGNORECASE
    )
    urls = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        urls = url_pattern.findall(content)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    return list(set(urls))  # deduplicate


def check_url(url: str) -> tuple[str, Optional[int], bool]:
    """Check if a URL is reachable.

    Returns:
        A tuple of (url, status_code, is_valid)
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; public-apis-validator/1.0; "
            "+https://github.com/public-apis/public-apis)"
        )
    }
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.head(
                url,
                timeout=TIMEOUT,
                headers=headers,
                allow_redirects=True,
            )
            if response.status_code == 405:
                # HEAD not allowed, try GET
                response = requests.get(
                    url,
                    timeout=TIMEOUT,
                    headers=headers,
                    allow_redirects=True,
                )
            is_valid = response.status_code in ACCEPTABLE_STATUS_CODES
            return url, response.status_code, is_valid
        except requests.exceptions.Timeout:
            if attempt < RETRY_COUNT - 1:
                time.sleep(SLEEP_BETWEEN_RETRIES)
            else:
                return url, None, False
        except requests.exceptions.ConnectionError:
            if attempt < RETRY_COUNT - 1:
                time.sleep(SLEEP_BETWEEN_RETRIES)
            else:
                return url, None, False
        except requests.exceptions.RequestException as e:
            print(f"  [WARN] Request exception for {url}: {e}")
            return url, None, False
    return url, None, False


def validate_links(filepath: str) -> bool:
    """Validate all links found in the given markdown file.

    Returns:
        True if all links are valid, False otherwise.
    """
    print(f"Extracting URLs from '{filepath}'...")
    urls = extract_urls(filepath)
    print(f"Found {len(urls)} unique URLs. Checking...\n")

    broken = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}
        for future in as_completed(futures):
            url, status_code, is_valid = future.result()
            status_display = str(status_code) if status_code else "N/A"
            if is_valid:
                print(f"  [OK]     {status_display}  {url}")
            else:
                print(f"  [BROKEN] {status_display}  {url}")
                broken.append((url, status_code))

    print(f"\n--- Results ---")
    print(f"Total URLs checked : {len(urls)}")
    print(f"Broken links found : {len(broken)}")

    if broken:
        print("\nBroken links:")
        for url, code in broken:
            print(f"  - {url} (status: {code})")
        return False

    print("All links are valid!")
    return True


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else README_PATH
    success = validate_links(filepath)
    sys.exit(0 if success else 1)
