import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://stock.naver.com/api/domestic/detail/{item_code}/ETFComponent"
CSV_COLUMNS = ("구성종목명", "주식수(계약수)", "구성비중(%)")


def format_number(value: object) -> str:
	"""API 숫자 문자열의 불필요한 소수점 0을 제거합니다."""
	if value is None or value == "":
		return ""
	try:
		return format(Decimal(str(value)).normalize(), "f")
	except InvalidOperation:
		return str(value)


def fetch_components(item_code: str) -> list[dict[str, str]]:
	url = API_URL.format(item_code=item_code)
	request = Request(
		url,
		headers={
			"User-Agent": "Mozilla/5.0",
			"Referer": f"https://stock.naver.com/domestic/stock/{item_code}/info/analysis",
		},
	)

	try:
		with urlopen(request, timeout=20) as response:
			payload = json.load(response)
	except (HTTPError, URLError, TimeoutError) as error:
		raise RuntimeError(f"네이버 증권 API 요청에 실패했습니다: {error}") from error
	except json.JSONDecodeError as error:
		raise RuntimeError("API 응답을 JSON으로 읽을 수 없습니다.") from error

	if not isinstance(payload, list):
		raise RuntimeError("예상한 구성종목 목록 형식이 아닙니다.")

	rows = []
	for component in payload:
		if not isinstance(component, dict):
			continue
		rows.append(
			{
				CSV_COLUMNS[0]: str(component.get("componentName", "")),
				CSV_COLUMNS[1]: format_number(component.get("cuUnitQuantity")),
				CSV_COLUMNS[2]: format_number(component.get("weight")),
			}
		)
	return rows


def main() -> None:
	parser = argparse.ArgumentParser(description="네이버 증권 ETF의 CU당 구성종목을 CSV로 저장합니다.")
	parser.add_argument("--code", default="102110", help="ETF 종목코드 (기본값: 102110, TIGER 200)")
	parser.add_argument("--output", type=Path, help="CSV 저장 경로")
	args = parser.parse_args()

	output_path = args.output or Path(__file__).with_name(f"etf_{args.code}_components.csv")
	components = fetch_components(args.code)
	if not components:
		raise RuntimeError("구성종목 데이터가 없습니다. 종목코드 또는 API 응답을 확인하세요.")

	with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
		writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
		writer.writeheader()
		writer.writerows(components)

	print(f"{len(components)}개 종목을 저장했습니다: {output_path}")


if __name__ == "__main__":
	main()
