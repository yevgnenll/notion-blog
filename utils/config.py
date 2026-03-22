"""설정 관리 모듈"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def load_notion_db_id() -> str:
    """Notion DB ID를 환경변수에서 직접 로드 (이미 파싱된 ID 사용)"""
    db_id = os.getenv("NOTION_DATABASE_ID")
    if not db_id:
        # fallback: URL에서 파싱
        url = os.getenv("NOTION_DB_URL")
        if not url:
            raise ValueError("NOTION_DATABASE_ID or NOTION_DB_URL is required")
        
        parts = url.split("/")
        for part in parts:
            if len(part) == 32:
                return part
            if "-" in part and len(part.replace("-", "")) == 32:
                return part.replace("-", "")
        
        raise ValueError(f"Could not parse DB ID from URL: {url}")
    return db_id


def load_notion_integration_key() -> str:
    """Notion Integration Token 로드 (우선 사용)"""
    token = os.getenv("NOTION_INTEGRATION_KEY")
    if not token:
        # fallback:老 key
        token = os.getenv("NOTION_KEY")
        if not token:
            raise ValueError("NOTION_INTEGRATION_KEY or NOTION_KEY environment variable is required")
    return token


def load_telegram_token() -> str:
    """Telegram Bot Token 로드"""
    token = os.getenv("TELEGRAM_BOT_KEY")
    if not token:
        raise ValueError("TELEGRAM_BOT_KEY environment variable is required")
    return token


def load_openai_api_key() -> str:
    """OpenAI API Key 로드"""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return key


def load_notebooklm_notebook_id() -> str:
    """NotebookLM Notebook ID 로드 (선택사항 - 나중에 설정 가능)"""
    notebook_id = os.getenv("NOTEBOOKLM_NOTEBOOK_ID")
    if not notebook_id:
        # 빈 값일 경우 None 반환 (나중에 수동 설정 가능)
        return ""
    return notebook_id


# 디렉토리 설정
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 전역 설정
CONFIG = {
    "notion_integration_key": load_notion_integration_key(),
    "notion_db_id": load_notion_db_id(),
    "telegram_token": load_telegram_token(),
    "openai_api_key": load_openai_api_key(),
    "notebooklm_notebook_id": load_notebooklm_notebook_id(),
    "data_dir": DATA_DIR,
}
