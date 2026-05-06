import joblib
import random

# Load model once
model = joblib.load("model/crop_model.pkl")


def predict_crop_util(N, P, K, temperature, humidity, ph, rainfall):
    data = [[N, P, K, temperature, humidity, ph, rainfall]]
    prediction = model.predict(data)
    return prediction[0]


def predict_price_util(base_price, month):
    # seasonal factor
    if month in ["apr", "may", "jun", "jul"]:
        seasonal_factor = 1.1
    elif month in ["nov", "dec", "jan"]:
        seasonal_factor = 0.9
    else:
        seasonal_factor = 1.0

    # demand factor
    demand_factor = random.uniform(0.95, 1.1)

    predicted_price = int(base_price * seasonal_factor * demand_factor)

    if predicted_price > base_price:
        trend = "📈 Increasing"
    elif predicted_price < base_price:
        trend = "📉 Decreasing"
    else:
        trend = "➡ Stable"

    return predicted_price, trend