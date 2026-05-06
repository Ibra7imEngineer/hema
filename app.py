import json
from pathlib import Path
from typing import Optional, Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    filename = uploaded_file.name.lower()
    if filename.endswith('.csv') or uploaded_file.type == 'text/csv':
        return pd.read_csv(uploaded_file)
    if filename.endswith('.xlsx'):
        return pd.read_excel(uploaded_file, engine='openpyxl')
    if filename.endswith('.xls'):
        return pd.read_excel(uploaded_file)
    raise ValueError('Unsupported file format. Please upload a CSV or Excel file.')


def build_forecast(values: list[float], periods: int = 3) -> list[float]:
    values = [float(v) for v in values]
    n = len(values)
    if n < 2:
        return [values[-1] if n else 0.0 for _ in range(periods)]

    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(values) / n
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
    denominator = sum((xi - mean_x) ** 2 for xi in x)
    m = numerator / denominator if denominator else 0.0
    b = mean_y - m * mean_x
    future_x = list(range(n, n + periods))
    return [m * xi + b for xi in future_x]


def make_analysis_payload(df: pd.DataFrame) -> dict[str, Any]:
    df = df.dropna(how='all')
    numeric_df = df.select_dtypes(include=['number'])
    if numeric_df.empty:
        raise ValueError('The uploaded file does not contain numeric columns for analysis.')

    summary_stats: dict[str, dict[str, float]] = {}
    for column in numeric_df.columns:
        series = numeric_df[column].dropna().astype(float)
        summary_stats[column] = {
            'mean': float(series.mean()),
            'sum': float(series.sum()),
            'max': float(series.max()),
            'min': float(series.min()),
        }

    chart_column = numeric_df.columns[0]
    numeric_series = numeric_df[chart_column].dropna().astype(float).tolist()
    chart_labels = [str(i + 1) for i in range(len(numeric_series))]
    forecast_values = build_forecast(numeric_series, periods=3)
    forecast_labels = [f'Next {i}' for i in range(1, 4)]

    table_data = df.head(50).fillna('').astype(str).to_dict(orient='records')

    return {
        'summary_stats': summary_stats,
        'chart_data': {
            'labels': chart_labels,
            'values': numeric_series,
            'seriesName': chart_column,
        },
        'forecast_data': {
            'labels': forecast_labels,
            'values': [float(value) for value in forecast_values],
            'seriesName': chart_column,
        },
        'table_data': table_data,
        'columns': df.columns.tolist(),
        'row_count': int(df.shape[0]),
        'chart_column': chart_column,
    }


def load_html_template() -> str:
    path = Path(__file__).parent / 'index.html'
    return path.read_text(encoding='utf-8')


def inject_streamlit_payload(html: str, payload: Optional[dict[str, Any]]) -> str:
    if payload is None:
        return html

    payload_json = json.dumps(payload)
    injection = (
        '<script>'
        f'window.projectData = {payload_json};'
        'window.postMessage({ type: "PROJECT_DATA", payload: window.projectData }, "*");'
        '</script>'
    )
    return html.replace('</body>', f'{injection}</body>')


st.set_page_config(page_title='Streamlit BI Dashboard', layout='wide')

st.sidebar.title('Upload Dataset')
uploaded_file = st.sidebar.file_uploader(
    'Upload CSV or Excel file', type=['csv', 'xlsx', 'xls']
)

analysis_payload = None
if uploaded_file is not None:
    try:
        dataframe = read_uploaded_file(uploaded_file)
        analysis_payload = make_analysis_payload(dataframe)
    except Exception as exc:
        st.sidebar.error(str(exc))

st.markdown(
    '### Streamlit Dashboard Integration\n'
    'Upload your file through the sidebar uploader. The embedded dashboard uses your dataset for analysis and chart rendering.',
)

html_content = load_html_template()
html_content = inject_streamlit_payload(html_content, analysis_payload)
components.html(html_content, height=1600, scrolling=True)
