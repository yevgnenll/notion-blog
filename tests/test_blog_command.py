import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mvp_notebooklm import make_slug

def test_make_slug_english():
    assert make_slug("The Future of Quantum Computing") == "the-future-of-quantum-computing"

def test_make_slug_strips_special_chars():
    assert make_slug("Hello, World! (2024)") == "hello-world-2024"

def test_make_slug_collapses_hyphens():
    assert make_slug("A  B---C") == "a-b-c"

def test_make_slug_strips_leading_trailing():
    assert make_slug("  hello world  ") == "hello-world"
