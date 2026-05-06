from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import numpy as np

app = Flask(__name__, static_folder='.', static_url_path='')


def safe_value(value):
    if isinstance(value, (np.generic, np.ndarray)):
        return np.asarray(value).item()
    if pd.isna(value):
        return None
    return value


def read_uploaded_file(uploaded_file):
    filename = uploaded_file.filename.lower()
    if filename.endswith('.csv') or uploaded_file.content_type == 'text/csv':
        return pd.read_csv(uploaded_file)
    if filename.endswith('.xlsx'):
        return pd.read_excel(uploaded_file, engine='openpyxl')
    if filename.endswith('.xls'):
        return pd.read_excel(uploaded_file)
    raise ValueError('Unsupported file format. Please upload CSV or Excel.')


def build_forecast(values, periods=3):
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 2:
        return [float(values[-1]) if n else 0.0 for _ in range(periods)]
    x = np.arange(n, dtype=float)
    m, b = np.polyfit(x, values, 1)
    future_x = np.arange(n, n + periods, dtype=float)
    return (m * future_x + b).tolist()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return jsonify({'error': 'No file uploaded.'}), 400

    try:
        df = read_uploaded_file(uploaded_file)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400

    df = df.dropna(how='all')
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return jsonify({'error': 'No numeric columns found for analysis.'}), 400

    summary_stats = {}
    for column in numeric_df.columns:
        series = numeric_df[column].dropna().astype(float)
        summary_stats[column] = {
            'mean': safe_value(series.mean()),
            'sum': safe_value(series.sum()),
            'max': safe_value(series.max()),
            'min': safe_value(series.min()),
        }

    chart_column = numeric_df.columns[0]
    numeric_series = numeric_df[chart_column].dropna().astype(float)
    chart_labels = [str(i + 1) for i in range(len(numeric_series))]
    chart_values = numeric_series.tolist()
    forecast_values = build_forecast(chart_values, periods=3)
    forecast_labels = [f'Next {i}' for i in range(1, 4)]

    table_data = df.head(50).fillna('').astype(str).to_dict(orient='records')
    columns = df.columns.tolist()

    response = {
        'summary_stats': summary_stats,
        'chart_data': {
            'labels': chart_labels,
            'values': chart_values,
            'seriesName': chart_column,
        },
        'forecast_data': {
            'labels': forecast_labels,
            'values': [safe_value(x) for x in forecast_values],
            'seriesName': chart_column,
        },
        'table_data': table_data,
        'columns': columns,
        'row_count': int(df.shape[0]),
        'chart_column': chart_column,
    }

    return jsonify(response)


if __name__ == '__main__':
    app.run(debug=True)
