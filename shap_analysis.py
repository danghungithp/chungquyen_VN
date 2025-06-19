# shap_analysis.py
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import shap

def analyze_shap(df):
    X = df.drop(['warrant_price'], axis=1)
    y = df['warrant_price']
    model = RandomForestRegressor(n_estimators=100)
    model.fit(X, y)
    explainer = shap.TreeExplainer(model)
    shap.summary_plot(explainer.shap_values(X), X)
    return explainer, model
