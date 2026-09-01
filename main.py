# -*- coding: utf-8 -*-
"""
채용정보 자동 수집 스크립트

사용법:
    python main.py

동작:
    1. config.py 의 SITES(공공기관)를 순회하며 채용공고 게시판을 파싱
    2. 사람인에서 대구/영천/경산 지역 + 키워드로 민간기업 공고를 검색
    3. state.json 에 저장된 이전 결과와 비교해서 "새로 뜬 공고"만 추림
    4. 새 공고가 있으면 텔레그램으로 알림 발송, state.json 갱신

환경변수 (GitHub Actions Secrets 로 설정):
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import io

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

import config

STATE_FILE = Path(__file__).parent / "state.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 15


# ────────────────────────────────────────────────────────────
# 파서
# ────────────────────────────────────────────────────────────
ATTACHMENT_HINTS = ("download", "file", ".pdf", ".hwp", ".hwpx", ".doc")


def _extract_attachments(tr, base_url: str):
    """행(tr) 안에서 첨부파일로 보이는 링크들을 뽑아냄 (PDF/HWP 등)"""
    attachments = []
    for a in tr.find_all("a"):
        href = (a.get("href") or "").lower()
        if not href or href.startswith("javascript"):
            continue
        if any(hint in href for hint in ATTACHMENT_HINTS):
            full_url = a.get("href")
            if not full_url.startswith("http"):
                full_url = requests.compat.urljoin(base_url, full_url)
            kind = "pdf" if ".pdf" in href else ("hwp" if "hwp" in href else "file")
            attachments.append({"url": full_url, "type": kind})
    return attachments


def parse_generic_table(html: str, base_url: str):
    """
    대부분의 공공기관 게시판(표준프레임워크 selectNttList.do, goBoard.do 계열 등)에
    공통적으로 쓰이는 <table> 기반 목록을 파싱하는 범용 함수.

    - <table> 안의 각 <tr> 을 검사
    - 그 안에 있는 <a> 태그 중 텍스트 길이가 6자 이상인 것을 "공고 제목"으로 간주
    - 같은 행(tr) 안에 PDF/HWP 등 첨부파일 링크가 있으면 함께 수집
    - 페이지마다 구조가 조금씩 달라 100% 정확하지는 않으므로, 사이트별로 결과를
      확인해서 필요하면 전용 파서로 교체하는 걸 권장

    반환: [{"title": str, "link": str, "attachments": [{"url","type"}, ...]}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen_titles = set()

    tables = soup.find_all("table")
    for table in tables:
        for tr in table.find_all("tr"):
            # 헤더 행(th만 있는 행)은 스킵
            if tr.find("th") and not tr.find("td"):
                continue

            attachments = _extract_attachments(tr, base_url)

            for a in tr.find_all("a"):
                title = a.get_text(strip=True)
                if len(title) < 6:
                    continue
                if title in seen_titles:
                    continue
                # 페이지네이션/메뉴성 텍스트, 첨부파일 링크 자체는 제목 후보에서 제외
                if title in ("처음페이지", "이전페이지", "다음페이지", "마지막페이지"):
                    continue
                href = (a.get("href") or "").lower()
                if any(hint in href for hint in ATTACHMENT_HINTS):
                    continue

                full_href = a.get("href")
                link = base_url
                if full_href and full_href.startswith("http"):
                    link = full_href
                elif full_href and not full_href.startswith("javascript"):
                    link = requests.compat.urljoin(base_url, full_href)

                seen_titles.add(title)
                results.append(
                    {"title": title, "link": link, "attachments": attachments}
                )

    return results


def extract_pdf_text(url: str, max_pages: int = 5) -> str:
    """PDF 첨부파일을 다운로드해서 텍스트를 추출. 실패하면 빈 문자열 반환."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        reader = PdfReader(io.BytesIO(resp.content))
        text_parts = []
        for page in reader.pages[:max_pages]:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as e:  # noqa: BLE001
        print(f"[경고] PDF 추출 실패 ({url}): {e}", file=sys.stderr)
        return ""


def find_keyword_snippet(text: str, keywords, context: int = 60) -> str:
    """텍스트에서 키워드가 처음 발견된 위치 주변을 잘라서 반환"""
    for kw in keywords:
        idx = text.find(kw)
        if idx != -1:
            start = max(0, idx - context)
            end = min(len(text), idx + len(kw) + context)
            snippet = text[start:end].strip().replace("\n", " ")
            return f"...{snippet}..."
    return ""


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp.text


def crawl_public_sites():
    """공공기관 사이트를 순회하며 채용공고 목록을 수집"""
    all_results = {}
    for site in config.SITES:
        name = site["name"]
        try:
            html = fetch(site["url"])
            parser_fn = globals()[site["parser"]]
            postings = parser_fn(html, site["url"])
        except Exception as e:  # noqa: BLE001
            print(f"[경고] {name} 크롤링 실패: {e}", file=sys.stderr)
            postings = []
        all_results[name] = {
            "category": site["category"],
            "postings": postings,
        }
        time.sleep(1)  # 서버 부담을 줄이기 위한 딜레이
    return all_results


# ────────────────────────────────────────────────────────────
# 민간기업 (사람인 지역+키워드 검색)
# ────────────────────────────────────────────────────────────
def search_saramin():
    """
    사람인 검색 결과 페이지를 지역+키워드 조합으로 크롤링.
    사람인은 검색 파라미터가 자주 바뀔 수 있어서, 동작하지 않으면
    실제 검색 URL을 사람인 사이트에서 직접 확인해 loc_cd, cat_kw 등을 갱신해야 함.
    """
    results = []
    base = "https://www.saramin.co.kr/zf_user/search/recruit"
    for region in config.SARAMIN_REGIONS:
        for kw in config.KEYWORDS:
            query = f"{region} {kw}"
            params = {"searchword": query}
            try:
                resp = requests.get(
                    base, params=params, headers=HEADERS, timeout=TIMEOUT
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".item_recruit")
                for item in items:
                    title_tag = item.select_one(".job_tit a")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    link = requests.compat.urljoin(
                        "https://www.saramin.co.kr", title_tag.get("href", "")
                    )
                    company_tag = item.select_one(".corp_name a")
                    company = (
                        company_tag.get_text(strip=True) if company_tag else "?"
                    )
                    results.append(
                        {
                            "title": f"[{company}] {title}",
                            "link": link,
                            "region": region,
                            "keyword": kw,
                        }
                    )
            except Exception as e:  # noqa: BLE001
                print(f"[경고] 사람인 검색 실패 ({query}): {e}", file=sys.stderr)
            time.sleep(1)
    return results


# ────────────────────────────────────────────────────────────
# 키워드 필터 / 변경분 감지 / 알림
# ────────────────────────────────────────────────────────────
def matches_keyword(title: str) -> bool:
    return any(kw in title for kw in config.KEYWORDS)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[알림 생략] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 미설정")
        print(text)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for i in range(0, len(text), 3500):  # 텔레그램 메시지 길이 제한 대응
        chunk = text[i : i + 3500]
        requests.post(
            url,
            data={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )


def main():
    state = load_state()
    prev_titles = set(state.get("seen_titles", []))
    new_titles = set()
    new_postings_msg = []

    # 1) 공공기관
    public_results = crawl_public_sites()
    for org_name, data in public_results.items():
        for p in data["postings"]:
            key = f"{org_name}::{p['title']}"
            new_titles.add(key)
            if key in prev_titles:
                continue  # 이미 이전에 확인한 공고

            # 제목에서 먼저 키워드 확인
            hit = matches_keyword(p["title"])
            snippet = ""
            pdf_note = ""

            # 제목에 키워드가 없어도, PDF 첨부파일 안에 키워드가 있을 수 있으므로 열어봄
            for att in p.get("attachments", []):
                if att["type"] == "pdf":
                    pdf_text = extract_pdf_text(att["url"])
                    if matches_keyword(pdf_text):
                        hit = True
                        snippet = find_keyword_snippet(pdf_text, config.KEYWORDS)
                elif att["type"] == "hwp":
                    # HWP는 텍스트 추출 미지원 - 첨부파일이 있다는 것만 알림에 표시
                    pdf_note = " (⚠️ HWP 첨부파일 있음 - 직접 확인 필요)"

            if hit:
                msg = f"[공공기관 | {org_name}] {p['title']}{pdf_note}\n{p['link']}"
                if snippet:
                    msg += f"\n📎 첨부파일 내용: {snippet}"
                new_postings_msg.append(msg)

    # 2) 민간기업 (사람인 지역+키워드)
    saramin_results = search_saramin()
    for p in saramin_results:
        key = f"saramin::{p['title']}"
        new_titles.add(key)
        if key not in prev_titles:
            new_postings_msg.append(
                f"[민간기업 | {p['region']}] {p['title']}\n{p['link']}"
            )

    # 3) 알림
    if new_postings_msg:
        header = f"🔔 새 채용공고 {len(new_postings_msg)}건\n\n"
        send_telegram(header + "\n\n".join(new_postings_msg))
    else:
        print("새로 감지된 공고가 없습니다.")

    # 4) 상태 저장
    state["seen_titles"] = sorted(new_titles)
    save_state(state)


if __name__ == "__main__":
    main()
