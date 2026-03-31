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

def test_parse_second_h1_becomes_paragraph():
    text = "# 제목\n\n# 두번째 제목\n\n## 섹션\n내용"
    result = parse_blog_response(text)
    assert result["title"] == "제목"
    # second # line → paragraph without # prefix
    assert ("paragraph", "두번째 제목") in result["blocks"]


from unittest.mock import patch, MagicMock
from mvp_notebooklm import post_to_notion

def test_post_to_notion_sends_correct_payload():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"id": "page-123", "url": "https://notion.so/page-123"}

    blocks = [("heading_2", "들어가며"), ("paragraph", "내용입니다.")]

    with patch("mvp_notebooklm.requests.post", return_value=mock_resp) as mock_post, \
         patch.dict("os.environ", {"NOTION_INTEGRATION_KEY": "secret_test", "NOTION_DATABASE_ID": "db-id-abc"}):
        result = post_to_notion(
            title="양자컴퓨팅의 미래",
            tags=["기술", "과학"],
            blocks=blocks,
            slug="quantum-computing-future"
        )

    assert result["id"] == "page-123"

    call_args = mock_post.call_args
    payload = call_args.kwargs["json"] if "json" in call_args.kwargs else call_args[1]["json"]

    # Check properties
    props = payload["properties"]
    assert props["Name"]["title"][0]["text"]["content"] == "양자컴퓨팅의 미래"
    assert props["태그"]["multi_select"] == [{"name": "기술"}, {"name": "과학"}]
    assert props["공개여부"]["checkbox"] is False

    # Check first content block is yaml code block
    children = payload["children"]
    assert children[0]["type"] == "code"
    assert children[0]["code"]["language"] == "yaml"
    assert "cleanUrl: /posts/quantum-computing-future" in children[0]["code"]["rich_text"][0]["text"]["content"]

    # Check heading_2 block
    assert children[1]["type"] == "heading_2"
    assert children[2]["type"] == "paragraph"
