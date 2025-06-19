# warrant_scraper.py
from vnstock import Listing, Quote, Trading
import pandas as pd
import datetime

def get_all_warrants():
    """Lấy danh sách tất cả mã chứng quyền niêm yết."""
    return Listing(source="VCI").all_covered_warrant()

def get_warrant_history(symbol, start="2020-01-01", end=None):
    """Lấy giá lịch sử (đồ thị nến) của chứng quyền. end=None sẽ lấy tới ngày hiện tại."""
    if end is None:
        end = datetime.date.today().strftime("%Y-%m-%d")
    # Sử dụng đúng thứ tự tham số cho Quote: source, symbol
    return Quote(source="VCI", symbol=symbol.upper()).history(start=start, end=end)

def get_warrant_intraday(symbol):
    """Lấy dữ liệu khớp lệnh trong ngày (intraday) của chứng quyền."""
    return Quote(symbol, source="VCI").intraday()

def get_warrant_price_depth(symbol):
    """Lấy khối lượng giao dịch theo bước giá (order book depth) của chứng quyền."""
    return Quote(symbol, source="VCI").price_depth()

def get_warrant_price_board(symbol):
    """Lấy thông tin bảng giá của chứng quyền."""
    return Trading(symbol, source="VCI").price_board([symbol])

def fetch_fx_rate(base="USD", quote="VND"):
    """Lấy tỷ giá ngoại tệ (ví dụ: USD/VND) từ vnstock."""
    from vnstock import Vnstock
    # Vnstock hỗ trợ lấy tỷ giá qua lớp Vnstock
    fx = Vnstock(symbol=f"{base}{quote}", source="MSN")
    df = fx.stock().quote.history()
    # Lấy tỷ giá mới nhất
    if not df.empty:
        return float(df['close'].iloc[-1])
    else:
        raise ValueError(f"Không lấy được tỷ giá {base}/{quote}")
