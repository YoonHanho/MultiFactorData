"""네이버증권 추정실적 컨센서스를 연간/분기 DataFrame으로 가져옵니다."""

import json
import re
import ssl
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

CONSENSUS_PAGE_URL = (
    "https://navercomp.wisereport.co.kr/v3/company/c1050001.aspx"
)
CONSENSUS_DATA_URL = (
    "https://navercomp.wisereport.co.kr/v3/company/ajax/c1050001_data.aspx"
)
CONSENSUS_COLUMNS = [
    "FY-end",
    "주재무제표",
    "매출액 (억원)",
    "YoY (%)",
    "영업이익 (억원)",
    "당기순이익 (억원)",
    "EPS (원)",
    "BPS (원)",
    "PER (배)",
    "PBR (배)",
    "ROE (%)",
    "EV/EBITDA (배)",
]
STOCK_CODE_PATTERN = re.compile(r"(?:A)?\d{6}")
DATE_PATTERN = re.compile(
    r'<input\b[^>]*\bid=["\']hidDT["\'][^>]*\bvalue=["\'](\d{8})["\']',
    re.IGNORECASE,
)

API_COLUMN_MAP = {
    "FY-end": "YYMM",
    "주재무제표": "MAIN",
    "매출액 (억원)": "SALES",
    "YoY (%)": "YOY",
    "영업이익 (억원)": "OP",
    "당기순이익 (억원)": "NP",
    "EPS (원)": "EPS",
    "BPS (원)": "BPS",
    "PER (배)": "PER",
    "PBR (배)": "PBR",
    "ROE (%)": "ROE",
    "EV/EBITDA (배)": "EV",
}

COLUMN_MAP = {
    "매출액 (억원)": "매출액",
    "영업이익 (억원)": "영업이익",
    "당기순이익 (억원)": "당기순이익",
    "BPS (원)": "BPS(원)",
    "PER (배)": "PER(배)",
    "PBR (배)": "PBR(배)",
    "ROE (%)": "ROE(%)",
    "EV/EBITDA (배)": "EV/EBITDA(배)",
}


def _clean_stock_code(stock_code: str) -> str:
    clean_code = str(stock_code).strip()
    if not STOCK_CODE_PATTERN.fullmatch(clean_code):
        clean_code = clean_code.zfill(6)
        if not STOCK_CODE_PATTERN.fullmatch(clean_code):
            raise ValueError(f"올바르지 않은 종목코드 형식입니다: {stock_code}")
    return clean_code.removeprefix("A")


def _fetch_text(url: str, timeout: float, referer: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "Referer": referer,
            "Accept": "text/html,application/json",
        },
    )
    last_error = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode(
                    response.headers.get_content_charset() or "utf-8"
                )
        except (URLError, ssl.SSLError, ConnectionError, OSError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(1.0)
    if last_error is not None:
        raise last_error
    raise RuntimeError("네이버증권 데이터 요청에 실패했습니다.")


def _get_reference_date(stock_code: str, timeout: float) -> str:
    query = urlencode(
        {"cmp_cd": stock_code, "theme": "light", "cn": ""}
    )
    page_url = f"{CONSENSUS_PAGE_URL}?{query}"
    html = _fetch_text(page_url, timeout, page_url)
    match = DATE_PATTERN.search(html)
    if match is None:
        raise ValueError(
            "네이버증권 페이지에서 컨센서스 기준일을 찾지 못했습니다. "
            "페이지의 데이터 형식이 변경되었을 수 있습니다."
        )
    return match.group(1)


def get_naver_consensus(
    stock_code: str = "005930",
    timeout: float = 15,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """네이버증권에서 종목의 연간·분기 컨센서스를 가져옵니다."""
    company_code = _clean_stock_code(stock_code)
    reference_date = _get_reference_date(company_code, timeout)

    def fetch_frequency(frequency: str) -> pd.DataFrame:
        query = urlencode(
            {
                "flag": "2",
                "cmp_cd": company_code,
                "finGubun": "MAIN",
                "frq": frequency,
                "sDT": reference_date,
                "chartType": "svg",
            }
        )
        url = f"{CONSENSUS_DATA_URL}?{query}"
        response_text = _fetch_text(
            url,
            timeout,
            f"{CONSENSUS_PAGE_URL}?cmp_cd={company_code}",
        )
        response_data = json.loads(response_text)
        rows = response_data.get("JsonData")
        if not isinstance(rows, list) or not rows:
            raise ValueError(
                f"네이버증권에서 {frequency} 컨센서스 데이터를 찾지 못했습니다."
            )

        frame = pd.DataFrame(
            [
                {
                    column: row.get(api_key)
                    for column, api_key in API_COLUMN_MAP.items()
                }
                for row in rows
            ],
            columns=CONSENSUS_COLUMNS,
        )
        for column in CONSENSUS_COLUMNS[2:]:
            values = frame[column].astype("string").str.replace(
                ",", "", regex=False
            )
            frame[column] = pd.to_numeric(values, errors="coerce")
        return frame

    annual = fetch_frequency("0")
    quarterly = fetch_frequency("1")
    return annual, quarterly


def get_naver_finstate(
    stock_code: str,
    freq: str = "Y",
    timeout: float = 15,
) -> pd.DataFrame:
    """
    네이버증권 컨센서스를 기존 SnapDataReader와 호환되는 형태로 반환합니다.

    freq는 'Y'(연간) 또는 'Q'(분기)입니다.
    """
    annual_df, quarterly_df = get_naver_consensus(
        stock_code=stock_code,
        timeout=timeout,
    )
    is_annual = freq.upper().endswith("Y") or freq.upper() == "Y"
    frame = annual_df.copy() if is_annual else quarterly_df.copy()

    if "FY-end" in frame.columns:
        frame.set_index("FY-end", inplace=True)
        frame.index.name = "날짜"

    for original_column, target_column in COLUMN_MAP.items():
        if original_column in frame.columns:
            frame[target_column] = frame[original_column]

    return frame
