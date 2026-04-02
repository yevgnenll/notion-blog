"""Notion Integration 모듈"""
import os
from typing import Optional
from notion_client import Client
from utils.config import CONFIG


class NotionClient:
    """Notion API 클라이언트"""
    
    def __init__(self):
        self.client = Client(auth=CONFIG["notion_integration_key"])
        self.database_id = CONFIG["notion_db_id"]
    
    def create_post(
        self,
        title: str,
        content_blocks: list,
        tags: Optional[list] = None,
        parent_page_id: Optional[str] = None
    ) -> dict:
        """
        Notion에 게시글 생성
        
        Args:
            title: 게시글 제목
            content_blocks: Notion block 형식의 콘텐츠
            tags: 태그 목록
            parent_page_id: 부모 페이지 ID (생략시 DB에 직접 추가)
        
        Returns:
            생성된 페이지 정보
        """
        # Parent 설정
        if parent_page_id:
            parent = {"type": "page_id", "page_id": parent_page_id}
        else:
            parent = {"type": "database_id", "database_id": self.database_id}
        
        # Properties 정의
        properties = {
            "Title": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": title}
                    }
                ]
            }
        }
        
        # Tags 추가
        if tags:
            properties["Tags"] = {
                "multi_select": [{"name": tag} for tag in tags]
            }
        
        # 페이지 생성
        page = self.client.pages.create(
            parent=parent,
            properties=properties,
            children=content_blocks
        )
        
        return page
    
    def query_database(self, filter_condition: Optional[dict] = None) -> list:
        """
        데이터베이스 쿼리
        
        Args:
            filter_condition: 필터 조건
        
        Returns:
            페이지 목록
        """
        query = {"database_id": self.database_id}
        if filter_condition:
            query["filter"] = filter_condition
        
        response = self.client.databases.query(**query)
        return response.get("results", [])
    
    def get_page(self, page_id: str) -> dict:
        """
        페이지 정보 조회
        
        Args:
            page_id: Notion 페이지 ID
        
        Returns:
            페이지 정보
        """
        return self.client.pages.retrieve(page_id)
    
    def update_page(
        self,
        page_id: str,
        blocks: Optional[list] = None,
        properties: Optional[dict] = None
    ) -> dict:
        """
        페이지 수정
        
        Args:
            page_id: Notion 페이지 ID
            blocks: 업데이트할 블록
            properties: 업데이트할 속성
        
        Returns:
            수정된 페이지 정보
        """
        data = {}
        if blocks:
            data["children"] = blocks
        if properties:
            data["properties"] = properties
        
        return self.client.pages.update(page_id, **data)


def _parse_inline_rich_text(text: str) -> list:
    """
    텍스트에서 인라인 코드(`code`)를 파싱해 Notion rich_text 리스트로 변환
    """
    import re
    parts = re.split(r'`([^`]+)`', text)
    rich_text = []
    for idx, segment in enumerate(parts):
        if not segment:
            continue
        if idx % 2 == 0:
            rich_text.append({"type": "text", "text": {"content": segment}})
        else:
            rich_text.append({
                "type": "text",
                "text": {"content": segment},
                "annotations": {"code": True}
            })
    return rich_text


def create_notion_block_from_markdown(markdown: str) -> list:
    """
    Markdown을 Notion block으로 변환

    Args:
        markdown: 마크다운 텍스트

    Returns:
        Notion block 목록
    """
    import re
    blocks = []
    lines = markdown.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        # fenced code block
        if line.startswith("```"):
            lang = line[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                    "language": lang
                }
            })
        # 제목
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]}
            })
        elif line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]}
            })
        elif line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]}
            })
        # 목록
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _parse_inline_rich_text(line[2:].strip())}
            })
        # 번호 목록
        elif line.strip().startswith(("1.", "2.", "3.", "4.", "5.")):
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": _parse_inline_rich_text(line.strip()[2:].strip())}
            })
        # 인용문
        elif line.startswith("> "):
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}],
                    "emoji": "💡"
                }
            })
        # 사진 (간단한 처리)
        elif line.startswith("![](") or line.startswith("![") or line.startswith("<img"):
            url_match = re.search(r'\(([^)]+)\)', line)
            if url_match:
                url = url_match.group(1)
                blocks.append({
                    "object": "block",
                    "type": "image",
                    "image": {"type": "external", "external": {"url": url}}
                })
        # 빈 줄
        elif line.strip() == "":
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": []}
            })
        # 일반 텍스트 (인라인 코드 포함)
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _parse_inline_rich_text(line)}
            })

        i += 1

    return blocks
