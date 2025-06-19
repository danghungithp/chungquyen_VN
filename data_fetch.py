# data_fetch.py
import logging
import pandas as pd
from vnstock import stock_historical_data

def fetch_stb():
    df = stock_historical_data("STB", start_date=None, end_date=None)
    df = df.tail(120).copy()
    df['ret'] = 100 * df['close'].pct_change()
    df.to_csv("STB_120.csv", index=False)
    logging.info("Data STB downloaded")
    return df

def estimate_garch(df):
    from arch import arch_model
    series = df['ret'].dropna()
    model = arch_model(series, vol='Garch', p=1, q=1)
    res = model.fit(disp='off')
    df['vol'] = res.conditional_volatility
    logging.info("GARCH fitted | sigma latest = %.4f", df['vol'].iloc[-1])
    return df
