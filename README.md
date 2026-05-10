# Blog Generator

NotebookLM에서 답변을 받아 Notion 데이터베이스에 블로그 포스트로 게시하는 CLI 도구입니다.
한·영 동시 발행과 인포그래픽 커버 이미지 생성, 사이트맵 제출까지 한 번에 처리합니다.

## 주요 기능

### 1. NotebookLM 노트북 관리
- 노트북 목록 조회 (소유 / 공유 구분 표시)
- 새 노트북 생성
- URL 소스를 노트북에 추가
- 대화형 질의 (최대 10턴까지 `conversation_id`를 유지하는 후속 질문 지원)
- 응답에 포함된 citations / references를 소스 제목과 함께 출력

### 2. 블로그 생성 → Notion 자동 게시 (`blog` / `bilingual`)
- `docs/seo-strategy.md` 가이드를 프롬프트에 주입해 SEO 친화적인 본문 생성
- NotebookLM 응답을 파싱해 Notion 블록으로 변환
  - `# 제목`, `태그: a, b, c`, `## / ###` 헤딩
  - bullet / numbered 리스트 (빈 줄이 없는 다음 줄은 직전 항목의 continuation으로 합침)
  - 코드 블록 (``` ... ```)
  - 인라인 마크다운: `**bold**`, `*italic*`, `` `code` ``, `$LaTeX$` (Notion equation으로 변환)
- Notion 페이지 구성
  - 상단에 `cleanUrl: /posts/<slug>` YAML 코드 블록 + 자동 목차
  - 제목 / 태그(multi_select) / 공개여부(false) / 작성일자 속성 자동 채움
  - 100개 초과 블록은 `PATCH /blocks/{id}/children`로 분할 append
- 슬러그 생성: ASCII 변환이 비어 있을 경우 `utils.ollama.translate_title_to_slug`로 폴백, 그래도 비면 오늘 날짜 사용
- 참고문헌 섹션을 `참고문헌` / `References` 헤딩으로 자동 부착 (인용문 300자 이상은 잘라냄)
- 호출 실패 시 `utils.retry.with_retry`로 재시도

### 3. 한·영 동시 발행 (`bilingual`)
- 한글 본문, 영문 본문, 인포그래픽 이미지를 `ThreadPoolExecutor`로 병렬 생성
- 영문 발행 시 citations가 비어 있으면 한글 결과의 citations / references를 폴백으로 사용
- 동일한 인포그래픽 이미지를 두 페이지의 커버 + 본문 이미지 블록으로 공유

### 4. Notion 커버 이미지 업로드
- NotebookLM이 만든 이미지 URL을 다운로드한 뒤 Notion `file_uploads` API(`single_part` 모드)로 업로드
- 업로드 성공 시 `file_upload_id`를 페이지 cover와 image 블록에 사용
- 업로드 실패 시 external URL로 자동 폴백

### 5. Google Search Console 사이트맵 제출 (`cli_seo.py`)
- OAuth2(데스크톱 앱) 흐름으로 인증, `token.json`에 토큰 저장 후 재사용
- `https://blog.yevgnenll.me/sitemap.xml`을 Search Console에 수동 제출
- 사용자 확인 프롬프트(`y/n`) 후에만 제출 진행

## 설치 및 실행

```bash
pip install -r requirements.txt
nlm login   # 또는 NOTEBOOKLM_COOKIES 환경변수 설정
python mvp_notebooklm.py <command>
```

## 명령어

```bash
python mvp_notebooklm.py list                       # 노트북 목록
python mvp_notebooklm.py create "My Research"       # 노트북 생성
python mvp_notebooklm.py query                      # 대화형 질의 (NOTEBOOKLM_NOTEBOOK_ID 사용)
python mvp_notebooklm.py add <notebook_id> <url>    # URL 소스 추가
python mvp_notebooklm.py blog "양자컴퓨팅의 미래"     # 한글 블로그 생성 + Notion 게시
python mvp_notebooklm.py bilingual "Quantum future" # 한·영 + 인포그래픽 동시 게시
python cli_seo.py                                   # 사이트맵 제출
```

## 환경 변수

`.env` 파일 또는 셸 환경에 다음을 설정하세요.

| 변수 | 설명 |
| --- | --- |
| `NOTEBOOKLM_NOTEBOOK_ID` | `query` / `blog` / `bilingual`에서 사용할 대상 노트북 ID |
| `NOTEBOOKLM_COOKIES` | Chrome 쿠키 (선택, `nlm login` 대안) |
| `NOTEBOOKLM_QUERY_TIMEOUT` | 쿼리 타임아웃 초 (기본 120) |
| `NOTION_INTEGRATION_KEY` | Notion Integration 토큰 (`NOTION_API_KEY`도 인식) |
| `NOTION_DATABASE_ID` | 블로그 포스트가 저장될 Notion 데이터베이스 ID |

## Notion 데이터베이스 스키마

게시할 데이터베이스에 다음 속성이 있어야 합니다.

- `제목` (title)
- `태그` (multi-select)
- `공개여부` (checkbox) — 생성 시 항상 `false`로 게시됨
- `작성일자` (date)

## Google Search Console 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성 후 **Google Search Console API** 활성화
2. **OAuth 클라이언트 ID (데스크톱 앱)**를 발급받아 `client_secrets.json`으로 프로젝트 루트에 저장
3. **OAuth 동의 화면**의 **Test users**에 사용 계정 이메일 추가
4. `python cli_seo.py` 최초 실행 시 브라우저 로그인 → `token.json`에 자격 증명 저장

- 대상 사이트: `https://blog.yevgnenll.me`
- 사이트맵: `https://blog.yevgnenll.me/sitemap.xml`
