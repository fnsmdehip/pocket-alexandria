"""
Pocket Alexandria - Database Layer
SQLite database for reading progress, bookmarks, highlights, and book metadata.
"""

import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "alexandria.db")


def get_connection():
    """Get a database connection with row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize all database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            year INTEGER,
            category TEXT,
            subcategory TEXT,
            url TEXT,
            description TEXT,
            file_path TEXT,
            file_size INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            downloaded INTEGER DEFAULT 0,
            indexed INTEGER DEFAULT 0,
            added_at TEXT DEFAULT (datetime('now')),
            UNIQUE(title, author)
        );

        CREATE TABLE IF NOT EXISTS reading_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            position INTEGER DEFAULT 0,
            total_length INTEGER DEFAULT 0,
            percent_complete REAL DEFAULT 0.0,
            last_read TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id),
            UNIQUE(book_id)
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            label TEXT,
            snippet TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS highlights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            start_pos INTEGER NOT NULL,
            end_pos INTEGER NOT NULL,
            text TEXT NOT NULL,
            note TEXT,
            color TEXT DEFAULT 'yellow',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            context TEXT,
            virality_score REAL DEFAULT 0.0,
            shared_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS search_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            chunk_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE INDEX IF NOT EXISTS idx_search_text ON search_index(text);
        CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
        CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
        CREATE INDEX IF NOT EXISTS idx_reading_progress_book ON reading_progress(book_id);
        CREATE INDEX IF NOT EXISTS idx_bookmarks_book ON bookmarks(book_id);
        CREATE INDEX IF NOT EXISTS idx_highlights_book ON highlights(book_id);
        CREATE INDEX IF NOT EXISTS idx_quotes_book ON quotes(book_id);
    """)

    conn.commit()
    conn.close()


def load_catalog_to_db(csv_path):
    """Load books from CSV into the database."""
    import csv

    conn = get_connection()
    cursor = conn.cursor()
    count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO books (title, author, year, category, subcategory, url, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get("title", "").strip(),
                    row.get("author", "").strip(),
                    int(row.get("year", 0)) if row.get("year", "").strip() else 0,
                    row.get("category", "").strip(),
                    row.get("subcategory", "").strip(),
                    row.get("url", "").strip(),
                    row.get("description", "").strip(),
                ))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                print(f"  Warning: skipped row - {e}")

    conn.commit()
    conn.close()
    return count


def get_all_books(category=None, downloaded_only=False):
    """Get all books, optionally filtered."""
    conn = get_connection()
    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if downloaded_only:
        query += " AND downloaded = 1"

    query += " ORDER BY category, title"
    books = conn.execute(query, params).fetchall()
    conn.close()
    return books


def get_book_by_id(book_id):
    """Get a single book by ID."""
    conn = get_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return book


def get_book_by_title(title):
    """Get a book by title (fuzzy match)."""
    conn = get_connection()
    book = conn.execute(
        "SELECT * FROM books WHERE LOWER(title) LIKE ? ORDER BY LENGTH(title) ASC LIMIT 1",
        (f"%{title.lower()}%",)
    ).fetchone()
    conn.close()
    return book


def mark_downloaded(book_id, file_path, file_size=0, word_count=0):
    """Mark a book as downloaded."""
    conn = get_connection()
    conn.execute("""
        UPDATE books SET downloaded = 1, file_path = ?, file_size = ?, word_count = ?
        WHERE id = ?
    """, (file_path, file_size, word_count, book_id))
    conn.commit()
    conn.close()


def update_reading_progress(book_id, position, total_length):
    """Update reading progress for a book."""
    percent = (position / total_length * 100) if total_length > 0 else 0
    conn = get_connection()
    conn.execute("""
        INSERT INTO reading_progress (book_id, position, total_length, percent_complete, last_read)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(book_id) DO UPDATE SET
            position = excluded.position,
            total_length = excluded.total_length,
            percent_complete = excluded.percent_complete,
            last_read = datetime('now')
    """, (book_id, position, total_length, percent))
    conn.commit()
    conn.close()


def get_reading_progress(book_id):
    """Get reading progress for a book."""
    conn = get_connection()
    progress = conn.execute(
        "SELECT * FROM reading_progress WHERE book_id = ?", (book_id,)
    ).fetchone()
    conn.close()
    return progress


def add_bookmark(book_id, position, label=None, snippet=None):
    """Add a bookmark."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO bookmarks (book_id, position, label, snippet) VALUES (?, ?, ?, ?)",
        (book_id, position, label, snippet)
    )
    conn.commit()
    conn.close()


def get_bookmarks(book_id):
    """Get all bookmarks for a book."""
    conn = get_connection()
    bookmarks = conn.execute(
        "SELECT * FROM bookmarks WHERE book_id = ? ORDER BY position", (book_id,)
    ).fetchall()
    conn.close()
    return bookmarks


def add_highlight(book_id, start_pos, end_pos, text, note=None, color="yellow"):
    """Add a highlight."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO highlights (book_id, start_pos, end_pos, text, note, color) VALUES (?, ?, ?, ?, ?, ?)",
        (book_id, start_pos, end_pos, text, note, color)
    )
    conn.commit()
    conn.close()


def get_highlights(book_id):
    """Get all highlights for a book."""
    conn = get_connection()
    highlights = conn.execute(
        "SELECT * FROM highlights WHERE book_id = ? ORDER BY start_pos", (book_id,)
    ).fetchall()
    conn.close()
    return highlights


def add_quote(book_id, text, context=None, virality_score=0.0):
    """Add a quote."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO quotes (book_id, text, context, virality_score) VALUES (?, ?, ?, ?)",
        (book_id, text, context, virality_score)
    )
    conn.commit()
    conn.close()


def get_quotes(book_id=None, limit=50):
    """Get quotes, optionally filtered by book."""
    conn = get_connection()
    if book_id:
        quotes = conn.execute(
            "SELECT q.*, b.title, b.author FROM quotes q JOIN books b ON q.book_id = b.id WHERE q.book_id = ? ORDER BY q.virality_score DESC LIMIT ?",
            (book_id, limit)
        ).fetchall()
    else:
        quotes = conn.execute(
            "SELECT q.*, b.title, b.author FROM quotes q JOIN books b ON q.book_id = b.id ORDER BY q.virality_score DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return quotes


def build_search_index(book_id, text, chunk_size=500):
    """Build search index for a book by splitting into chunks."""
    conn = get_connection()
    # Clear existing index for this book
    conn.execute("DELETE FROM search_index WHERE book_id = ?", (book_id,))

    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    for i, chunk in enumerate(chunks):
        conn.execute(
            "INSERT INTO search_index (book_id, chunk_number, text) VALUES (?, ?, ?)",
            (book_id, i, chunk)
        )

    conn.execute("UPDATE books SET indexed = 1 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return len(chunks)


def search_books(query, limit=20):
    """Full-text search across all indexed books."""
    conn = get_connection()
    results = conn.execute("""
        SELECT si.*, b.title, b.author, b.category
        FROM search_index si
        JOIN books b ON si.book_id = b.id
        WHERE si.text LIKE ?
        ORDER BY b.title, si.chunk_number
        LIMIT ?
    """, (f"%{query}%", limit)).fetchall()
    conn.close()
    return results


def get_categories():
    """Get all unique categories with counts."""
    conn = get_connection()
    categories = conn.execute("""
        SELECT category, COUNT(*) as count,
               SUM(CASE WHEN downloaded = 1 THEN 1 ELSE 0 END) as downloaded_count
        FROM books
        GROUP BY category
        ORDER BY category
    """).fetchall()
    conn.close()
    return categories


def get_stats():
    """Get collection statistics."""
    conn = get_connection()
    stats = {}
    stats["total_books"] = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    stats["downloaded"] = conn.execute("SELECT COUNT(*) FROM books WHERE downloaded = 1").fetchone()[0]
    stats["indexed"] = conn.execute("SELECT COUNT(*) FROM books WHERE indexed = 1").fetchone()[0]
    stats["total_words"] = conn.execute("SELECT COALESCE(SUM(word_count), 0) FROM books WHERE downloaded = 1").fetchone()[0]
    stats["total_size_mb"] = round(conn.execute("SELECT COALESCE(SUM(file_size), 0) FROM books WHERE downloaded = 1").fetchone()[0] / (1024 * 1024), 2)
    stats["categories"] = conn.execute("SELECT COUNT(DISTINCT category) FROM books").fetchone()[0]
    stats["bookmarks"] = conn.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0]
    stats["highlights"] = conn.execute("SELECT COUNT(*) FROM highlights").fetchone()[0]
    stats["quotes"] = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]

    reading = conn.execute("""
        SELECT COUNT(*) as books_started,
               AVG(percent_complete) as avg_progress
        FROM reading_progress
        WHERE percent_complete > 0
    """).fetchone()
    stats["books_started"] = reading["books_started"] if reading else 0
    stats["avg_progress"] = round(reading["avg_progress"] or 0, 1)

    stats["oldest_text"] = conn.execute("SELECT title, year FROM books ORDER BY year ASC LIMIT 1").fetchone()
    stats["newest_text"] = conn.execute("SELECT title, year FROM books ORDER BY year DESC LIMIT 1").fetchone()

    conn.close()
    return stats


def get_random_passage(min_length=100, max_length=500):
    """Get a random passage from a random downloaded book."""
    import random
    conn = get_connection()
    chunks = conn.execute("""
        SELECT si.text, b.title, b.author, b.category
        FROM search_index si
        JOIN books b ON si.book_id = b.id
        WHERE LENGTH(si.text) > ?
        ORDER BY RANDOM()
        LIMIT 1
    """, (min_length,)).fetchone()
    conn.close()

    if chunks:
        text = chunks["text"]
        # Try to find a good passage within the chunk
        sentences = text.split(".")
        if len(sentences) > 2:
            start = random.randint(0, max(0, len(sentences) - 3))
            passage = ". ".join(sentences[start:start + 3]).strip()
            if passage and not passage.endswith("."):
                passage += "."
        else:
            passage = text[:max_length]

        return {
            "text": passage,
            "title": chunks["title"],
            "author": chunks["author"],
            "category": chunks["category"],
        }
    return None


# Initialize on import
init_db()
