#!/usr/bin/env python3
"""
Pocket Alexandria - The Hidden Digital Library
A curated collection of esoteric, occult, philosophical, and sacred texts.

Usage:
    python pocket_alexandria.py download     # Download all books
    python pocket_alexandria.py search "alchemy"  # Full-text search
    python pocket_alexandria.py browse       # Interactive category browser
    python pocket_alexandria.py read "Kybalion"   # Read in terminal with paging
    python pocket_alexandria.py stats        # Collection statistics
    python pocket_alexandria.py recommend    # Discover related texts
    python pocket_alexandria.py random       # Random profound passage
    python pocket_alexandria.py list         # List all books
    python pocket_alexandria.py web          # Start web reader
"""

import os
import sys
import argparse
import textwrap
import shutil
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.columns import Columns
    from rich import box
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(BASE_DIR, "books_metadata.csv")

BANNER = r"""
   ___           _        _      _   _                          _      _
  / _ \___   ___| | _____| |_   / \ | | _____  ____ _ _ __   __| |_ __(_) __ _
 / /_)/ _ \ / __| |/ / _ \ __| / _ \| |/ _ \ \/ / _` | '_ \ / _` | '__| |/ _` |
/ ___/ (_) | (__|   <  __/ |_ / ___ \ |  __/>  < (_| | | | | (_| | |  | | (_| |
\/    \___/ \___|_|\_\___|\__/_/   \_\_|\___/_/\_\__,_|_| |_|\__,_|_|  |_|\__,_|

                    The Hidden Digital Library
                  Sacred | Esoteric | Philosophical
"""


def clear_screen():
    """Clear the terminal screen safely."""
    if os.name == 'nt':
        subprocess.run(["cmd", "/c", "cls"], check=False)
    else:
        subprocess.run(["clear"], check=False)


def print_banner():
    """Print the application banner."""
    if HAS_RICH:
        console.print(Panel(
            Text(BANNER, style="bold cyan", justify="center"),
            border_style="bright_magenta",
            box=box.DOUBLE,
        ))
    else:
        print(BANNER)


def ensure_catalog():
    """Ensure the catalog is loaded into the database."""
    db.init_db()
    db.load_catalog_to_db(CATALOG_PATH)


def cmd_download(args):
    """Download all books."""
    print_banner()
    ensure_catalog()

    if HAS_RICH:
        console.print("\n[bold yellow]Initiating library download...[/bold yellow]\n")

    from download_books import download_all
    download_all(
        category=getattr(args, 'category', None),
        force=getattr(args, 'force', False),
    )


def cmd_search(args):
    """Full-text search across all books."""
    ensure_catalog()
    query = " ".join(args.query) if isinstance(args.query, list) else args.query

    if not query:
        print("Usage: pocket_alexandria.py search <query>")
        return

    results = db.search_books(query, limit=args.limit if hasattr(args, 'limit') else 20)

    if not results:
        if HAS_RICH:
            console.print(f"\n[yellow]No results found for '[bold]{query}[/bold]'[/yellow]")
            console.print("[dim]Tip: Make sure books are downloaded and indexed first.[/dim]")
        else:
            print(f"\nNo results found for '{query}'")
        return

    if HAS_RICH:
        console.print(f"\n[bold green]Found {len(results)} results for '[cyan]{query}[/cyan]':[/bold green]\n")

        for i, result in enumerate(results, 1):
            text = result['text']
            idx = text.lower().find(query.lower())
            if idx >= 0:
                start = max(0, idx - 100)
                end = min(len(text), idx + len(query) + 100)
                snippet = text[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
            else:
                snippet = text[:200] + "..."

            panel = Panel(
                f"[dim]{snippet}[/dim]",
                title=f"[bold]{result['title']}[/bold] by {result['author']}",
                subtitle=f"[dim]{result['category']}[/dim]",
                border_style="cyan",
            )
            console.print(panel)
    else:
        print(f"\nFound {len(results)} results for '{query}':\n")
        for i, result in enumerate(results, 1):
            text = result['text']
            idx = text.lower().find(query.lower())
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(text), idx + len(query) + 80)
                snippet = text[start:end]
            else:
                snippet = text[:160]
            print(f"  {i}. [{result['category']}] {result['title']} by {result['author']}")
            print(f"     ...{snippet}...")
            print()


def cmd_browse(args):
    """Interactive category browser."""
    ensure_catalog()

    while True:
        categories = db.get_categories()

        if HAS_RICH:
            console.print("\n[bold magenta]Library Categories[/bold magenta]\n")
            table = Table(box=box.ROUNDED, border_style="bright_magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Category", style="bold cyan")
            table.add_column("Total", justify="right")
            table.add_column("Downloaded", justify="right", style="green")

            for i, cat in enumerate(categories, 1):
                table.add_row(
                    str(i),
                    cat['category'],
                    str(cat['count']),
                    str(cat['downloaded_count']),
                )

            console.print(table)
            console.print("\n[dim]Enter category number to browse, or 'q' to quit[/dim]")

            choice = Prompt.ask("Select", default="q")
        else:
            print("\nLibrary Categories:")
            for i, cat in enumerate(categories, 1):
                print(f"  {i}. {cat['category']} ({cat['count']} books, {cat['downloaded_count']} downloaded)")
            choice = input("\nSelect category number (q to quit): ").strip()

        if choice.lower() == 'q':
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                browse_category(categories[idx]['category'])
            else:
                print("Invalid selection.")
        except ValueError:
            print("Enter a number or 'q'.")


def browse_category(category):
    """Browse books in a specific category."""
    books = db.get_all_books(category=category)

    if HAS_RICH:
        console.print(f"\n[bold cyan]{category}[/bold cyan]\n")
        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold")
        table.add_column("Author", style="dim")
        table.add_column("Year", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Description", style="dim", max_width=40)

        for i, book in enumerate(books, 1):
            status = "[green]Downloaded[/green]" if book['downloaded'] else "[red]Not yet[/red]"
            desc = (book['description'] or "")[:40]
            table.add_row(
                str(i), book['title'], book['author'],
                str(book['year']), status, desc
            )
        console.print(table)

        choice = Prompt.ask("\n[dim]Enter book number to read, or 'b' to go back[/dim]", default="b")
    else:
        print(f"\n{category}:")
        for i, book in enumerate(books, 1):
            status = "***" if book['downloaded'] else "   "
            print(f"  {status} {i}. {book['title']} ({book['author']}, {book['year']})")
        choice = input("\nSelect book number (b to go back): ").strip()

    if choice.lower() != 'b':
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(books):
                read_book(books[idx])
        except ValueError:
            pass


def cmd_read(args):
    """Read a book in the terminal."""
    ensure_catalog()
    title = " ".join(args.title) if isinstance(args.title, list) else args.title

    book = db.get_book_by_title(title)
    if not book:
        if HAS_RICH:
            console.print(f"[red]Book not found: '{title}'[/red]")
            console.print("[dim]Try 'pocket_alexandria.py list' to see available books.[/dim]")
        else:
            print(f"Book not found: '{title}'")
        return

    if not book['downloaded']:
        if HAS_RICH:
            console.print(f"[yellow]'{book['title']}' hasn't been downloaded yet.[/yellow]")
            console.print("[dim]Run 'pocket_alexandria.py download' first.[/dim]")
        else:
            print(f"'{book['title']}' hasn't been downloaded yet.")
        return

    read_book(book)


def read_book(book):
    """Interactive book reader with paging."""
    file_path = book['file_path']
    if not file_path or not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    if not text.strip():
        print("Book file is empty.")
        return

    # Get terminal size
    term_width = shutil.get_terminal_size().columns
    term_height = shutil.get_terminal_size().lines - 4

    # Word wrap
    lines = []
    for paragraph in text.split('\n'):
        if paragraph.strip():
            wrapped = textwrap.wrap(paragraph, width=min(term_width - 4, 80))
            lines.extend(wrapped)
            lines.append('')
        else:
            lines.append('')

    total_lines = len(lines)
    total_pages = max(1, (total_lines + term_height - 1) // term_height)

    # Resume from saved position
    progress = db.get_reading_progress(book['id'])
    current_line = 0
    if progress and progress['position'] > 0:
        if HAS_RICH:
            resume = Confirm.ask(
                f"[yellow]Resume from {progress['percent_complete']:.1f}% ({current_line}/{total_lines})?[/yellow]",
                default=True
            )
            if not resume:
                current_line = 0
            else:
                current_line = progress['position']
        else:
            resp = input(f"Resume from {progress['percent_complete']:.1f}%? (Y/n): ").strip()
            if resp.lower() != 'n':
                current_line = progress['position']

    while True:
        clear_screen()

        page_num = current_line // term_height + 1
        percent = min(100, (current_line + term_height) / total_lines * 100) if total_lines > 0 else 100

        # Header
        if HAS_RICH:
            console.print(Panel(
                f"[bold]{book['title']}[/bold] by [cyan]{book['author']}[/cyan]",
                subtitle=f"Page {page_num}/{total_pages} | {percent:.0f}%",
                border_style="bright_magenta",
            ))
        else:
            print(f"{'=' * min(term_width, 80)}")
            print(f"  {book['title']} by {book['author']}")
            print(f"  Page {page_num}/{total_pages} | {percent:.0f}%")
            print(f"{'=' * min(term_width, 80)}")

        # Display page content
        page_lines = lines[current_line:current_line + term_height]
        for line in page_lines:
            print(f"  {line}")

        # Footer
        if HAS_RICH:
            console.print(
                "\n[dim][n]ext [p]rev [j]ump [b]ookmark [s]earch [h]ome [q]uit[/dim]",
                justify="center"
            )
        else:
            print(f"\n  [n]ext [p]rev [j]ump [b]ookmark [s]earch [h]ome [q]uit")

        # Save progress
        db.update_reading_progress(book['id'], current_line, total_lines)

        # Input
        try:
            cmd = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ('n', '', 'next'):
            current_line = min(current_line + term_height, total_lines - term_height)
            current_line = max(0, current_line)
        elif cmd in ('p', 'prev'):
            current_line = max(0, current_line - term_height)
        elif cmd in ('q', 'quit', 'exit'):
            db.update_reading_progress(book['id'], current_line, total_lines)
            break
        elif cmd in ('h', 'home'):
            current_line = 0
        elif cmd.startswith('j') or cmd.startswith('jump'):
            try:
                page = int(cmd.split()[-1]) if len(cmd.split()) > 1 else int(input("  Jump to page: "))
                current_line = min(max(0, (page - 1) * term_height), total_lines - term_height)
            except (ValueError, EOFError):
                pass
        elif cmd in ('b', 'bookmark'):
            snippet = " ".join(lines[current_line:current_line + 3])[:200]
            label = input("  Bookmark label (enter for none): ").strip() or None
            db.add_bookmark(book['id'], current_line, label, snippet)
            if HAS_RICH:
                console.print("[green]Bookmark saved![/green]")
            else:
                print("  Bookmark saved!")
            input("  Press Enter to continue...")
        elif cmd in ('s', 'search'):
            query = input("  Search text: ").strip()
            if query:
                found = False
                for i in range(current_line, total_lines):
                    if query.lower() in lines[i].lower():
                        current_line = max(0, i - 2)
                        found = True
                        break
                if not found:
                    for i in range(0, current_line):
                        if query.lower() in lines[i].lower():
                            current_line = max(0, i - 2)
                            found = True
                            break
                if not found:
                    print(f"  '{query}' not found.")
                    input("  Press Enter to continue...")


def cmd_stats(args):
    """Show collection statistics."""
    ensure_catalog()
    stats = db.get_stats()

    if HAS_RICH:
        print_banner()

        table = Table(
            title="Library Statistics",
            box=box.DOUBLE_EDGE,
            border_style="bright_magenta",
            show_header=False,
            pad_edge=True,
        )
        table.add_column("Metric", style="bold cyan", width=30)
        table.add_column("Value", style="bold white", justify="right", width=20)

        table.add_row("Total Books in Catalog", str(stats['total_books']))
        table.add_row("Books Downloaded", str(stats['downloaded']))
        table.add_row("Books Indexed", str(stats['indexed']))
        table.add_row("Total Words", f"{stats['total_words']:,}")
        table.add_row("Library Size", f"{stats['total_size_mb']} MB")
        table.add_row("Categories", str(stats['categories']))
        table.add_row("", "")
        table.add_row("Bookmarks", str(stats['bookmarks']))
        table.add_row("Highlights", str(stats['highlights']))
        table.add_row("Saved Quotes", str(stats['quotes']))
        table.add_row("", "")
        table.add_row("Books Started Reading", str(stats['books_started']))
        table.add_row("Average Progress", f"{stats['avg_progress']}%")

        if stats['oldest_text']:
            table.add_row("", "")
            table.add_row("Oldest Text", f"{stats['oldest_text']['title']} ({stats['oldest_text']['year']})")
        if stats['newest_text']:
            table.add_row("Newest Text", f"{stats['newest_text']['title']} ({stats['newest_text']['year']})")

        console.print(table)

        categories = db.get_categories()
        cat_table = Table(
            title="Category Breakdown",
            box=box.ROUNDED,
            border_style="cyan",
        )
        cat_table.add_column("Category", style="bold")
        cat_table.add_column("Total", justify="right")
        cat_table.add_column("Downloaded", justify="right", style="green")
        cat_table.add_column("Completion", justify="right")

        for cat in categories:
            pct = (cat['downloaded_count'] / cat['count'] * 100) if cat['count'] > 0 else 0
            bar_len = int(pct / 5)
            bar = "[green]" + "|" * bar_len + "[/green]" + "[dim]" + "|" * (20 - bar_len) + "[/dim]"
            cat_table.add_row(
                cat['category'],
                str(cat['count']),
                str(cat['downloaded_count']),
                f"{bar} {pct:.0f}%",
            )
        console.print(cat_table)
    else:
        print("\n=== Library Statistics ===")
        print(f"  Total Books: {stats['total_books']}")
        print(f"  Downloaded: {stats['downloaded']}")
        print(f"  Indexed: {stats['indexed']}")
        print(f"  Total Words: {stats['total_words']:,}")
        print(f"  Library Size: {stats['total_size_mb']} MB")
        print(f"  Categories: {stats['categories']}")
        print(f"  Bookmarks: {stats['bookmarks']}")
        print(f"  Books Reading: {stats['books_started']}")


def cmd_list(args):
    """List all books in the catalog."""
    ensure_catalog()
    category = getattr(args, 'category', None)
    books = db.get_all_books(category=category)

    if HAS_RICH:
        table = Table(
            title="Pocket Alexandria - Book Catalog",
            box=box.ROUNDED,
            border_style="bright_magenta",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold cyan", max_width=45)
        table.add_column("Author", style="dim", max_width=25)
        table.add_column("Year", justify="right", width=6)
        table.add_column("Category", style="magenta", max_width=20)
        table.add_column("Status", justify="center", width=8)

        for i, book in enumerate(books, 1):
            status = "[green]Yes[/green]" if book['downloaded'] else "[dim]No[/dim]"
            table.add_row(
                str(i), book['title'], book['author'],
                str(book['year']), book['category'], status
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(books)} books[/dim]")
    else:
        print(f"\nPocket Alexandria - {len(books)} books:\n")
        for i, book in enumerate(books, 1):
            dl = "*" if book['downloaded'] else " "
            print(f"  [{dl}] {i:3d}. {book['title'][:45]} | {book['author'][:20]} | {book['year']} | {book['category']}")


def cmd_recommend(args):
    """Recommend books based on reading history or preferences."""
    ensure_catalog()

    if HAS_RICH:
        console.print("\n[bold magenta]Book Recommendations[/bold magenta]\n")

    conn = db.get_connection()

    read_books = conn.execute("""
        SELECT b.category, b.subcategory, b.title
        FROM reading_progress rp
        JOIN books b ON rp.book_id = b.id
        WHERE rp.percent_complete > 5
    """).fetchall()

    if read_books:
        read_categories = set(b['category'] for b in read_books)
        read_subcategories = set(b['subcategory'] for b in read_books if b['subcategory'])
        read_titles = set(b['title'] for b in read_books)

        recommendations = conn.execute("""
            SELECT * FROM books
            WHERE downloaded = 1
            AND title NOT IN ({})
            AND (category IN ({}) OR subcategory IN ({}))
            ORDER BY RANDOM()
            LIMIT 10
        """.format(
            ','.join('?' * len(read_titles)),
            ','.join('?' * len(read_categories)),
            ','.join('?' * len(read_subcategories))
        ), list(read_titles) + list(read_categories) + list(read_subcategories)).fetchall()
    else:
        recommendations = conn.execute("""
            SELECT * FROM books
            WHERE downloaded = 1
            ORDER BY RANDOM()
            LIMIT 10
        """).fetchall()

    conn.close()

    if not recommendations:
        recommendations = db.get_all_books(downloaded_only=True)[:10]

    if not recommendations:
        print("Download some books first to get recommendations!")
        return

    if HAS_RICH:
        if read_books:
            console.print(f"[dim]Based on your reading of: {', '.join(b['title'] for b in read_books[:3])}...[/dim]\n")
        else:
            console.print("[dim]Essential texts to start your journey:[/dim]\n")

        for i, book in enumerate(recommendations, 1):
            panel = Panel(
                f"[dim]{book['description'] or 'A classic text awaiting discovery.'}[/dim]",
                title=f"[bold cyan]{book['title']}[/bold cyan] by [dim]{book['author']}[/dim]",
                subtitle=f"[magenta]{book['category']}[/magenta] | {book['year']}",
                border_style="bright_magenta",
            )
            console.print(panel)
    else:
        print("\nRecommended reading:\n")
        for i, book in enumerate(recommendations, 1):
            print(f"  {i}. {book['title']} by {book['author']} ({book['year']})")
            print(f"     {book['category']} - {book['description'] or ''}")
            print()


def cmd_random(args):
    """Show a random profound passage."""
    ensure_catalog()
    passage = db.get_random_passage()

    if not passage:
        print("No indexed books found. Download and index books first.")
        return

    if HAS_RICH:
        text = passage['text']
        panel = Panel(
            f"\n[italic]{text}[/italic]\n",
            title="[bold yellow]Random Passage[/bold yellow]",
            subtitle=f"[bold cyan]{passage['title']}[/bold cyan] by [dim]{passage['author']}[/dim] | [magenta]{passage['category']}[/magenta]",
            border_style="bright_yellow",
            width=min(console.width, 90),
            padding=(1, 3),
        )
        console.print(panel)
    else:
        print(f"\n{'=' * 60}")
        print(f"  {passage['text']}")
        print(f"{'=' * 60}")
        print(f"  -- {passage['title']} by {passage['author']}")
        print()


def cmd_web(args):
    """Start the web reader."""
    ensure_catalog()
    port = getattr(args, 'port', 8888)

    if HAS_RICH:
        console.print(f"\n[bold green]Starting Pocket Alexandria web reader on port {port}...[/bold green]")
        console.print(f"[dim]Open http://localhost:{port} in your browser[/dim]\n")
    else:
        print(f"\nStarting web reader on port {port}...")
        print(f"Open http://localhost:{port} in your browser\n")

    from web_reader import app
    app.run(host="0.0.0.0", port=port, debug=getattr(args, 'debug', False))


def main():
    parser = argparse.ArgumentParser(
        description="Pocket Alexandria - The Hidden Digital Library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Commands:
              download    Download all books from the catalog
              search      Full-text search across all books
              browse      Interactive category browser
              read        Read a book in the terminal
              stats       Show collection statistics
              list        List all books in the catalog
              recommend   Get book recommendations
              random      Show a random profound passage
              web         Start the web reader interface
        """)
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    dl_parser = subparsers.add_parser('download', help='Download all books')
    dl_parser.add_argument('--category', help='Only download this category')
    dl_parser.add_argument('--force', action='store_true', help='Re-download all')

    search_parser = subparsers.add_parser('search', help='Full-text search')
    search_parser.add_argument('query', nargs='+', help='Search query')
    search_parser.add_argument('--limit', type=int, default=20, help='Max results')

    subparsers.add_parser('browse', help='Interactive category browser')

    read_parser = subparsers.add_parser('read', help='Read a book')
    read_parser.add_argument('title', nargs='+', help='Book title (partial match)')

    subparsers.add_parser('stats', help='Collection statistics')

    list_parser = subparsers.add_parser('list', help='List all books')
    list_parser.add_argument('--category', help='Filter by category')

    subparsers.add_parser('recommend', help='Book recommendations')

    subparsers.add_parser('random', help='Random profound passage')

    web_parser = subparsers.add_parser('web', help='Start web reader')
    web_parser.add_argument('--port', type=int, default=8888, help='Port number')
    web_parser.add_argument('--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        return

    commands = {
        'download': cmd_download,
        'search': cmd_search,
        'browse': cmd_browse,
        'read': cmd_read,
        'stats': cmd_stats,
        'list': cmd_list,
        'recommend': cmd_recommend,
        'random': cmd_random,
        'web': cmd_web,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
