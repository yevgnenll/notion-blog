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

def test_parse_tags_en():
    SAMPLE_RESPONSE_EN = """# The Future of Quantum Computing

Tags: technology, science, computing

## Introduction
Quantum computing goes beyond the limits of classical computing.
"""
    result = parse_blog_response(SAMPLE_RESPONSE_EN)
    assert result["tags"] == ["technology", "science", "computing"]

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
    assert props["제목"]["title"][0]["text"]["content"] == "양자컴퓨팅의 미래"
    assert props["태그"]["multi_select"] == [{"name": "기술"}, {"name": "과학"}]
    assert props["공개여부"]["checkbox"] is False

    # Check first content block is yaml code block
    children = payload["children"]
    assert children[0]["type"] == "code"
    assert children[0]["code"]["language"] == "yaml"
    assert "cleanUrl: /posts/quantum-computing-future" in children[0]["code"]["rich_text"][0]["text"]["content"]

    # Check heading_2 block (now at index 2 because index 1 is table_of_contents)
    assert children[1]["type"] == "table_of_contents"
    assert children[2]["type"] == "heading_2"
    assert children[3]["type"] == "paragraph"


from mvp_notebooklm import generate_blog

MOCK_NLM_RESPONSE = """# 양자컴퓨팅의 미래

태그: 기술, 과학, 미래

## 서론
양자컴퓨팅은 매우 혁신적인 기술이다.

## 결론
앞으로 더 발전할 것이다.
"""

def test_generate_blog_calls_notebooklm_and_notion():
    mock_chat_result = {"answer": MOCK_NLM_RESPONSE, "conversation_id": "conv-1"}

    with patch("mvp_notebooklm.chat.query", return_value=mock_chat_result) as mock_query, \
         patch("mvp_notebooklm.get_client") as mock_get_client, \
         patch("mvp_notebooklm.post_to_notion", return_value={"id": "pg-1", "url": "https://notion.so/pg-1"}) as mock_notion:
        result = generate_blog("양자컴퓨팅의 미래")

    mock_query.assert_called_once()
    call_kwargs = mock_query.call_args
    # Prompt must contain the topic
    query_text = (
        call_kwargs.kwargs.get("query_text")
        or (call_kwargs[1].get("query_text") if call_kwargs[1] else None)
        or (call_kwargs[0][2] if len(call_kwargs[0]) > 2 else None)
    )
    assert query_text is not None, "query_text not found in call args"
    assert "양자컴퓨팅의 미래" in query_text

    mock_notion.assert_called_once()
    notion_call = mock_notion.call_args
    notion_kwargs = notion_call.kwargs if notion_call.kwargs else notion_call[1]
    assert notion_kwargs["title"] == "양자컴퓨팅의 미래"
    assert "기술" in notion_kwargs["tags"]

    assert result["notion_url"] == "https://notion.so/pg-1"
    assert result["title"] == "양자컴퓨팅의 미래"


import subprocess

def test_blog_command_help_shows_in_help():
    result = subprocess.run(
        ["python", "mvp_notebooklm.py", "--help"],
        cwd="/Users/yevgnenll/dev/blog-generator",
        capture_output=True, text=True
    )
    assert "blog" in result.stdout or "blog" in result.stderr
