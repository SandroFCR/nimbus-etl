import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from etl.load import get_conn

st.set_page_config(page_title="Clima ETL - Dashboard", page_icon="🌤️", layout="wide")

# Paleta categorica validada (orden fijo, no se reordena por seleccion)
CATEGORICAL_PALETTE = [
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100",
    "#e87ba4", "#008300", "#4a3aa7", "#e34948",
]
SEQUENTIAL_BLUE = "#2a78d6"
CHART_BG = "#fcfcfb"
GRID_COLOR = "#e1e0d9"
AXIS_COLOR = "#c3c2b7"
TEXT_PRIMARY = "#0b0b0b"
TEXT_MUTED = "#898781"


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    conn = get_conn()
    try:
        df = pd.read_sql(
            """
            SELECT ciudad, pais, temperatura, sensacion, humedad, descripcion,
                   viento_kmh, timestamp, fecha
            FROM clima
            ORDER BY fecha, ciudad
            """,
            conn,
        )
    finally:
        conn.close()
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def style_chart(fig, title, y_title="Temperatura (°C)"):
    fig.update_layout(
        title=title,
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=TEXT_PRIMARY, family="system-ui, -apple-system, Segoe UI, sans-serif"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=60, t=60, b=10),
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=AXIS_COLOR, tickfont=dict(color=TEXT_MUTED))
    fig.update_yaxes(title=y_title, showgrid=True, gridcolor=GRID_COLOR, showline=False, tickfont=dict(color=TEXT_MUTED))
    return fig


st.title("🌤️ Clima ETL — Dashboard")
st.caption("Historico de clima recolectado automaticamente por el ETL, leido en vivo desde Azure SQL Database.")

with st.spinner("Conectando a Azure SQL... (puede tardar unos segundos si la base estaba en pausa)"):
    df = load_data()

if df.empty:
    st.warning("Todavia no hay datos en la base. Corre el ETL (python main.py, o espera al timer trigger) y refresca esta pagina.")
    st.stop()

ultima_actualizacion = df["timestamp"].max()
st.caption(
    f"Ultima actualizacion registrada: **{ultima_actualizacion} UTC** · "
    f"{df['ciudad'].nunique()} ciudades · {len(df)} registros"
)

# ---- Snapshot: ultimo registro por ciudad (tabla, mas legible que 9 stat tiles) ----
st.subheader("Clima actual por ciudad")
latest = df.sort_values("fecha").groupby("ciudad").tail(1).sort_values("ciudad")
st.dataframe(
    latest[["ciudad", "pais", "temperatura", "sensacion", "humedad", "descripcion", "viento_kmh", "fecha"]]
    .rename(columns={
        "ciudad": "Ciudad", "pais": "Pais", "temperatura": "Temp (C)", "sensacion": "Sensacion (C)",
        "humedad": "Humedad (%)", "descripcion": "Clima", "viento_kmh": "Viento (km/h)", "fecha": "Fecha",
    }),
    hide_index=True,
    use_container_width=True,
)

# ---- Comparar ciudades: multi-linea categorica, tope de 8 por legibilidad ----
st.subheader("Comparar temperatura entre ciudades")

comparable_cities = sorted(df["ciudad"].unique())[:8]
city_color = {city: CATEGORICAL_PALETTE[i] for i, city in enumerate(comparable_cities)}

if df["ciudad"].nunique() > 8:
    st.caption(
        "Por legibilidad, aqui se pueden comparar hasta 8 ciudades a la vez. "
        "Todas las ciudades (sin limite) se ven en la seccion de abajo."
    )

seleccion = st.multiselect(
    "Ciudades a comparar",
    options=comparable_cities,
    default=comparable_cities[:4],
    max_selections=8,
)

if seleccion:
    fig = go.Figure()
    for city in seleccion:
        city_df = df[df["ciudad"] == city].sort_values("fecha")
        fig.add_trace(go.Scatter(
            x=city_df["fecha"], y=city_df["temperatura"],
            mode="lines+markers", name=city,
            line=dict(color=city_color[city], width=2),
            marker=dict(size=6),
        ))
        last_point = city_df.iloc[-1]
        fig.add_annotation(
            x=last_point["fecha"], y=last_point["temperatura"], text=city,
            showarrow=False, xanchor="left", xshift=8,
            font=dict(color=city_color[city], size=12),
        )
    style_chart(fig, "Temperatura en el tiempo")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Selecciona al menos una ciudad para ver el grafico.")

# ---- Todas las ciudades: small multiples (1 serie por grafico, sin tope) ----
st.subheader("Todas las ciudades")
cities_all = sorted(df["ciudad"].unique())
cols_per_row = 3
for i in range(0, len(cities_all), cols_per_row):
    row_cities = cities_all[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    for col, city in zip(cols, row_cities):
        city_df = df[df["ciudad"] == city].sort_values("fecha")
        fig = go.Figure(go.Scatter(
            x=city_df["fecha"], y=city_df["temperatura"],
            mode="lines+markers",
            line=dict(color=SEQUENTIAL_BLUE, width=2),
            marker=dict(size=5),
            showlegend=False,
        ))
        style_chart(fig, city)
        fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
        col.plotly_chart(fig, use_container_width=True)

with st.expander("Ver datos crudos"):
    st.dataframe(
        df.sort_values(["fecha", "ciudad"], ascending=[False, True]),
        hide_index=True,
        use_container_width=True,
    )
