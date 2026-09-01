# 채용정보 자동 수집기

산업안전/설비 분야 공무직·계약직 채용정보를 매일 자동으로 모아
텔레그램으로 알려주는 스크립트입니다.

- **공공기관** (`config.py` 의 `SITES`): 각 기관 채용페이지를 직접 파싱
- **민간기업** (대구·영천·경산): 사람인 검색 결과를 지역+키워드로 크롤링

## 1. 로컬 테스트

```bash
pip install -r requirements.txt
python main.py
```

`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` 환경변수가 없으면 알림 대신
콘솔에 결과가 출력됩니다. 먼저 이렇게 콘솔 출력으로 각 사이트가 잘
파싱되는지 확인해 보세요.

**주의**: `parse_generic_table` 은 범용 파서라 사이트 구조에 따라
제목이 아닌 엉뚱한 텍스트가 섞이거나, 반대로 실제 공고를 못 찾을 수
있습니다. 사이트별로 결과를 확인해서 이상하면 알려주시면 전용 파서로
다듬어 드릴게요.

### PDF / HWP 첨부파일 처리

- 게시판 목록에서 제목뿐 아니라 같은 행의 **첨부파일 링크(PDF/HWP)** 도 함께 수집합니다.
- 제목에 키워드가 없어도, **PDF 첨부파일을 열어서 본문 텍스트 안에 키워드가 있는지** 확인합니다.
  일치하면 알림에 해당 문구 주변 내용(스니펫)까지 함께 보내줍니다.
- **HWP(한글) 파일은 텍스트 추출을 지원하지 않습니다.** 대신 "HWP 첨부파일 있음 -
  직접 확인 필요"라고 알림에 표시만 됩니다. HWP까지 자동으로 읽게 하려면
  `pyhwp` 등 별도 라이브러리 연동이 필요한데, 설치가 까다로운 편이라 필요하시면
  별도로 도와드릴게요.
- 스캔본 PDF(이미지로만 된 공고문)는 텍스트 추출이 안 될 수 있습니다. 이 경우도
  OCR(예: Tesseract) 연동이 필요합니다.

## 2. 텔레그램 봇 만들기 (5분)

1. 텔레그램에서 `@BotFather` 검색 → `/newbot` → 안내에 따라 봇 이름 설정
2. 발급받은 토큰이 `TELEGRAM_BOT_TOKEN`
3. 만든 봇과 대화를 한 번 시작(아무 메시지나 전송)
4. 브라우저로 `https://api.telegram.org/bot<토큰>/getUpdates` 접속 →
   `"chat":{"id": 숫자}` 부분이 `TELEGRAM_CHAT_ID`

## 3. GitHub 레포에 올리고 자동화하기

1. 이 폴더를 새 GitHub 저장소로 push
2. 저장소 **Settings → Secrets and variables → Actions** 에서
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 등록
3. **Settings → Actions → General → Workflow permissions** 에서
   "Read and write permissions" 선택 (state.json 자동 커밋을 위해 필요)
4. `.github/workflows/crawl.yml` 이 매일 08:00(KST)에 자동 실행됨
   (Actions 탭에서 "Run workflow" 버튼으로 즉시 테스트도 가능)

## 4. 필터 키워드 / 대상 기관 수정

`config.py` 상단의 `KEYWORDS` 리스트와 `SITES` 리스트를 수정하면
관심 직무나 모니터링 대상 기관을 바꿀 수 있습니다.

아직 채용페이지 URL을 못 찾은 대구혁신도시 소재 기관(한국사학진흥재단,
한국산업기술기획평가원, 한국로봇산업진흥원, 대구경북첨단의료산업진흥재단,
한국물기술인증원 등)은 URL이 확인되면 `SITES` 에 같은 형식으로
추가하면 됩니다.
