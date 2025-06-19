# main.py (mở rộng)
from warrant_scraper import fetch_warrant_price
from data_fetch import fetch_stb, estimate_garch
from analysis import analyze
from shap_analysis import analyze_shap
from portfolio import port

df = fetch_stb()
df = estimate_garch(df)

# Lấy giá warrant
market_price = fetch_warrant_price('STB.W')
res = analyze(df, market_price)

# Tích hợp SHAP nếu có đủ records
# explainer, model = analyze_shap(full_df)

# Cập nhật portfolio
port.loc['STB.W'] = [market_price, df['vol'].iloc[-1], res['delta'], res['kelly'], res['action']]

# Xác định đơn vị VNĐ với tỷ giá hiện hành
usd_vnd_rate = fetch_fx_rate('USD', 'VND')
port['value_vnd'] = port['warrant_price'] * port['position'] * usd_vnd_rate

