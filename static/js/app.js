/**
 * Pocket Alexandria - Frontend JavaScript
 * Handles sidebar toggle, keyboard shortcuts, and UI interactions.
 */

document.addEventListener('DOMContentLoaded', function() {

    // ─── Sidebar Toggle (Mobile) ────────────────────────────────────────
    const sidebar = document.getElementById('sidebar');
    const toggle = document.getElementById('sidebarToggle');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768 &&
                sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                e.target !== toggle) {
                sidebar.classList.remove('open');
            }
        });
    }

    // ─── Keyboard Shortcuts ─────────────────────────────────────────────
    document.addEventListener('keydown', function(e) {
        // Don't trigger shortcuts when typing in inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        // / - Focus search
        if (e.key === '/') {
            e.preventDefault();
            var searchInput = document.querySelector('.sidebar-search input');
            if (searchInput) searchInput.focus();
        }

        // Escape - Close sidebar on mobile
        if (e.key === 'Escape') {
            if (sidebar) sidebar.classList.remove('open');
        }
    });

    // ─── Smooth page transitions ────────────────────────────────────────
    document.querySelectorAll('a[href^="/"]').forEach(function(link) {
        link.addEventListener('click', function() {
            document.body.style.opacity = '0.95';
            setTimeout(function() {
                document.body.style.opacity = '1';
            }, 200);
        });
    });

    // ─── Search autocomplete debouncing ─────────────────────────────────
    var searchInput = document.querySelector('.search-form-large input');
    if (searchInput) {
        var debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                // Could add live search here
            }, 300);
        });
    }

    // ─── Reading progress persistence ───────────────────────────────────
    var readerText = document.getElementById('readerText');
    if (readerText) {
        // Track scroll position for reading progress
        var lastScrollSave = 0;
        window.addEventListener('scroll', function() {
            var now = Date.now();
            if (now - lastScrollSave > 2000) {
                lastScrollSave = now;
                var scrollPercent = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
                var progressBar = document.getElementById('readingProgress');
                if (progressBar) {
                    progressBar.style.width = Math.min(100, scrollPercent) + '%';
                }
            }
        });
    }

    console.log('Pocket Alexandria loaded. Press / to search.');
});
