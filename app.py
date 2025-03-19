import datetime
from flask import Flask, json, request, jsonify, render_template, redirect, url_for
from flask_caching import Cache
import pandas as pd
import numpy as np
import requests
import pickle
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error

app = Flask(__name__)

app.config['CACHE_TYPE'] = 'SimpleCache' 
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  
cache = Cache(app)

# URL API Data
current_year =datetime.datetime.now().year
start_year = current_year - 2
end_year = current_year
API_URL = f"http://10.10.2.70:3008/api/energy-emission/energy?start_year={start_year}&end_year={current_year}&start_month=01&end_month=12&is_emission=false"

# Load model Prophet
with open('models/prophet_model.pkl', 'rb') as f:
    model = pickle.load(f)

def replace_nan_with_null(obj):
    if isinstance(obj, float) and np.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: replace_nan_with_null(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_with_null(v) for v in obj]
    return obj

@app.route('/')
def home_page():
    return redirect(url_for('forecast_page'))

@app.route('/forecast')
def forecast_page():
    return render_template('forecast.html')

@app.route('/data')
def data_page():
    return render_template('data.html')

@app.route('/about')
def about_page():
    return render_template('about.html')

# Route untuk mengambil data aktual
@app.route('/actual_data')
def get_actual_data():
    response = requests.get(API_URL)
    if response.status_code == 200:
        api_data = response.json()
        trend_data = api_data.get("data", {}).get("trendData", [])
        
        all_data = [entry for entry in trend_data if entry["line"] == "All"]

        extracted_data = []
        for entry in all_data:
            for item in entry["data"]:
                extracted_data.append({
                    "ds": f"{item['year']}-{item['month']}-01",  
                    "y": item["values"]["indexEnergy"]
                })

        df = pd.DataFrame(extracted_data)
        df["ds"] = pd.to_datetime(df["ds"])
        
        if df.isnull().values.any():
            print("Ada data NaN, menghapus data tersebut...")
            df = df.dropna()
            
        return jsonify(df.to_dict(orient='records'))
    else:
        return jsonify({"error": "Gagal mengambil data dari API"}), 500

# Route untuk melakukan forecasting secara dinamis
@app.route('/forecast_data')
@cache.cached(timeout=3600)  
def get_forecast_data():
    # Hitung tanggal mulai dan akhir untuk prediksi
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year + 1}-12-01" 

    future = model.make_future_dataframe(periods=12, freq='M')
    forecast = model.predict(future)
    forecast_filtered = forecast[(forecast['ds'] >= start_date) & (forecast['ds'] <= end_date)]

    forecast_data = forecast_filtered[['ds', 'yhat']].to_dict(orient='records')
    return jsonify(forecast_data)

@app.route('/summary_data')
def get_summary_data():
    actual_response = requests.get(request.host_url + 'actual_data')
    forecast_response = requests.get(request.host_url + 'forecast_data')

    if actual_response.status_code != 200 or forecast_response.status_code != 200:
        return jsonify({"error": "Gagal mengambil data actual atau forecast"}), 500

    actual_data = pd.DataFrame(actual_response.json())
    forecast_data = pd.DataFrame(forecast_response.json())

    # Pastikan format tanggal sesuai
    actual_data["ds"] = pd.to_datetime(actual_data["ds"])
    forecast_data["ds"] = pd.to_datetime(forecast_data["ds"])

    # Hitung summary statistik
    def calculate_summary(df, column):
        return {
            "min": round(df[column].min(), 4),
            "max": round(df[column].max(), 4),
            "average": round(df[column].mean(), 4)
        }

    summary_actual = calculate_summary(actual_data, "y") if not actual_data.empty else None
    summary_forecast = calculate_summary(forecast_data, "yhat") if not forecast_data.empty else None

    summary_result = {
        "summary_actual": summary_actual,
        "summary_forecast": summary_forecast
    }

    return jsonify(summary_result)

@app.route('/model_evaluation')
def evaluate_model():
    actual_response = requests.get(request.host_url + 'actual_data')
    forecast_response = requests.get(request.host_url + 'forecast_data')

    if actual_response.status_code != 200 or forecast_response.status_code != 200:
        return jsonify({"error": "Gagal mengambil data actual atau forecast"}), 500

    actual_data = pd.DataFrame(actual_response.json())
    forecast_data = pd.DataFrame(forecast_response.json())
    actual_data["ds"] = pd.to_datetime(actual_data["ds"])
    forecast_data["ds"] = pd.to_datetime(forecast_data["ds"])
    merged_df = actual_data.merge(forecast_data, on="ds", how="inner")
    
    if merged_df.empty:
        return jsonify({"error": "Tidak ada data yang cocok untuk evaluasi"}), 400

    y_actual = merged_df["y"]
    y_forecast = merged_df["yhat"]

    mae = mean_absolute_error(y_actual, y_forecast)
    mape = mean_absolute_percentage_error(y_actual, y_forecast)
    rmse = np.sqrt(mean_squared_error(y_actual, y_forecast)) 

    evaluation_metrics = {
        "MAE": round(mae, 4),
        "MAPE": round(mape * 100, 2),  
        "RMSE": round(rmse, 4)
    }

    return jsonify(evaluation_metrics)

@app.route('/clear_cache')
def clear_cache():
    cache.clear()
    return "Cache berhasil dibersihkan!", 200

if __name__ == "__main__":
    app.run(debug=True)
