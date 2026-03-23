#!/usr/bin/env python3
"""
Pocket Alexandria - Discovery Engine
Scrapes Project Gutenberg and Sacred-Texts.com for new public domain texts
matching our esoteric/philosophical categories.

Usage:
    python discovery.py scrape-gutenberg   # Find new books on Gutenberg
    python discovery.py scrape-sacred      # Find new books on Sacred-Texts
    python discovery.py classify           # Classify discovered books
    python discovery.py add-all            # Add all discoveries to catalog
"""

import os
import re
import csv
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import track
    from rich import box
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(BASE_DIR, "books_metadata.csv")
DISCOVERIES_PATH = os.path.join(BASE_DIR, "data", "discoveries.json")

HEADERS = {
    "User-Agent": "PocketAlexandria/1.0 (Digital Library Discovery; contact@pocketalexandria.org)"
}

# Gutenberg subject keywords that match our categories
GUTENBERG_SUBJECTS = {
    "Sacred Texts": [
        "Bible", "Quran", "Koran", "Religious texts", "Sacred books",
        "Vedas", "Upanishads", "Buddhism", "Hinduism",
    ],
    "Hermetic / Occult": [
        "Occultism", "Hermetism", "Theosophy", "Magic", "Kabbalah",
        "Alchemy", "Mysticism", "Rosicrucianism", "Freemasonry",
        "Hermetic", "Esoteric",
    ],
    "Philosophy": [
        "Philosophy", "Ethics", "Metaphysics", "Stoicism",
        "Existentialism", "Political philosophy", "Epistemology",
        "Logic", "Aesthetics",
    ],
    "Psychology": [
        "Psychology", "Psychoanalysis", "Psychiatry",
        "Social psychology", "Crowd psychology",
    ],
    "Astrology / Divination": [
        "Astrology", "Divination", "Prophecies", "Tarot",
        "Fortune-telling", "Oracles",
    ],
    "Apocrypha": [
        "Apocryphal books", "Gnostic", "Dead Sea scrolls",
        "Pseudepigrapha", "Nag Hammadi",
    ],
    "Eastern Wisdom": [
        "Taoism", "Confucianism", "Zen", "Bushido", "Martial arts",
        "Yoga", "Meditation",
    ],
    "Forbidden / Controversial": [
        "Banned books", "Censorship", "Political science",
        "Revolution", "Anarchism", "Utopias",
    ],
    "Alchemy / Mysticism": [
        "Alchemy", "Mysticism", "Spiritual life",
        "Contemplation", "Asceticism",
    ],
    "Secret Societies": [
        "Freemasonry", "Illuminati", "Secret societies",
        "Rosicrucians", "Knights Templar",
    ],
}


def load_discoveries():
    """Load previously discovered books."""
    if os.path.exists(DISCOVERIES_PATH):
        with open(DISCOVERIES_PATH, 'r') as f:
            return json.load(f)
    return []


def save_discoveries(discoveries):
    """Save discoveries to file."""
    os.makedirs(os.path.dirname(DISCOVERIES_PATH), exist_ok=True)
    with open(DISCOVERIES_PATH, 'w') as f:
        json.dump(discoveries, f, indent=2)


def scrape_gutenberg():
    """
    Search Project Gutenberg for books matching our categories.
    Uses the Gutenberg search API and catalog.
    """
    if not HAS_BS4:
        print("ERROR: BeautifulSoup4 required. Run: pip install beautifulsoup4")
        return []

    discoveries = load_discoveries()
    existing_urls = set(d['url'] for d in discoveries)
    new_finds = []

    print("Searching Project Gutenberg...")

    for category, keywords in GUTENBERG_SUBJECTS.items():
        for keyword in keywords:
            try:
                time.sleep(2)  # Rate limiting
                search_url = f"https://www.gutenberg.org/ebooks/search/?query={keyword.replace(' ', '+')}&submit_search=Go%21"

                if HAS_RICH:
                    console.print(f"  [dim]Searching: {keyword}...[/dim]")
                else:
                    print(f"  Searching: {keyword}...")

                response = requests.get(search_url, headers=HEADERS, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Parse search results
                for item in soup.select('.booklink'):
                    title_el = item.select_one('.title')
                    author_el = item.select_one('.subtitle')
                    link_el = item.select_one('a')

                    if not title_el or not link_el:
                        continue

                    title = title_el.get_text(strip=True)
                    author = author_el.get_text(strip=True) if author_el else "Unknown"
                    href = link_el.get('href', '')

                    # Extract ebook ID
                    match = re.search(r'/ebooks/(\d+)', href)
                    if not match:
                        continue

                    ebook_id = match.group(1)
                    txt_url = f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"

                    if txt_url in existing_urls:
                        continue

                    discovery = {
                        'title': title,
                        'author': author,
                        'year': 0,
                        'category': category,
                        'subcategory': keyword,
                        'url': txt_url,
                        'source': 'gutenberg',
                        'ebook_id': ebook_id,
                        'description': f"Discovered via Gutenberg search for '{keyword}'",
                        'discovered_at': datetime.now().isoformat(),
                        'verified': False,
                    }

                    new_finds.append(discovery)
                    existing_urls.add(txt_url)

            except requests.RequestException as e:
                print(f"  Warning: Failed to search '{keyword}': {e}")
            except Exception as e:
                print(f"  Warning: Error processing '{keyword}': {e}")

    # Save all discoveries
    discoveries.extend(new_finds)
    save_discoveries(discoveries)

    if HAS_RICH:
        console.print(f"\n[bold green]Found {len(new_finds)} new texts on Gutenberg[/bold green]")
    else:
        print(f"\nFound {len(new_finds)} new texts on Gutenberg")

    return new_finds


def scrape_sacred_texts():
    """
    Scrape Sacred-Texts.com for esoteric texts.
    The site is organized by tradition/category.
    """
    if not HAS_BS4:
        print("ERROR: BeautifulSoup4 required. Run: pip install beautifulsoup4")
        return []

    discoveries = load_discoveries()
    existing_urls = set(d['url'] for d in discoveries)
    new_finds = []

    # Sacred-texts.com category pages
    sacred_categories = {
        "Hermetic / Occult": [
            "https://sacred-texts.com/eso/index.htm",
            "https://sacred-texts.com/grim/index.htm",
        ],
        "Alchemy / Mysticism": [
            "https://sacred-texts.com/alc/index.htm",
        ],
        "Sacred Texts": [
            "https://sacred-texts.com/bib/index.htm",
            "https://sacred-texts.com/hin/index.htm",
            "https://sacred-texts.com/bud/index.htm",
            "https://sacred-texts.com/isl/index.htm",
            "https://sacred-texts.com/egy/index.htm",
        ],
        "Apocrypha": [
            "https://sacred-texts.com/gno/index.htm",
            "https://sacred-texts.com/chr/apo/index.htm",
        ],
        "Secret Societies": [
            "https://sacred-texts.com/mas/index.htm",
            "https://sacred-texts.com/sro/index.htm",
        ],
        "Astrology / Divination": [
            "https://sacred-texts.com/astro/index.htm",
            "https://sacred-texts.com/tarot/index.htm",
        ],
        "Eastern Wisdom": [
            "https://sacred-texts.com/tao/index.htm",
            "https://sacred-texts.com/cfu/index.htm",
            "https://sacred-texts.com/shi/index.htm",
        ],
    }

    print("Searching Sacred-Texts.com...")

    for category, urls in sacred_categories.items():
        for page_url in urls:
            try:
                time.sleep(2)

                if HAS_RICH:
                    console.print(f"  [dim]Scanning: {page_url}...[/dim]")
                else:
                    print(f"  Scanning: {page_url}...")

                response = requests.get(page_url, headers=HEADERS, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find links to texts
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)

                    # Skip navigation links and non-text links
                    if not text or len(text) < 5:
                        continue
                    if href.startswith('#') or href.startswith('http') and 'sacred-texts.com' not in href:
                        continue
                    if href.endswith('.jpg') or href.endswith('.gif') or href.endswith('.png'):
                        continue

                    # Build full URL
                    if not href.startswith('http'):
                        from urllib.parse import urljoin
                        full_url = urljoin(page_url, href)
                    else:
                        full_url = href

                    if full_url in existing_urls:
                        continue

                    # Only include actual text pages (not index pages)
                    if '/index.htm' in full_url:
                        continue

                    discovery = {
                        'title': text[:100],
                        'author': 'Various',
                        'year': 0,
                        'category': category,
                        'subcategory': '',
                        'url': full_url,
                        'source': 'sacred-texts',
                        'description': f"Discovered on Sacred-Texts.com",
                        'discovered_at': datetime.now().isoformat(),
                        'verified': False,
                    }

                    new_finds.append(discovery)
                    existing_urls.add(full_url)

            except requests.RequestException as e:
                print(f"  Warning: Failed to scan '{page_url}': {e}")
            except Exception as e:
                print(f"  Warning: Error processing '{page_url}': {e}")

    discoveries.extend(new_finds)
    save_discoveries(discoveries)

    if HAS_RICH:
        console.print(f"\n[bold green]Found {len(new_finds)} new texts on Sacred-Texts[/bold green]")
    else:
        print(f"\nFound {len(new_finds)} new texts on Sacred-Texts")

    return new_finds


def classify_discoveries():
    """
    Classify and verify discovered texts.
    Uses heuristic matching to assign proper categories and descriptions.
    Falls back to keyword-based classification.
    """
    discoveries = load_discoveries()
    unverified = [d for d in discoveries if not d.get('verified')]

    if not unverified:
        print("No unverified discoveries to classify.")
        return

    print(f"Classifying {len(unverified)} discoveries...\n")

    # Keyword-based classifier
    CATEGORY_KEYWORDS = {
        "Sacred Texts": ["bible", "quran", "scripture", "gospel", "psalm", "testament", "vedic", "sutra", "dharma"],
        "Hermetic / Occult": ["hermetic", "occult", "magic", "theosophy", "blavatsky", "crowley", "ritual", "grimoire"],
        "Philosophy": ["philosophy", "ethics", "plato", "aristotle", "stoic", "nietzsche", "metaphysics", "epistemology"],
        "Psychology": ["psychology", "freud", "jung", "unconscious", "psychoanalysis", "behavior", "mind"],
        "Astrology / Divination": ["astrology", "tarot", "divination", "horoscope", "zodiac", "oracle", "prophecy"],
        "Apocrypha": ["apocrypha", "gnostic", "nag hammadi", "pseudepigrapha", "enoch", "gospel of"],
        "Eastern Wisdom": ["tao", "confuci", "zen", "bushido", "samurai", "yoga", "buddha", "dharma"],
        "Alchemy / Mysticism": ["alchemy", "alchemist", "mystic", "contemplat", "transmut", "elixir"],
        "Secret Societies": ["freemason", "masonic", "rosicrucian", "illuminati", "templar", "secret societ"],
        "Forbidden / Controversial": ["banned", "censored", "revolution", "anarchi", "radical", "heresy"],
    }

    classified = 0
    for disc in unverified:
        title_lower = disc['title'].lower()
        desc_lower = disc.get('description', '').lower()
        combined = title_lower + ' ' + desc_lower

        best_category = disc.get('category', 'Uncategorized')
        best_score = 0

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_category = category

        disc['category'] = best_category
        disc['verified'] = True
        classified += 1

    save_discoveries(discoveries)
    print(f"Classified {classified} discoveries.")


def add_discoveries_to_catalog():
    """Add verified discoveries to the main catalog CSV."""
    discoveries = load_discoveries()
    verified = [d for d in discoveries if d.get('verified')]

    if not verified:
        print("No verified discoveries to add. Run 'classify' first.")
        return

    # Load existing catalog URLs
    existing_urls = set()
    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row.get('url', '').strip())

    # Add new entries
    added = 0
    with open(CATALOG_PATH, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for disc in verified:
            if disc['url'] not in existing_urls:
                writer.writerow([
                    disc['title'],
                    disc['author'],
                    disc.get('year', 0),
                    disc['category'],
                    disc.get('subcategory', ''),
                    disc['url'],
                    disc.get('description', ''),
                ])
                existing_urls.add(disc['url'])
                added += 1

    # Reload into database
    db.load_catalog_to_db(CATALOG_PATH)

    if HAS_RICH:
        console.print(f"\n[bold green]Added {added} new texts to the catalog[/bold green]")
    else:
        print(f"\nAdded {added} new texts to the catalog")


def show_discoveries():
    """Show all discovered texts."""
    discoveries = load_discoveries()

    if not discoveries:
        print("No discoveries yet. Run 'scrape-gutenberg' or 'scrape-sacred' first.")
        return

    if HAS_RICH:
        table = Table(title=f"Discoveries ({len(discoveries)} texts)", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold", max_width=40)
        table.add_column("Category", style="magenta")
        table.add_column("Source", style="dim")
        table.add_column("Verified", justify="center")

        for i, d in enumerate(discoveries[:50], 1):
            verified = "[green]Yes[/green]" if d.get('verified') else "[red]No[/red]"
            table.add_row(str(i), d['title'][:40], d['category'], d['source'], verified)

        console.print(table)
        if len(discoveries) > 50:
            console.print(f"[dim]Showing 50 of {len(discoveries)} discoveries[/dim]")
    else:
        print(f"\nDiscoveries ({len(discoveries)} texts):\n")
        for i, d in enumerate(discoveries[:50], 1):
            v = "*" if d.get('verified') else " "
            print(f"  [{v}] {i}. {d['title'][:40]} | {d['category']} | {d['source']}")


def main():
    parser = argparse.ArgumentParser(description="Pocket Alexandria - Discovery Engine")
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('scrape-gutenberg', help='Search Project Gutenberg')
    subparsers.add_parser('scrape-sacred', help='Search Sacred-Texts.com')
    subparsers.add_parser('classify', help='Classify discovered texts')
    subparsers.add_parser('add-all', help='Add discoveries to catalog')
    subparsers.add_parser('show', help='Show all discoveries')
    subparsers.add_parser('scrape-all', help='Run all scrapers')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    db.init_db()

    if args.command == 'scrape-gutenberg':
        scrape_gutenberg()
    elif args.command == 'scrape-sacred':
        scrape_sacred_texts()
    elif args.command == 'classify':
        classify_discoveries()
    elif args.command == 'add-all':
        add_discoveries_to_catalog()
    elif args.command == 'show':
        show_discoveries()
    elif args.command == 'scrape-all':
        scrape_gutenberg()
        scrape_sacred_texts()
        classify_discoveries()
        print("\nDone! Run 'python discovery.py add-all' to add discoveries to catalog.")


if __name__ == "__main__":
    main()
