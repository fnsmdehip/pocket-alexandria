#!/usr/bin/env python3
"""
Pocket Alexandria - Daily Wisdom & Content Generator
Generate viral-ready content from the library for TikTok, Instagram, and Twitter.

Usage:
    python daily_wisdom.py                    # Generate today's wisdom
    python daily_wisdom.py --format tweet     # Tweet thread format
    python daily_wisdom.py --format tiktok    # TikTok caption format
    python daily_wisdom.py --format instagram # Instagram post format
    python daily_wisdom.py --format all       # All formats
    python daily_wisdom.py --batch 7          # Generate 7 days of content
    python daily_wisdom.py --theme alchemy    # Theme-specific content
"""

import os
import sys
import json
import random
import argparse
import textwrap
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich import box
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "content")

# Viral hooks / templates for different platforms
TIKTOK_HOOKS = [
    "Books they don't want you to read:",
    "This ancient text predicted everything:",
    "Hidden knowledge from {year}:",
    "The most banned book in history says:",
    "This {category} text will change how you see reality:",
    "Ancient secrets they removed from school curriculum:",
    "This {year}-year-old text knew about consciousness:",
    "Why this book was banned for centuries:",
    "The forbidden library thread you need to save:",
    "Ancient wisdom that modern science is just catching up to:",
]

INSTAGRAM_TEMPLATES = [
    "'{quote}'\n\n-- {author}, {title} ({year})\n\nThis {category} text has been hidden for centuries. {description}\n\n#HiddenKnowledge #AncientWisdom #ForbiddenBooks #{category_tag} #Esoteric #OccultKnowledge #Philosophy #SacredTexts",
    "DAILY WISDOM\n\n'{quote}'\n\n{title} by {author}\n{year} | {category}\n\nSave this. Share this. The knowledge they tried to suppress.\n\n#PocketAlexandria #HiddenLibrary #AncientTexts #{category_tag}",
    "What {author} understood in {year} that we're still learning:\n\n'{quote}'\n\nFrom: {title}\n\n{description}\n\n#WisdomDaily #Philosophy #{category_tag} #MindExpansion",
]

TWEET_TEMPLATES = [
    "'{quote}'\n\n-- {author}, {title} ({year})\n\n[Thread on why this ancient text matters] 1/",
    "Hidden wisdom from {year}:\n\n'{quote}'\n\n{title} by {author}\n\nThis is the kind of knowledge they removed from the curriculum.",
    "Read this quote from {year}. Then read it again.\n\n'{quote}'\n\n-- {author}, {title}",
]


def get_best_quote(theme=None):
    """Get the best available quote, optionally themed."""
    conn = db.get_connection()

    if theme:
        quotes = conn.execute("""
            SELECT q.*, b.title, b.author, b.year, b.category, b.description
            FROM quotes q
            JOIN books b ON q.book_id = b.id
            WHERE (LOWER(b.category) LIKE ? OR LOWER(b.title) LIKE ? OR LOWER(q.text) LIKE ?)
            AND q.virality_score >= 30
            ORDER BY q.virality_score DESC
            LIMIT 50
        """, (f"%{theme.lower()}%", f"%{theme.lower()}%", f"%{theme.lower()}%")).fetchall()
    else:
        quotes = conn.execute("""
            SELECT q.*, b.title, b.author, b.year, b.category, b.description
            FROM quotes q
            JOIN books b ON q.book_id = b.id
            WHERE q.virality_score >= 30
            ORDER BY q.virality_score DESC
            LIMIT 100
        """).fetchall()

    conn.close()

    if not quotes:
        # Fallback to random passage
        passage = db.get_random_passage()
        if passage:
            return {
                'text': passage['text'][:200],
                'title': passage['title'],
                'author': passage['author'],
                'year': 'ancient',
                'category': passage['category'],
                'description': '',
                'virality_score': 30,
            }
        return None

    # Pick a random one from the top ones
    selected = random.choice(quotes[:min(20, len(quotes))])
    return dict(selected)


def make_category_tag(category):
    """Convert category to hashtag-safe format."""
    return category.replace(' ', '').replace('/', '').replace('-', '')


def generate_tiktok_caption(quote_data):
    """Generate a TikTok-ready caption."""
    if not quote_data:
        return None

    hook = random.choice(TIKTOK_HOOKS)
    hook = hook.format(
        year=quote_data.get('year', 'ancient'),
        category=quote_data.get('category', 'ancient'),
    )

    caption = f"""{hook}

"{quote_data['text'][:200]}"

-- {quote_data['author']}, {quote_data['title']}

Follow for more hidden knowledge from the world's most suppressed texts.

#HiddenKnowledge #AncientWisdom #ForbiddenBooks #BookTok #Esoteric #{make_category_tag(quote_data.get('category', 'Philosophy'))} #DarkAcademia #Occult #Philosophy"""

    return caption


def generate_instagram_post(quote_data):
    """Generate an Instagram-ready post."""
    if not quote_data:
        return None

    template = random.choice(INSTAGRAM_TEMPLATES)
    post = template.format(
        quote=quote_data['text'][:250],
        author=quote_data['author'],
        title=quote_data['title'],
        year=quote_data.get('year', 'ancient'),
        category=quote_data.get('category', 'Philosophy'),
        category_tag=make_category_tag(quote_data.get('category', 'Philosophy')),
        description=quote_data.get('description', 'An ancient text of hidden wisdom.')[:100],
    )
    return post


def generate_tweet_thread(quote_data):
    """Generate a Twitter/X thread."""
    if not quote_data:
        return None

    template = random.choice(TWEET_TEMPLATES)
    tweet = template.format(
        quote=quote_data['text'][:200],
        author=quote_data['author'],
        title=quote_data['title'],
        year=quote_data.get('year', 'ancient'),
        category=quote_data.get('category', 'Philosophy'),
    )

    thread = [tweet]

    # Add context tweet
    thread.append(f"2/ {quote_data['title']} was written by {quote_data['author']} ({quote_data.get('year', 'date unknown')}). {quote_data.get('description', '')[:200]}")

    # Add call to action
    thread.append(f"3/ The full text is in the public domain and freely available.\n\nPocket Alexandria has curated 100+ texts like this -- sacred, philosophical, and esoteric works spanning 4000+ years.\n\nRT to spread hidden knowledge.")

    return thread


def generate_image_template(quote_data):
    """Generate a text template for creating quote images."""
    if not quote_data:
        return None

    template = {
        'quote': quote_data['text'][:200],
        'author': quote_data['author'],
        'title': quote_data['title'],
        'year': quote_data.get('year', ''),
        'category': quote_data.get('category', ''),
        'layout': {
            'background': '#0a0a0f',
            'text_color': '#e0ddd5',
            'accent_color': '#d4a853',
            'font_quote': 'Cinzel',
            'font_source': 'Crimson Text',
            'watermark': 'Pocket Alexandria',
        }
    }
    return template


def generate_daily_wisdom(format_type='all', theme=None):
    """Generate daily wisdom content."""
    quote_data = get_best_quote(theme=theme)

    if not quote_data:
        print("No quotes available. Run 'python generate_quotes.py' first.")
        return

    outputs = {}

    if format_type in ('all', 'tiktok'):
        outputs['tiktok'] = generate_tiktok_caption(quote_data)

    if format_type in ('all', 'instagram'):
        outputs['instagram'] = generate_instagram_post(quote_data)

    if format_type in ('all', 'tweet'):
        outputs['tweet'] = generate_tweet_thread(quote_data)

    if format_type in ('all', 'image'):
        outputs['image_template'] = generate_image_template(quote_data)

    # Display
    if HAS_RICH:
        console.print(Panel(
            f"[bold]{quote_data['title']}[/bold] by {quote_data['author']}",
            title="[bold gold1]Daily Wisdom Source[/bold gold1]",
            border_style="gold1",
        ))

        for platform, content in outputs.items():
            if platform == 'tweet' and isinstance(content, list):
                content = '\n\n---\n\n'.join(content)
            elif platform == 'image_template':
                content = json.dumps(content, indent=2)

            if content:
                console.print(Panel(
                    content,
                    title=f"[bold cyan]{platform.upper()}[/bold cyan]",
                    border_style="cyan",
                    width=min(console.width, 80),
                ))
    else:
        print(f"\n{'=' * 60}")
        print(f"  Daily Wisdom: {quote_data['title']} by {quote_data['author']}")
        print(f"{'=' * 60}\n")

        for platform, content in outputs.items():
            print(f"\n--- {platform.upper()} ---\n")
            if isinstance(content, list):
                for item in content:
                    print(item)
                    print()
            elif isinstance(content, dict):
                print(json.dumps(content, indent=2))
            else:
                print(content)

    return outputs


def generate_batch(count=7, format_type='all', theme=None):
    """Generate multiple days of content."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_content = []

    if HAS_RICH:
        console.print(f"\n[bold magenta]Generating {count} days of content...[/bold magenta]\n")
    else:
        print(f"\nGenerating {count} days of content...\n")

    for i in range(count):
        date = datetime.now() + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')

        quote_data = get_best_quote(theme=theme)
        if not quote_data:
            continue

        day_content = {
            'date': date_str,
            'source': {
                'title': quote_data['title'],
                'author': quote_data['author'],
                'year': quote_data.get('year', ''),
                'category': quote_data.get('category', ''),
            },
            'tiktok': generate_tiktok_caption(quote_data),
            'instagram': generate_instagram_post(quote_data),
            'tweet': generate_tweet_thread(quote_data),
            'image_template': generate_image_template(quote_data),
        }
        all_content.append(day_content)

        print(f"  Day {i+1} ({date_str}): {quote_data['title']} by {quote_data['author']}")

    # Save batch
    output_path = os.path.join(OUTPUT_DIR, f"content_batch_{datetime.now().strftime('%Y%m%d')}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_content, f, indent=2, ensure_ascii=False)

    # Also save individual plain text files for easy copy-paste
    for day in all_content:
        day_dir = os.path.join(OUTPUT_DIR, day['date'])
        os.makedirs(day_dir, exist_ok=True)

        if day.get('tiktok'):
            with open(os.path.join(day_dir, 'tiktok.txt'), 'w') as f:
                f.write(day['tiktok'])

        if day.get('instagram'):
            with open(os.path.join(day_dir, 'instagram.txt'), 'w') as f:
                f.write(day['instagram'])

        if day.get('tweet'):
            with open(os.path.join(day_dir, 'tweet_thread.txt'), 'w') as f:
                for i, tweet in enumerate(day['tweet'], 1):
                    f.write(f"--- Tweet {i} ---\n{tweet}\n\n")

        if day.get('image_template'):
            with open(os.path.join(day_dir, 'image_template.json'), 'w') as f:
                json.dump(day['image_template'], f, indent=2)

    print(f"\nContent saved to {OUTPUT_DIR}/")
    print(f"Batch file: {output_path}")

    return all_content


def main():
    parser = argparse.ArgumentParser(description="Generate daily wisdom content")
    parser.add_argument('--format', choices=['all', 'tiktok', 'instagram', 'tweet', 'image'],
                       default='all', help='Output format')
    parser.add_argument('--batch', type=int, help='Generate N days of content')
    parser.add_argument('--theme', help='Theme/topic for content')

    args = parser.parse_args()
    db.init_db()

    if args.batch:
        generate_batch(count=args.batch, format_type=args.format, theme=args.theme)
    else:
        generate_daily_wisdom(format_type=args.format, theme=args.theme)


if __name__ == "__main__":
    main()
