"""
Pocket Alexandria - Book Downloader
Downloads all books from the catalog, handles multiple formats,
extracts text, and builds the search index.
"""

import os
import re
import csv
import time
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(BASE_DIR, "books")
CATALOG_PATH = os.path.join(BASE_DIR, "books_metadata.csv")

HEADERS = {
    "User-Agent": "PocketAlexandria/1.0 (Digital Library Project; contact@pocketalexandria.org)"
}

# Rate limiting
REQUEST_DELAY = 1.0  # seconds between requests to same domain
_last_request_time = {}


def rate_limit(url):
    """Respect rate limits per domain."""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    now = time.time()
    if domain in _last_request_time:
        elapsed = now - _last_request_time[domain]
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time[domain] = time.time()


def sanitize_filename(name):
    """Create a safe filename from a title."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:80].strip('_')


def detect_format(url, content_type=None):
    """Detect file format from URL or content type."""
    url_lower = url.lower()
    if '.epub' in url_lower:
        return 'epub'
    elif '.pdf' in url_lower:
        return 'pdf'
    elif url_lower.endswith('.htm') or url_lower.endswith('.html'):
        return 'html'
    elif '.txt' in url_lower:
        return 'txt'
    elif content_type:
        if 'epub' in content_type:
            return 'epub'
        elif 'pdf' in content_type:
            return 'pdf'
        elif 'html' in content_type:
            return 'html'
        elif 'text/plain' in content_type:
            return 'txt'
    return 'txt'


def extract_text_from_html(content):
    """Extract readable text from HTML content."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        text = soup.get_text(separator='\n')
        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        text = '\n'.join(line for line in lines if line)
        return text
    except ImportError:
        # Fallback: strip HTML tags with regex
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def extract_text_from_epub(filepath):
    """Extract text from an EPUB file."""
    try:
        import zipfile
        text_parts = []
        with zipfile.ZipFile(filepath, 'r') as z:
            for name in z.namelist():
                if name.endswith(('.html', '.xhtml', '.htm')):
                    content = z.read(name).decode('utf-8', errors='ignore')
                    text_parts.append(extract_text_from_html(content))
        return '\n\n'.join(text_parts)
    except Exception as e:
        return f"[Could not extract EPUB text: {e}]"


def download_single_book(book_row):
    """Download a single book and return status."""
    book_id = book_row['id']
    title = book_row['title']
    url = book_row['url']
    category = book_row['category']

    # Create category directory
    cat_dir = os.path.join(BOOKS_DIR, sanitize_filename(category))
    os.makedirs(cat_dir, exist_ok=True)

    try:
        rate_limit(url)

        response = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        fmt = detect_format(url, content_type)

        filename = f"{sanitize_filename(title)}.{fmt}"
        filepath = os.path.join(cat_dir, filename)

        # Save raw file
        with open(filepath, 'wb') as f:
            f.write(response.content)

        # Extract text
        text_path = os.path.join(cat_dir, f"{sanitize_filename(title)}.txt")

        if fmt == 'txt':
            text = response.content.decode('utf-8', errors='ignore')
            if filepath != text_path:
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(text)
        elif fmt == 'html' or fmt == 'htm':
            text = extract_text_from_html(response.content.decode('utf-8', errors='ignore'))
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
        elif fmt == 'epub':
            text = extract_text_from_epub(filepath)
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)
        else:
            text = response.content.decode('utf-8', errors='ignore')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text)

        file_size = os.path.getsize(filepath)
        word_count = len(text.split())

        # Update database
        db.mark_downloaded(book_id, text_path, file_size, word_count)

        # Build search index
        db.build_search_index(book_id, text)

        return {
            'status': 'success',
            'title': title,
            'size': file_size,
            'words': word_count,
            'format': fmt,
        }

    except requests.exceptions.HTTPError as e:
        return {'status': 'error', 'title': title, 'error': f"HTTP {e.response.status_code}"}
    except requests.exceptions.Timeout:
        return {'status': 'error', 'title': title, 'error': "Timeout"}
    except requests.exceptions.ConnectionError:
        return {'status': 'error', 'title': title, 'error': "Connection failed"}
    except Exception as e:
        return {'status': 'error', 'title': title, 'error': str(e)[:100]}


def download_all(max_workers=3, category=None, force=False):
    """Download all books from the catalog."""
    # Ensure catalog is loaded
    db.init_db()
    count = db.load_catalog_to_db(CATALOG_PATH)
    if count > 0:
        print(f"  Loaded {count} new books into database")

    books = db.get_all_books(category=category)
    if not force:
        books = [b for b in books if not b['downloaded']]

    if not books:
        print("All books already downloaded! Use --force to re-download.")
        return

    total = len(books)
    success = 0
    failed = 0
    results = []

    print(f"\n  Downloading {total} books...\n")

    if HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading library...", total=total)
            for book in books:
                result = download_single_book(dict(book))
                results.append(result)
                if result['status'] == 'success':
                    success += 1
                    progress.update(task, advance=1, description=f"[green]Got: {result['title'][:40]}...")
                else:
                    failed += 1
                    progress.update(task, advance=1, description=f"[red]Failed: {result['title'][:40]}...")
    elif tqdm:
        for book in tqdm(books, desc="Downloading", unit="book"):
            result = download_single_book(dict(book))
            results.append(result)
            if result['status'] == 'success':
                success += 1
            else:
                failed += 1
    else:
        for i, book in enumerate(books, 1):
            print(f"  [{i}/{total}] {book['title'][:50]}...", end=" ")
            result = download_single_book(dict(book))
            results.append(result)
            if result['status'] == 'success':
                success += 1
                print(f"OK ({result['words']} words)")
            else:
                failed += 1
                print(f"FAILED: {result['error']}")

    # Summary
    print(f"\n  Download complete!")
    print(f"  Success: {success}/{total}")
    print(f"  Failed: {failed}/{total}")

    if failed > 0:
        print(f"\n  Failed books:")
        for r in results:
            if r['status'] == 'error':
                print(f"    - {r['title']}: {r['error']}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download Pocket Alexandria books")
    parser.add_argument("--category", help="Only download books in this category")
    parser.add_argument("--force", action="store_true", help="Re-download all books")
    parser.add_argument("--workers", type=int, default=3, help="Download concurrency")
    args = parser.parse_args()
    download_all(max_workers=args.workers, category=args.category, force=args.force)
