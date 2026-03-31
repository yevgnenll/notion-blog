import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mvp_notebooklm import make_slug, parse_blog_response

def test_make_slug_english():
    assert make_slug("The Future of Quantum Computing") == "the-future-of-quantum-computing"

def test_make_slug_strips_special_chars():
    assert make_slug("Hello, World! (2024)") == "hello-world-2024"

def test_make_slug_collapses_hyphens():
    assert make_slug("A  B---C") == "a-b-c"

def test_make_slug_strips_leading_trailing():
    assert make_slug("  hello world  ") == "hello-world"


SAMPLE_RESPONSE = """# 양자컴퓨팅의 미래

태그: 기술, 과학, 컴퓨팅

## 들어가며
양자컴퓨팅은 고전적인 컴퓨팅의 한계를 넘어선다.

## 핵심 원리
중첩과 얽힘을 활용해 병렬 연산을 수행한다.
"""

def test_parse_title():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["title"] == "양자컴퓨팅의 미래"

def test_parse_tags():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["tags"] == ["기술", "과학", "컴퓨팅"]

def test_parse_blocks_count():
    result = parse_blog_response(SAMPLE_RESPONSE)
    # Two heading_2 + two paragraph blocks
    assert len(result["blocks"]) == 4

def test_parse_blocks_heading():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["blocks"][0] == ("heading_2", "들어가며")

def test_parse_blocks_paragraph():
    result = parse_blog_response(SAMPLE_RESPONSE)
    assert result["blocks"][1] == ("paragraph", "양자컴퓨팅은 고전적인 컴퓨팅의 한계를 넘어선다.")

def test_parse_no_title_raises():
    try:
        parse_blog_response("태그: x\n\n## 섹션\n내용")
        assert False, "Expected ValueError"
    except ValueError:
        pass
