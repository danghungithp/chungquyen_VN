from flask import Flask, render_template_string, request
import pandas as pd
from warrant_scraper import get_all_warrants, get_warrant_history, get_warrant_intraday
from analysis import monte_carlo_price, bs_delta, kelly_fraction
import logging
import os
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import time
from datetime import datetime
from scipy.stats import norm

logging.getLogger('vnstock').setLevel(logging.ERROR)

app = Flask(__name__)

DATA_CSV = 'warrant_data.csv'
TRADE_CSV = 'warrant_trade_data.csv'

def analyze_warrants(investment):
    # Lấy danh sách tất cả mã chứng quyền còn giao dịch trên thị trường (Series)
    warrants = get_all_warrants()
    if hasattr(warrants, 'values'):
        symbols = warrants.values
    else:
        symbols = list(warrants)
    results = []
    for symbol in symbols:
        try:
            hist = get_warrant_history(symbol)
            if hist is None or len(hist) < 30 or 'close' not in hist:
                continue
            S0 = hist['close'].iloc[-1]
            sigma = hist['close'].pct_change().std() * (252 ** 0.5)
            r = 0.05
            T = 30/252
            K = S0
            model_price = monte_carlo_price(S0, sigma, r, T, K)
            market_price = S0
            delta = bs_delta(S0, K, sigma, r, T)
            edge = abs(market_price - model_price) / market_price
            Kelly = kelly_fraction(edge, 0.55, 0.45, payoff_ratio=1)
            action = "LONG" if model_price > market_price else "SHORT"
            profit = model_price - market_price
            results.append({
                'symbol': symbol,
                'market_price': market_price,
                'model_price': model_price,
                'delta': delta,
                'kelly': Kelly,
                'action': action,
                'profit': profit
            })
        except Exception as e:
            continue
    df = pd.DataFrame(results)
    df = df[df['profit'] > 0].sort_values('profit', ascending=False)
    # Phân bổ vốn theo Kelly
    if not df.empty:
        df['capital'] = (df['kelly'] / df['kelly'].sum()) * investment
    return df

# Nút tải dữ liệu: lấy top 20 mã, lưu vào file CSV
@app.route('/download', methods=['POST'])
def download_data():
    warrants = get_all_warrants()
    # Lấy toàn bộ mã chứng quyền
    if hasattr(warrants, 'values'):
        symbols = warrants.values
    else:
        symbols = list(warrants)
    results = []
    import time
    for symbol in symbols:
        try:
            hist = get_warrant_history(symbol)
            if hist is None or len(hist) < 30 or 'close' not in hist:
                continue
            S0 = hist['close'].iloc[-1]
            sigma = hist['close'].pct_change().std() * (252 ** 0.5)
            results.append({'symbol': symbol, 'close': S0, 'sigma': sigma})
            time.sleep(1)  # Thêm delay để tránh bị chặn API
        except Exception as e:
            continue
    df = pd.DataFrame(results)
    df.to_csv(DATA_CSV, index=False)
    return f'Đã tải dữ liệu mới nhất ({len(df)} mã)! Quay lại để phân tích.'

@app.route('/download_trade', methods=['POST'])
def download_trade_data():
    warrants = get_all_warrants()
    if hasattr(warrants, 'values'):
        symbols = warrants.values
    else:
        symbols = list(warrants)
    trade_results = []
    import time
    for symbol in symbols:
        try:
            intraday = get_warrant_intraday(symbol)
            if intraday is None or len(intraday) == 0:
                continue
            # Nếu intraday là DataFrame, thêm cột symbol để phân biệt
            if hasattr(intraday, 'assign'):
                intraday = intraday.assign(symbol=symbol)
                trade_results.append(intraday)
            time.sleep(1)  # Delay để tránh bị chặn API
        except Exception as e:
            continue
    if trade_results:
        df_trade = pd.concat(trade_results, ignore_index=True)
        df_trade.to_csv(TRADE_CSV, index=False)
        return f'Đã tải dữ liệu giao dịch ({len(df_trade)} dòng)! Quay lại để phân tích.'
    else:
        return 'Không có dữ liệu giao dịch nào được tải!'

# Nút phân tích: đọc file CSV, phân tích, định giá, xuất kết quả và biểu đồ
@app.route('/analyze', methods=['POST'])
def analyze_data():
    # Đọc dữ liệu cơ bản
    if not os.path.exists(DATA_CSV):
        return 'Chưa có dữ liệu, hãy tải dữ liệu trước!'
    df = pd.read_csv(DATA_CSV)
    # Đọc dữ liệu giao dịch nếu có
    trade_df = None
    if os.path.exists(TRADE_CSV):
        trade_df = pd.read_csv(TRADE_CSV)
    results = []
    for _, row in df.iterrows():
        try:
            S0 = row['close']
            sigma = row['sigma']
            r = 0.05
            T = 30/252
            K = S0
            model_price = monte_carlo_price(S0, sigma, r, T, K)
            market_price = S0
            delta = bs_delta(S0, K, sigma, r, T)
            edge = abs(market_price - model_price) / market_price
            Kelly = kelly_fraction(edge, 0.55, 0.45, payoff_ratio=1)
            action = "LONG" if model_price > market_price else "SHORT"
            profit = model_price - market_price
            # Thống kê giao dịch nếu có dữ liệu giao dịch
            trade_stats = {}
            if trade_df is not None:
                trades = trade_df[trade_df['symbol'] == row['symbol']]
                if not trades.empty:
                    trade_stats['volume_sum'] = trades['volume'].sum() if 'volume' in trades else None
                    trade_stats['trade_count'] = len(trades)
                    trade_stats['last_trade_price'] = trades['price'].iloc[-1] if 'price' in trades else None
            results.append({
                'symbol': row['symbol'],
                'market_price': market_price,
                'model_price': model_price,
                'delta': delta,
                'kelly': Kelly,
                'action': action,
                'profit': profit,
                **trade_stats
            })
        except Exception as e:
            continue
    df2 = pd.DataFrame(results)
    df2 = df2[df2['profit'] > 0].sort_values('profit', ascending=False)
    if df2.empty:
        return '<h3>Không có chứng quyền nào có lợi nhuận dương để phân tích!</h3><br><a href="/">Quay lại</a>'
    if not df2.empty:
        df2['capital'] = (df2['kelly'] / df2['kelly'].sum()) * 10000000
    # Vẽ biểu đồ
    fig, ax = plt.subplots(figsize=(8,4))
    df2.head(10).plot.bar(x='symbol', y='profit', ax=ax, color='green')
    plt.title('Top 10 chứng quyền có lợi nhuận kỳ vọng cao nhất')
    plt.ylabel('Lợi nhuận kỳ vọng')
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    # Hiển thị bảng và biểu đồ
    table_html = df2.to_html(index=False, float_format='{:,.2f}'.format)
    html = f"""
    <h3>Kết quả phân tích chứng quyền</h3>
    <img src='data:image/png;base64,{img_base64}'/><br>
    {table_html}
    <br><a href='/'>Quay lại</a>
    """
    return html

def black_scholes_price(S, K, sigma, r=0.05, T=30/252, option_type='call'):
    from numpy import log, sqrt, exp
    d1 = (log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * exp(-r*T) * norm.cdf(d2)
    else:
        price = K * exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return float(price)

# Giao diện chính với 2 nút
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Chứng Quyền</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        .input-form { margin-bottom: 30px; }
        button { padding: 8px 16px; margin-right: 10px; }
    </style>
</head>
<body>
    <h2>Dashboard Chứng Quyền Định Giá Rẻ & Có Lãi</h2>
    <form method="post" action="/download" class="input-form">
        <button type="submit">Tải dữ liệu cơ bản</button>
    </form>
    <form method="post" action="/download_trade" class="input-form">
        <button type="submit">Tải dữ liệu giao dịch</button>
    </form>
    <form method="post" action="/analyze" class="input-form">
        <button type="submit">Phân tích</button>
    </form>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    result_html = ''
    symbol = ''
    investment = 10000000
    # Default values for user input
    stock_price = 0
    strike_price = 0
    expiry_date = ''
    risk_free = 4.5
    sigma = 0.3
    ratio = 1
    if request.method == 'POST':
        symbol = request.form.get('symbol', '').strip().upper()
        try:
            investment = float(request.form.get('investment', 10000000))
        except Exception:
            investment = 10000000
        try:
            stock_price = float(request.form.get('stock_price', 0))
            strike_price = float(request.form.get('strike_price', 0))
            expiry_date = request.form.get('expiry_date', '')
            risk_free = float(request.form.get('risk_free', 4.5))
            sigma = float(request.form.get('sigma', 0.3))
            ratio = float(request.form.get('ratio', 1))
        except Exception:
            pass
        try:
            # Tính thời gian đáo hạn thực tế (T, năm)
            if expiry_date:
                today = datetime.today().date()
                expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                T = max((expiry - today).days / 365, 1/252)
            else:
                T = 30/252
            r = risk_free / 100
            # Nếu người dùng nhập đủ thông tin, dùng thông tin nhập vào
            if stock_price > 0 and strike_price > 0 and sigma > 0 and ratio > 0:
                model_price_bs = black_scholes_price(stock_price, strike_price, sigma, r, T, option_type='call') / ratio
                result_html = f"""
                <h3>Kết quả định giá chứng quyền (Black-Scholes)</h3>
                <ul>
                    <li>Giá cổ phiếu cơ sở: {stock_price:,.2f}</li>
                    <li>Giá thực hiện: {strike_price:,.2f}</li>
                    <li>Ngày đáo hạn: {expiry_date}</li>
                    <li>Lãi suất phi rủi ro: {risk_free:.2f}%</li>
                    <li>Độ biến động kỳ vọng (sigma): {sigma:.4f}</li>
                    <li>Tỷ lệ chuyển đổi: {ratio:.2f}</li>
                    <li>Thời gian còn lại: {T:.4f} năm</li>
                    <li>Giá lý thuyết (Black-Scholes): <b>{model_price_bs:,.2f}</b></li>
                </ul>
                """
            else:
                # Nếu không nhập đủ, lấy dữ liệu như cũ
                hist = get_warrant_history(symbol)
                if hist is None or len(hist) < 30 or 'close' not in hist:
                    result_html = f"<p>Không đủ dữ liệu lịch sử cho mã {symbol}!</p>"
                else:
                    S0 = hist['close'].iloc[-1]
                    sigma = hist['close'].pct_change().std() * (252 ** 0.5)
                    r = 0.05
                    T = 30/252
                    K = S0
                    model_price_mc = monte_carlo_price(S0, sigma, r, T, K)
                    model_price_bs = black_scholes_price(S0, K, sigma, r, T, option_type='call')
                    market_price = S0
                    delta = bs_delta(S0, K, sigma, r, T)
                    edge = abs(market_price - model_price_mc) / market_price
                    Kelly = kelly_fraction(edge, 0.55, 0.45, payoff_ratio=1)
                    action = "LONG" if model_price_mc > market_price else "SHORT"
                    profit = model_price_mc - market_price
                    capital = float(Kelly) * investment if Kelly > 0 else 0
                    # Lấy dữ liệu giao dịch nếu có
                    trade_stats = ''
                    try:
                        intraday = get_warrant_intraday(symbol)
                        if intraday is not None and len(intraday) > 0:
                            vol_sum = intraday['volume'].sum() if 'volume' in intraday else 'N/A'
                            trade_count = len(intraday)
                            last_price = intraday['price'].iloc[-1] if 'price' in intraday else 'N/A'
                            trade_stats = f"<li>Tổng khối lượng giao dịch: {vol_sum}</li><li>Số lệnh: {trade_count}</li><li>Giá khớp cuối: {last_price}</li>"
                    except Exception:
                        pass
                    result_html = f"""
                    <h3>Kết quả phân tích mã {symbol}</h3>
                    <ul>
                        <li>Giá thị trường: {market_price:.2f}</li>
                        <li>Giá lý thuyết (Monte Carlo): {float(model_price_mc):.2f}</li>
                        <li>Giá lý thuyết (Black-Scholes): {float(model_price_bs):.2f}</li>
                        <li>Lợi nhuận kỳ vọng (Monte Carlo): {float(profit):.2f}</li>
                        <li>Delta: {float(delta):.2f}</li>
                        <li>Kelly: {float(Kelly):.2f}</li>
                        <li>Khuyến nghị: {action}</li>
                        <li>Vốn nên phân bổ: {float(capital):,.0f} VNĐ</li>
                        {trade_stats}
                    </ul>
                    """
        except Exception as e:
            result_html = f"<p>Lỗi khi phân tích mã {symbol}: {e}</p>"
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Phân tích chứng quyền</title>
        <style>
            body {{ font-family: Arial; margin: 40px; }}
            .input-form {{ margin-bottom: 30px; }}
            button {{ padding: 8px 16px; margin-right: 10px; }}
        </style>
    </head>
    <body>
        <h2>Phân tích, định giá chứng quyền</h2>
        <form method="post" class="input-form">
            <label>Nhập mã chứng quyền: </label>
            <input type="text" name="symbol" value="{symbol}" required>
            <label style="margin-left:20px">Số vốn đầu tư (VNĐ): </label>
            <input type="number" name="investment" value="{investment:.0f}" min="0" required>
            <br><br>
            <b>--- Hoặc nhập thông tin chi tiết để định giá Black-Scholes ---</b><br>
            <label>Giá cổ phiếu cơ sở: </label>
            <input type="number" name="stock_price" value="{stock_price}" step="0.01">
            <label style="margin-left:10px">Giá thực hiện: </label>
            <input type="number" name="strike_price" value="{strike_price}" step="0.01">
            <label style="margin-left:10px">Ngày đáo hạn: </label>
            <input type="date" name="expiry_date" value="{expiry_date}">
            <label style="margin-left:10px">Lãi suất phi rủi ro (%): </label>
            <input type="number" name="risk_free" value="{risk_free}" step="0.01">
            <label style="margin-left:10px">Sigma (biến động): </label>
            <input type="number" name="sigma" value="{sigma}" step="0.0001">
            <label style="margin-left:10px">Tỷ lệ chuyển đổi: </label>
            <input type="number" name="ratio" value="{ratio}" step="0.01">
            <br><br>
            <button type="submit">Phân tích</button>
        </form>
        <form method="post" action="/show_data" class="input-form">
            <input type="hidden" name="symbol" value="{symbol}">
            <button type="submit">Xem dữ liệu gốc</button>
        </form>
        {result_html}
    </body>
    </html>
    '''
    return html

@app.route('/show_data', methods=['POST'])
def show_data():
    symbol = request.form.get('symbol', '').strip().upper()
    hist_html = ''
    trade_html = ''
    try:
        hist = get_warrant_history(symbol)
        if hist is not None and len(hist) > 0:
            hist_html = '<h4>Lịch sử giá (close 10 phiên gần nhất):</h4>' + hist.tail(10).to_html(index=False)
    except Exception as e:
        hist_html = f'<p>Lỗi lấy lịch sử giá: {e}</p>'
    try:
        intraday = get_warrant_intraday(symbol)
        if intraday is not None and len(intraday) > 0:
            trade_html = '<h4>Giao dịch intraday (10 dòng cuối):</h4>' + intraday.tail(10).to_html(index=False)
    except Exception as e:
        trade_html = f'<p>Lỗi lấy dữ liệu giao dịch: {e}</p>'
    html = f'''
    <!DOCTYPE html>
    <html>
    <head><title>Dữ liệu chứng quyền</title></head>
    <body>
        <h2>Dữ liệu chứng quyền: {symbol}</h2>
        {hist_html}
        {trade_html}
        <br><a href="/">Quay lại</a>
    </body>
    </html>
    '''
    return html

if __name__ == '__main__':
    app.run(debug=True)
