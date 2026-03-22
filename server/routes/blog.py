"""블로그 관련 라우트"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from agent.notebooklm import NotebookLMWrapper
from agent.brain import BlogBrain
from integrations.notion import NotionClient, create_notion_block_from_markdown

router = APIRouter()


# Request Models
class BlogQueryRequest(BaseModel):
    question: str
    notebook_id: Optional[str] = None


class BlogQueryResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class ImproveRequest(BaseModel):
    original_response: str
    improvement_request: str
    topic: Optional[str] = None


# Routes
@router.post("/query", response_model=BlogQueryResponse)
async def query_notebooklm(request: BlogQueryRequest):
    """NotebookLM에 질문하고 결과 가져오기"""
    try:
        client = NotebookLMWrapper()
        response = client.ask_question(
            question=request.question,
            notebook_id=request.notebook_id
        )
        
        # 블로그 생성
        brain = BlogBrain()
        blog_post = brain.generate_blog_from_notebook_response(
            question=request.question,
            notebook_response=response
        )
        
        # Notion에 게시
        notion = NotionClient()
        blocks = create_notion_block_from_markdown(blog_post["markdown"])
        page = notion.create_post(
            title=blog_post["title"],
            content_blocks=blocks
        )
        
        blog_post["notion_page"] = page
        
        return BlogQueryResponse(success=True, data=blog_post)
    except Exception as e:
        return BlogQueryResponse(success=False, error=str(e))


@router.post("/improve")
async def improve_response(request: ImproveRequest):
    """NotebookLM 응답 개선"""
    try:
        brain = BlogBrain()
        improved = brain.improve_response(
            original_response=request.original_response,
            improvement_request=request.improvement_request,
            topic=request.topic
        )
        
        return {"success": True, "improved_response": improved}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/generate")
async def generate_blog(request: BlogQueryRequest):
    """NotebookLM 질문 -> 블로그 생성 -> Notion 게시"""
    try:
        client = NotebookLMWrapper()
        response = client.ask_question(
            question=request.question,
            notebook_id=request.notebook_id
        )
        
        brain = BlogBrain()
        blog_post = brain.generate_blog_from_notebook_response(
            question=request.question,
            notebook_response=response
        )
        
        notion = NotionClient()
        blocks = create_notion_block_from_markdown(blog_post["markdown"])
        page = notion.create_post(
            title=blog_post["title"],
            content_blocks=blocks
        )
        
        blog_post["notion_page"] = page
        
        return {"success": True, "data": blog_post}
    except Exception as e:
        return {"success": False, "error": str(e)}
