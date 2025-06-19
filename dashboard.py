# dashboard.py
import pandas as pd
from warrant_scraper import get_all_warrants, get_warrant_history, fetch_fx_rate
from analysis import monte_carlo_price, bs_delta, kelly_fraction


def analyze_warrants(investment):
    warrants = get_all_warrants()
    results = []
    fx_rate = fetch_fx_rate('USD', 'VND')
    for idx, row in warrants.iterrows():
        symbol = row['symbol']
        try:
            hist = get_warrant_history(symbol)
            if len(hist) < 30:
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
    df['capital'] = (df['kelly'] / df['kelly'].sum()) * investment
    return df


def main():
    investment = float(input("Nhập số vốn đầu tư (VNĐ): "))
    df = analyze_warrants(investment)
    print("\nDashboard các chứng quyền định giá rẻ và có lãi:")
    print(df[['symbol', 'market_price', 'model_price', 'profit', 'delta', 'kelly', 'action', 'capital']])

if __name__ == "__main__":
    main()
