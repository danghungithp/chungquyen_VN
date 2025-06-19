# analysis.py
import numpy as np, pandas as pd, logging
from mpmath import erf, sqrt

def monte_carlo_price(S0, sigma, r=0.05, T=30/252, K=None, N=20000):
    if K is None: K = S0
    dt = T / (252 * T)
    paths = S0 * np.exp(np.cumsum((r-0.5*sigma**2)*dt + sigma*np.sqrt(dt)*np.random.randn(N,int(252*T)), axis=1))
    payoffs = np.maximum(paths[:,-1]-K, 0)
    return np.exp(-r*T) * payoffs.mean()

def bs_delta(S, K, sigma, r=0.05, T=30/252):
    d1 = (np.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    return 0.5*(1+erf(d1/sqrt(2)))

def kelly_fraction(edge, win_prob, loss_prob, payoff_ratio):
    return (win_prob * payoff_ratio - loss_prob) / payoff_ratio

def analyze(df):
    S0=df['close'].iloc[-1]; sigma=df['vol'].iloc[-1]/100
    r=0.05; T=30/252; K=S0
    model_price = monte_carlo_price(S0, sigma, r, T, K)
    # giả định thị trường có warrant thị trường:
    market_price = float(input("Nhập giá warrant market: "))
    delta = bs_delta(S0, K, sigma, r, T)
    logging.info("MC=%.3f | Market=%.3f | Delta=%.3f", model_price, market_price, delta)
    if model_price < market_price:
        action = "SHORT warrant + LONG {:.2f} shares".format(delta)
    else:
        action = "LONG warrant + SHORT {:.2f} shares".format(delta)
    logging.info("Action: %s", action)
    edge = abs(market_price - model_price) / market_price
    Kelly = kelly_fraction(edge, 0.55, 0.45, payoff_ratio=1)  # giả định
    logging.info("Kelly fraction ≈ %.3f", Kelly)
    return {"model": model_price, "market": market_price, "delta": delta, "action": action, "kelly": Kelly}
