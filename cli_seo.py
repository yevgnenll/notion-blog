"""
Google Search Console 사이트맵 제출 CLI 도구 (OAuth2 인증 방식)
사용법: python cli_seo.py
"""
import os
import json
import sys
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 고정 설정값
SITE_URL = "https://blog.yevgnenll.me"
SITEMAP_URL = "https://blog.yevgnenll.me/sitemap.xml"

# 권한 범위 (Search Console 관리 권한)
SCOPES = ['https://www.googleapis.com/auth/webmasters']

def get_credentials():
    """OAuth2 인증 정보 가져오기 (최초 실행 시 브라우저 로그인)"""
    creds = None
    
    # 1. 기존에 저장된 인증 토큰 확인
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception:
            creds = None
    
    # 2. 인증 정보가 없거나 만료된 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 인증 토큰을 갱신 중입니다...")
            creds.refresh(Request())
        else:
            # 3. 브라우저 로그인 진행
            if not os.path.exists('client_secrets.json'):
                print("❌ 오류: 'client_secrets.json' 파일이 없습니다.")
                print("   구글 클라우드 콘솔에서 다운로드하여 프로젝트 루트에 넣어주세요.")
                sys.exit(1)
            
            print("🌐 브라우저를 열어 구글 계정 로그인을 진행해 주세요...")
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # 4. 다음 실행을 위해 토큰 저장
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds

def submit_sitemap():
    """사이트맵 제출 실행"""
    print(f"🚀 Google Search Console에 사이트맵 제출 시도 중...")
    
    try:
        creds = get_credentials()
        service = build('webmasters', 'v3', credentials=creds)
        
        # API 호출
        service.sitemaps().submit(
            siteUrl=SITE_URL,
            feedpath=SITEMAP_URL
        ).execute()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("\n" + "="*50)
        print(f"✅ 성공: 사이트맵이 정상적으로 제출되었습니다!")
        print(f"⏰ 일시: {now}")
        print(f"🔗 사이트: {SITE_URL}")
        print(f"🗺️ 사이트맵: {SITEMAP_URL}")
        print("="*50)
        
    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        message = error_details.get('error', {}).get('message', 'Unknown Google API Error')
        print(f"❌ 구글 API 오류: {message}")
    except Exception as e:
        print(f"❌ 내부 오류 발생: {str(e)}")

if __name__ == "__main__":
    print(f"--- Google Search Console Sitemap Submitter ---")
    print(f"대상: {SITE_URL}")
    print(f"사이트맵: {SITEMAP_URL}\n")
    
    confirm = input("검수가 완료되었나요? 사이트맵을 제출하시겠습니까? (y/n): ")
    if confirm.lower() == 'y':
        submit_sitemap()
    else:
        print("⏹️ 제출이 취소되었습니다.")
