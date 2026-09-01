# -*- coding: utf-8 -*-
"""
채용정보 크롤링 대상 목록.

category: "공공기관" | "민간기업"
region:   대구/영천/경산 등 (민간기업 필터링용, 공공기관은 생략 가능)
url:      채용공고 게시판 URL
parser:   이 사이트를 처리할 파서 함수 이름 (scraper.py 의 함수명과 매칭)

키워드 필터(KEYWORDS)에 해당하는 단어가 공고 제목에 포함되면 관심 공고로 표시합니다.
자격증/직무에 맞게 자유롭게 수정하세요.
"""

KEYWORDS = [
    "산업안전", "안전관리", "안전보건", "설비", "시설", "소방",
    "가스", "공무직", "기술직", "기능직", "환경안전", "방재",
]

# 사람인 지역+키워드 검색에 사용할 키워드 (사용자 보유/취득 예정 자격증 기준)
SARAMIN_KEYWORDS = [
    "가스기능사", "산업안전기사", "소방안전관리자", "소방설비기사",
]

SITES = [
    # ── 공공기관 (대구혁신도시) ─────────────────────────────
    {
        "name": "한국뇌연구원(KBRI)",
        "category": "공공기관",
        "url": "https://www.kbri.re.kr/new/pages/sub/page.html?mc=0635",
        "parser": "parse_generic_table",
    },
    {
        "name": "한국지능정보사회진흥원(NIA)",
        "category": "공공기관",
        "url": "https://www.nia.or.kr/site/nia_kor/ex/bbs/List.do?cbIdx=60362",
        "parser": "parse_generic_table",
    },
    {
        "name": "한국산업단지공단(KICOX)",
        "category": "공공기관",
        "url": "https://www.kicox.or.kr/boardList/1019",
        "parser": "parse_generic_table",
    },
    {
        "name": "신용보증기금(KODIT)",
        "category": "공공기관",
        "url": "https://www.kodit.or.kr/kodit/na/ntt/selectNttList.do?mi=2518&bbsId=407",
        "parser": "parse_generic_table",
    },
    {
        "name": "한국교육학술정보원(KERIS)",
        "category": "공공기관",
        "url": "https://www.keris.or.kr/main/na/ntt/selectNttList.do?mi=1086&bbsId=1089",
        "parser": "parse_generic_table",
    },
    {
        "name": "한국가스공사(KOGAS)",
        "category": "공공기관",
        "url": "https://www.kogas.or.kr/site/koGas/goBoard.do?boardNo=44&Key=1010801000000",
        "parser": "parse_generic_table",
    },
    {
        "name": "한국부동산원(REB)",
        "category": "공공기관",
        "url": "https://www.reb.or.kr/recruit/na/ntt/selectNttList.do?mi=9916&bbsId=1251",
        "parser": "parse_generic_table",
    },
    # 아래는 대구신서혁신도시 소재로 추정되나 채용페이지 URL을 아직 확인 못한 기관입니다.
    # 실제 URL을 찾아서 채워 넣거나, 확인되면 알려주시면 추가해 드릴게요.
    # - 한국사학진흥재단
    # - 한국산업기술기획평가원
    # - 한국로봇산업진흥원 (북구)
    # - 대구경북첨단의료산업진흥재단
    # - 한국물기술인증원 (달성군)

    # ── 민간기업 (대구/영천/경산) ────────────────────────────
    # 사기업은 채용 페이지가 자주 바뀌거나 별도 채용 사이트(사람인/잡코리아)만 쓰는 경우가
    # 많아서, 개별 URL을 고정 관리하기보다 사람인 지역+키워드 검색 결과를 크롤링하는 방식을
    # 추천합니다. main.py 의 search_saramin() 함수가 이 역할을 합니다.
]

# 사람인에서 지역+키워드로 검색할 때 사용할 지역 코드
# (사람인 지역코드: 대구=D, 세부 지역은 사람인 URL에서 지역 선택 후 loc_mcd 값 참고)
SARAMIN_REGIONS = ["대구", "영천", "경산"]
