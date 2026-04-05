"""SEO 및 Google Search Console 관련 라우트"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

router = APIRouter()

# Request Models
class SitemapSubmitRequest(BaseModel):
    site_url: str
    sitemap_url: str

class SitemapSubmitResponse(BaseModel):
    success: bool
    message: str
    submitted_at: str

# Google API Helper
def get_search_console_service():
    """Google Search Console API 서비스 객체 생성"""
    scopes = ['https://www.googleapis.com/auth/webmasters']
    
    # 환경 변수에서 구글 서비스 계정 키 파일 경로 가져오기
    # .env 파일에 GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json" 설정 필요
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not creds_path or not os.path.exists(creds_path):
        # 만약 파일 경로가 아니라 JSON 내용 자체가 환경 변수에 있다면 (Production 환경 고려)
        creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if creds_json:
            info = json.loads(creds_json)
            return build('webmasters', 'v3', credentials=service_account.Credentials.from_service_account_info(info, scopes=scopes))
        raise HTTPException(
            status_code=500, 
            detail="Google Service Account credentials not found. Please set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_JSON."
        )

    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    return build('webmasters', 'v3', credentials=creds)

# Routes
@router.post("/sitemap/submit", response_model=SitemapSubmitResponse)
async def submit_sitemap(request: SitemapSubmitRequest):
    """Google Search Console에 사이트맵 제출"""
    try:
        service = get_search_console_service()
        
        # Google Search Console API: Sitemaps.submit
        # site_url: Search Console에 등록된 사이트 URL
        # feedpath: 제출할 사이트맵 URL (전체 경로)
        service.sitemaps().submit(
            siteUrl=request.site_url,
            feedpath=request.sitemap_url
        ).execute()
        
        return SitemapSubmitResponse(
            success=True,
            message=f"Successfully submitted sitemap {request.sitemap_url} to site {request.site_url}",
            submitted_at=datetime.utcnow().isoformat() + "Z"
        )
        
    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        message = error_details.get('error', {}).get('message', 'Unknown Google API Error')
        return SitemapSubmitResponse(
            success=False,
            message=f"Google API Error: {message}",
            submitted_at=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return SitemapSubmitResponse(
            success=False,
            message=f"Internal Server Error: {str(e)}",
            submitted_at=datetime.utcnow().isoformat() + "Z"
        )
