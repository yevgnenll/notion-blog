"""Telegram Bot 라우트"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Telegram bot update model
class TelegramUpdate(BaseModel):
    update_id: int
    message: Optional[dict] = None
    edited_message: Optional[dict] = None


@router.post("/webhook")
async def telegram_webhook(update: TelegramUpdate):
    """Telegram webhook handler"""
    # 메시지 처리
    if update.message:
        chat_id = update.message["chat"]["id"]
        text = update.message.get("text", "")
        
        # /start 명령어
        if text == "/start":
            response_text = "안녕하세요! 블로그 생성기를 시작합니다.\n\n명령어:\n/query - NotebookLM에 질문하기"
            await send_telegram_message(chat_id, response_text)
        
        # /query 명령어
        elif text.startswith("/query "):
            question = text[7:]  # "/query " 제거
            await handle_blog_query(chat_id, question)
        
        # 일반 질문
        else:
            response_text = "질문을 하려면 /query [질문]的形式으로 사용해주세요."
            await send_telegram_message(chat_id, response_text)
    
    return {"status": "ok"}


async def handle_blog_query(chat_id: int, question: str):
    """블로그 질문 처리"""
    try:
        from agent.notebooklm import NotebookLMClient
        from agent.brain import BlogBrain
        from integrations.notion import NotionClient, create_notion_block_from_markdown
        
        # NotebookLM에 질문
        client = NotebookLMClient()
        response = client.ask_question(question=question)
        
        # 블로그 생성
        brain = BlogBrain()
        blog_post = brain.generate_blog_from_notebook_response(
            question=question,
            notebook_response=response
        )
        
        # Notion에 게시
        notion = NotionClient()
        blocks = create_notion_block_from_markdown(blog_post["markdown"])
        page = notion.create_post(
            title=blog_post["title"],
            content_blocks=blocks
        )
        
        # 결과 전송
        result_text = (
            f"✅ 블로그 포스트가 생성되었습니다!\n\n"
            f"제목: {blog_post['title']}\n"
            f"Notion URL: {page.get('url', 'N/A')}"
        )
        await send_telegram_message(chat_id, result_text)
        
    except Exception as e:
        error_text = f"❌ 오류 발생: {str(e)}"
        await send_telegram_message(chat_id, error_text)


async def send_telegram_message(chat_id: int, text: str):
    """Telegram 메시지 전송 (async 버전 - 구현 필요)"""
    # 실제 구현 시 python-telegram-bot 사용
    # bot = Bot(token=CONFIG["telegram_token"])
    # await bot.send_message(chat_id=chat_id, text=text)
    pass
