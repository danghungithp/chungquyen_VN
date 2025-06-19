from warrant_scraper import get_warrant_history

symbols = ["cvic2502", "cstb2507"]
for symbol in symbols:
    try:
        hist = get_warrant_history(symbol)
        print(f"{symbol}: {len(hist) if hist is not None else 0} dòng dữ liệu")
        print(hist.head())
    except Exception as e:
        print(f"{symbol}: Lỗi - {e}")
