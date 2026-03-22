"""Blog Generator - Main Entry Point"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from utils.config import CONFIG


def main():
    """Main entry point"""
    print("Blog Generator 시작...")
    print(f"NotebookLM Notebook ID: {CONFIG['notebooklm_notebook_id']}")
    print(f"Notion DB ID: {CONFIG['notion_db_id']}")
    print(f"Telegram Bot: {CONFIG['telegram_token'][:20]}...")
    
    # FastAPI 서버 실행
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
