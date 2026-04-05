"""NotebookLM 쿼리 결과에서 references만 추출하는 모듈."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from notebooklm_tools.mcp.tools._utils import get_client
from notebooklm_tools.services import chat, notebooks


NOTEBOOK_ID = os.environ.get("NOTEBOOKLM_NOTEBOOK_ID", "")


def fetch_references(query: str, notebook_id: str = NOTEBOOK_ID) -> list[dict]:
    """
    NotebookLM에 질문하고 references만 반환한다.

    Args:
        query: 질문 텍스트
        notebook_id: 노트북 UUID

    Returns:
        List of {citation_number, source_title, cited_text} dicts
    """
    client = get_client()
    result = chat.query(client, notebook_id=notebook_id, query_text=query)

    raw_references = result.get("references", [])
    citations = result.get("citations", {})

    if not citations:
        return []

    # source_id -> title 매핑
    source_title_map = {}
    try:
        nb_detail = notebooks.get_notebook(client, notebook_id)
        for src in nb_detail.get("sources", []):
            source_title_map[src["id"]] = os.path.splitext(src["title"])[0]
    except Exception as e:
        print(f"[warn] source title 조회 실패: {e}", file=sys.stderr)

    refs = []
    for ref in raw_references:
        source_id = ref["source_id"]
        refs.append({
            "citation_number": ref["citation_number"],
            "source_title": source_title_map.get(source_id, source_id),
            "cited_text": ref.get("cited_text", ""),
        })
    return refs


def print_references(refs: list[dict]) -> None:
    if not refs:
        print("references 없음")
        return
    for ref in refs:
        excerpt = ref["cited_text"][:200] + "…" if len(ref["cited_text"]) > 200 else ref["cited_text"]
        sep = f" — {excerpt}" if excerpt else ""
        print(f"[{ref['citation_number']}] {ref['source_title']}{sep}")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("질문: ").strip()
    if not query:
        print("질문을 입력해주세요.")
        sys.exit(1)

    print(f"\n질문: {query}\n")
    refs = fetch_references(query)
    print_references(refs)
