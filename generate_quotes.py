#!/usr/bin/env python3
"""
Pocket Alexandria - Quote Extraction Engine
Extracts the most profound, shareable quotes from each book.
Scores them for virality potential.

Usage:
    python generate_quotes.py                # Extract from all books
    python generate_quotes.py --book "Kybalion"  # Extract from specific book
    python generate_quotes.py --top 20       # Show top 20 quotes
    python generate_quotes.py --export       # Export quotes to JSON
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import track
    from rich import box
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Words that indicate profound/quotable content
POWER_WORDS = {
    # Wisdom/truth
    "truth", "wisdom", "knowledge", "understanding", "enlightenment",
    "consciousness", "awareness", "awakening", "illumination",
    # Spiritual
    "soul", "spirit", "divine", "sacred", "eternal", "infinite",
    "transcend", "transcendence", "immortal", "celestial",
    # Power/mastery
    "power", "master", "mastery", "strength", "courage", "will",
    "discipline", "virtue", "excellence", "greatness",
    # Mystery/depth
    "mystery", "secret", "hidden", "ancient", "forbidden",
    "profound", "deep", "essence", "nature", "reality",
    # Transformation
    "transform", "transmute", "evolve", "become", "create",
    "manifest", "destiny", "purpose", "path", "journey",
    # Universal principles
    "universe", "cosmos", "law", "principle", "harmony",
    "balance", "order", "chaos", "unity", "duality",
    # Human nature
    "mind", "heart", "desire", "fear", "love", "death",
    "life", "freedom", "suffering", "happiness", "peace",
}

# Patterns that suggest a quotable sentence
QUOTE_PATTERNS = [
    r"^[A-Z][^.!?]*(?:is|are|was|shall|must|will)[^.!?]*[.!?]$",  # Declarative truths
    r"^(?:He|She|They|The|All|No|Every|True|Real)[^.!?]*[.!?]$",  # Universal statements
    r"^(?:Know|Remember|Consider|Behold|Understand|Seek|Let)[^.!?]*[.!?]$",  # Imperatives
]


def score_quote(text):
    """
    Score a quote for virality potential (0-100).
    Higher = more shareable.
    """
    score = 0.0
    words = text.lower().split()
    word_count = len(words)

    # Length sweet spot (15-40 words is ideal for sharing)
    if 15 <= word_count <= 40:
        score += 20
    elif 10 <= word_count <= 50:
        score += 10
    elif word_count < 8 or word_count > 80:
        score -= 10

    # Power word density
    power_count = sum(1 for w in words if w.strip('.,;:!?"\'') in POWER_WORDS)
    power_density = power_count / max(1, word_count)
    score += min(30, power_density * 150)

    # Starts with a strong opening
    first_word = words[0] if words else ""
    strong_openers = {"the", "all", "no", "every", "true", "he", "she", "know",
                      "when", "there", "what", "those", "it", "man", "life"}
    if first_word.strip('.,;:!?"\'') in strong_openers:
        score += 5

    # Contains a contrast or paradox (very shareable)
    contrast_words = {"but", "yet", "however", "although", "despite", "not", "neither", "nor"}
    if any(w in contrast_words for w in words):
        score += 10

    # Contains a question (engaging)
    if text.strip().endswith('?'):
        score += 5

    # Proper sentence structure
    if text[0].isupper() and text.strip()[-1] in '.!?':
        score += 5

    # No obvious metadata/noise
    noise_words = {"chapter", "page", "vol", "section", "footnote", "ibid", "op. cit."}
    if any(w in noise_words for w in words):
        score -= 30

    # Readability - not too many complex/long words
    long_words = sum(1 for w in words if len(w) > 12)
    if long_words > word_count * 0.3:
        score -= 10

    return max(0, min(100, score))


def extract_quotes_from_text(text, max_quotes=50):
    """Extract potential quotes from a text."""
    quotes = []

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for sentence in sentences:
        sentence = sentence.strip()

        # Basic filters
        if len(sentence) < 30 or len(sentence) > 300:
            continue
        if not sentence[0].isupper():
            continue
        if sentence.count('\n') > 1:
            continue

        # Score it
        score = score_quote(sentence)

        if score >= 25:  # Minimum threshold
            quotes.append({
                'text': sentence,
                'score': score,
            })

    # Sort by score and return top N
    quotes.sort(key=lambda x: x['score'], reverse=True)
    return quotes[:max_quotes]


def extract_quotes_from_book(book, max_quotes=30):
    """Extract quotes from a single book."""
    if not book['file_path'] or not os.path.exists(book['file_path']):
        return []

    with open(book['file_path'], 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    if not text.strip():
        return []

    raw_quotes = extract_quotes_from_text(text, max_quotes=max_quotes)

    # Save to database
    for q in raw_quotes:
        db.add_quote(book['id'], q['text'], context=None, virality_score=q['score'])

    return raw_quotes


def extract_all(max_per_book=30):
    """Extract quotes from all downloaded books."""
    books = db.get_all_books(downloaded_only=True)

    if not books:
        print("No downloaded books found. Run 'pocket_alexandria.py download' first.")
        return

    total_quotes = 0

    if HAS_RICH:
        console.print(f"\n[bold magenta]Extracting quotes from {len(books)} books...[/bold magenta]\n")

        for book in track(books, description="Extracting quotes..."):
            quotes = extract_quotes_from_book(dict(book), max_quotes=max_per_book)
            total_quotes += len(quotes)
            if quotes:
                console.print(f"  [green]{book['title']}[/green]: {len(quotes)} quotes")
    else:
        print(f"\nExtracting quotes from {len(books)} books...\n")
        for book in books:
            quotes = extract_quotes_from_book(dict(book), max_quotes=max_per_book)
            total_quotes += len(quotes)
            if quotes:
                print(f"  {book['title']}: {len(quotes)} quotes")

    print(f"\nTotal quotes extracted: {total_quotes}")


def show_top_quotes(limit=20):
    """Display the top-scoring quotes."""
    quotes = db.get_quotes(limit=limit)

    if not quotes:
        print("No quotes found. Run 'python generate_quotes.py' to extract quotes.")
        return

    if HAS_RICH:
        console.print(f"\n[bold gold1]Top {limit} Most Shareable Quotes[/bold gold1]\n")

        for i, q in enumerate(quotes, 1):
            panel = Panel(
                f"[italic]{q['text']}[/italic]",
                title=f"[bold]#{i}[/bold] Score: {q['virality_score']:.0f}",
                subtitle=f"[cyan]{q['title']}[/cyan] by [dim]{q['author']}[/dim]",
                border_style="bright_yellow" if q['virality_score'] >= 50 else "dim",
                width=min(console.width, 90),
            )
            console.print(panel)
    else:
        print(f"\nTop {limit} Quotes:\n")
        for i, q in enumerate(quotes, 1):
            print(f"  {i}. [{q['virality_score']:.0f}] \"{q['text'][:120]}...\"")
            print(f"     -- {q['title']} by {q['author']}")
            print()


def export_quotes(output_path=None):
    """Export all quotes to JSON."""
    quotes = db.get_quotes(limit=1000)

    if not quotes:
        print("No quotes to export.")
        return

    if not output_path:
        output_path = os.path.join(BASE_DIR, "data", "quotes_export.json")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    export_data = [
        {
            'text': q['text'],
            'book': q['title'],
            'author': q['author'],
            'virality_score': q['virality_score'],
        }
        for q in quotes
    ]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(export_data)} quotes to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract quotes from the library")
    parser.add_argument('--book', help='Extract from a specific book (title search)')
    parser.add_argument('--top', type=int, default=20, help='Show top N quotes')
    parser.add_argument('--export', action='store_true', help='Export quotes to JSON')
    parser.add_argument('--max-per-book', type=int, default=30, help='Max quotes per book')

    args = parser.parse_args()
    db.init_db()

    if args.export:
        export_quotes()
    elif args.book:
        book = db.get_book_by_title(args.book)
        if book:
            quotes = extract_quotes_from_book(dict(book), max_quotes=args.max_per_book)
            print(f"Extracted {len(quotes)} quotes from '{book['title']}'")
            show_top_quotes(limit=args.top)
        else:
            print(f"Book not found: '{args.book}'")
    elif args.top and not args.book:
        # If quotes exist, just show them. Otherwise extract first.
        existing = db.get_quotes(limit=1)
        if existing:
            show_top_quotes(limit=args.top)
        else:
            extract_all(max_per_book=args.max_per_book)
            show_top_quotes(limit=args.top)
    else:
        extract_all(max_per_book=args.max_per_book)
        show_top_quotes(limit=args.top)


if __name__ == "__main__":
    main()
