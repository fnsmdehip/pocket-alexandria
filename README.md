# Pocket Alexandria

**The Hidden Digital Library** -- A curated collection of 100+ esoteric, occult, philosophical, and sacred texts, all public domain.

The kind of library that goes viral as "books they don't want you to read." Ancient wisdom spanning 4000+ years, from the Epic of Gilgamesh to Crowley's Thelema, from the Kybalion to Nietzsche, from the Dead Sea Scrolls to banned revolutionary pamphlets.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# See the full catalog
python pocket_alexandria.py list

# Download all 100+ texts
python pocket_alexandria.py download

# Browse by tradition
python pocket_alexandria.py browse

# Search across all texts
python pocket_alexandria.py search "transmutation of the soul"

# Read in terminal
python pocket_alexandria.py read "Kybalion"

# Start the web reader
python pocket_alexandria.py web

# Get a random profound passage
python pocket_alexandria.py random
```

## What's Inside

| Category | Texts | Description |
|---|---|---|
| Sacred Texts | 20+ | Bible, Quran, Bhagavad Gita, Egyptian Book of the Dead, Popol Vuh |
| Hermetic / Occult | 20+ | Kybalion, Corpus Hermeticum, Golden Dawn, Crowley, Kabbalah |
| Philosophy | 20+ | Plato, Aristotle, Nietzsche, Stoics, Machiavelli, Schopenhauer |
| Psychology | 8+ | Freud, Jung, Le Bon, Crowd Psychology, Religious Experience |
| Alchemy / Mysticism | 12+ | Emerald Tablet, Boehme, Cloud of Unknowing, St. Teresa |
| Apocrypha | 10+ | Book of Enoch, Gospel of Thomas, Nag Hammadi, Dead Sea Scrolls |
| Eastern Wisdom | 12+ | Art of War, Book of Five Rings, Tao Te Ching, Rumi, Hagakure |
| Secret Societies | 8+ | Morals and Dogma, Rosicrucian manifestos, Masonic texts |
| Astrology / Divination | 5+ | Tetrabiblos, I Ching, Tarot texts, Nostradamus |
| Forbidden / Controversial | 12+ | Banned books, revolutionary texts, censored works |

## Features

### CLI App (`pocket_alexandria.py`)
- **download** -- Downloads all texts from Gutenberg, Sacred-Texts, etc.
- **search** -- Full-text search across every downloaded book
- **browse** -- Interactive category browser with Rich terminal UI
- **read** -- Terminal book reader with pagination, bookmarks, search
- **stats** -- Collection statistics and reading progress
- **recommend** -- Book recommendations based on reading history
- **random** -- Surface a random profound passage

### Web Reader (`web_reader.py`)
- Beautiful dark theme reading interface at localhost:8888
- Category sidebar navigation
- Full-text search
- Reading progress tracking (SQLite)
- Bookmarks and highlights
- Random passage feature
- Keyboard navigation (arrow keys, / for search)

### Discovery Engine (`discovery.py`)
- Scrapes Project Gutenberg for matching public domain texts
- Scrapes Sacred-Texts.com for esoteric works
- Keyword-based text classification
- Auto-adds discovered books to catalog

### Content Virality Tools
- **generate_quotes.py** -- Extracts the most profound/shareable quotes, scored for virality
- **daily_wisdom.py** -- Generates ready-to-post content for TikTok, Instagram, and Twitter

## Content Generation

```bash
# Extract quotes from all books
python generate_quotes.py

# See top 20 most shareable quotes
python generate_quotes.py --top 20

# Generate today's social media content
python daily_wisdom.py

# Generate a week of content
python daily_wisdom.py --batch 7

# Theme-specific content
python daily_wisdom.py --theme alchemy

# TikTok-only format
python daily_wisdom.py --format tiktok
```

## Architecture

```
pocket_alexandria_full_starter_pack/
  pocket_alexandria.py  -- Main CLI app
  web_reader.py         -- Flask web reader
  download_books.py     -- Book downloader
  discovery.py          -- Discovery engine
  generate_quotes.py    -- Quote extraction
  daily_wisdom.py       -- Content generator
  db.py                 -- SQLite database layer
  books_metadata.csv    -- Master book catalog (100+ texts)
  requirements.txt      -- Python dependencies
  templates/            -- Jinja2 HTML templates
  static/               -- CSS, JS, assets
  books/                -- Downloaded texts (by category)
  data/                 -- SQLite DB, discoveries, exports
```

## Tech Stack

- **Python 3.8+** with no exotic dependencies
- **Flask** for the web reader
- **SQLite** for reading progress, bookmarks, search index
- **Rich** for beautiful terminal output
- **BeautifulSoup4** for web scraping in the discovery engine
- **tqdm** for progress bars

## All texts are public domain.

Every book in the catalog is freely available under public domain. Sources include Project Gutenberg, Sacred-Texts.com, and the Internet Archive. No copyrighted material is included.
