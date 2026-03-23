"""
Pocket Alexandria - Web Reader
Beautiful dark-themed web interface for reading the hidden library.
Flask app at localhost:8888.
"""

import os
import sys
import json
import random
from datetime import datetime

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, abort, send_from_directory
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(BASE_DIR, "books_metadata.csv")

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = os.urandom(24)


@app.before_request
def setup():
    """Ensure database is initialized."""
    db.init_db()
    db.load_catalog_to_db(CATALOG_PATH)


# ─── Pages ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Home page with library overview."""
    stats = db.get_stats()
    categories = db.get_categories()
    passage = db.get_random_passage()
    recent_books = []

    conn = db.get_connection()
    recent = conn.execute("""
        SELECT b.*, rp.percent_complete, rp.last_read
        FROM reading_progress rp
        JOIN books b ON rp.book_id = b.id
        WHERE rp.percent_complete > 0
        ORDER BY rp.last_read DESC
        LIMIT 5
    """).fetchall()
    conn.close()

    return render_template("index.html",
        stats=stats,
        categories=categories,
        passage=passage,
        recent_books=recent,
    )


@app.route("/browse")
@app.route("/browse/<category>")
def browse(category=None):
    """Browse books by category."""
    categories = db.get_categories()
    books = []
    if category:
        books = db.get_all_books(category=category)
    return render_template("browse.html",
        categories=categories,
        books=books,
        current_category=category,
    )


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    """Book detail page."""
    book = db.get_book_by_id(book_id)
    if not book:
        abort(404)

    progress = db.get_reading_progress(book_id)
    bookmarks = db.get_bookmarks(book_id)
    highlights = db.get_highlights(book_id)

    return render_template("book.html",
        book=book,
        progress=progress,
        bookmarks=bookmarks,
        highlights=highlights,
    )


@app.route("/read/<int:book_id>")
def read_book(book_id):
    """Full reading interface for a book."""
    book = db.get_book_by_id(book_id)
    if not book:
        abort(404)

    if not book['downloaded'] or not book['file_path']:
        return render_template("not_downloaded.html", book=book)

    file_path = book['file_path']
    if not os.path.exists(file_path):
        return render_template("not_downloaded.html", book=book)

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    # Split into pages (roughly 3000 chars each)
    page_size = 3000
    pages = []
    for i in range(0, len(text), page_size):
        chunk = text[i:i + page_size]
        # Try to break at a paragraph or sentence
        if i + page_size < len(text):
            last_para = chunk.rfind('\n\n')
            last_period = chunk.rfind('. ')
            break_at = max(last_para, last_period)
            if break_at > page_size * 0.5:
                chunk = text[i:i + break_at + 1]
        pages.append(chunk)

    progress = db.get_reading_progress(book_id)
    current_page = 0
    if progress:
        current_page = min(progress['position'], len(pages) - 1)

    page_num = int(request.args.get('page', current_page))
    page_num = max(0, min(page_num, len(pages) - 1))

    return render_template("reader.html",
        book=book,
        content=pages[page_num] if pages else "",
        current_page=page_num,
        total_pages=len(pages),
        progress=progress,
    )


@app.route("/search")
def search():
    """Search page."""
    query = request.args.get('q', '').strip()
    results = []
    if query:
        results = db.search_books(query, limit=50)
    return render_template("search.html", query=query, results=results)


@app.route("/quotes")
def quotes():
    """Quotes collection page."""
    book_id = request.args.get('book_id', type=int)
    all_quotes = db.get_quotes(book_id=book_id, limit=100)
    return render_template("quotes.html", quotes=all_quotes, book_id=book_id)


# ─── API Endpoints ───────────────────────────────────────────────────────────


@app.route("/api/progress", methods=["POST"])
def api_update_progress():
    """Update reading progress."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    book_id = data.get("book_id")
    position = data.get("position", 0)
    total = data.get("total", 1)

    if book_id:
        db.update_reading_progress(book_id, position, total)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Missing book_id"}), 400


@app.route("/api/bookmark", methods=["POST"])
def api_add_bookmark():
    """Add a bookmark."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    book_id = data.get("book_id")
    position = data.get("position", 0)
    label = data.get("label")
    snippet = data.get("snippet")

    if book_id:
        db.add_bookmark(book_id, position, label, snippet)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Missing book_id"}), 400


@app.route("/api/highlight", methods=["POST"])
def api_add_highlight():
    """Add a highlight."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    book_id = data.get("book_id")
    start_pos = data.get("start_pos", 0)
    end_pos = data.get("end_pos", 0)
    text = data.get("text", "")
    note = data.get("note")

    if book_id and text:
        db.add_highlight(book_id, start_pos, end_pos, text, note)
        return jsonify({"status": "ok"})
    return jsonify({"error": "Missing required fields"}), 400


@app.route("/api/random-passage")
def api_random_passage():
    """Get a random passage."""
    passage = db.get_random_passage()
    if passage:
        return jsonify(passage)
    return jsonify({"error": "No passages available"}), 404


@app.route("/api/search")
def api_search():
    """Search API endpoint."""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    if not query:
        return jsonify({"results": []})

    results = db.search_books(query, limit=limit)
    return jsonify({
        "query": query,
        "results": [
            {
                "book_id": r['book_id'],
                "title": r['title'],
                "author": r['author'],
                "category": r['category'],
                "snippet": r['text'][:300],
            }
            for r in results
        ]
    })


@app.route("/api/stats")
def api_stats():
    """Get library stats."""
    return jsonify(db.get_stats())


@app.route("/api/categories")
def api_categories():
    """Get categories."""
    cats = db.get_categories()
    return jsonify([dict(c) for c in cats])


# ─── Error Handlers ──────────────────────────────────────────────────────────


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ─── Template Filters ────────────────────────────────────────────────────────


@app.template_filter('nl2br')
def nl2br(value):
    """Convert newlines to <br> tags."""
    if not value:
        return ""
    return value.replace('\n\n', '</p><p>').replace('\n', '<br>')


@app.template_filter('truncate_words')
def truncate_words(value, count=50):
    """Truncate to a number of words."""
    if not value:
        return ""
    words = value.split()
    if len(words) <= count:
        return value
    return ' '.join(words[:count]) + '...'


if __name__ == "__main__":
    print("Starting Pocket Alexandria Web Reader...")
    print("Open http://localhost:8888 in your browser")
    app.run(host="0.0.0.0", port=8888, debug=True)
