import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from etl.load import get_conn

st.set_page_config(page_title="Clima ETL - Dashboard", page_icon="🌤️", layout="wide")

# ---- Tokens de diseno (superficie oscura, misma paleta validada del proyecto) ----
PAGE_BG = "#0d0d0d"
SURFACE = "#1a1a19"
GRID_COLOR = "#2c2c2a"
AXIS_COLOR = "#383835"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c3c2b7"
TEXT_MUTED = "#898781"

# Paleta categorica validada, pasos para superficie oscura (orden fijo, no se reordena)
CATEGORICAL_PALETTE = [
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#008300", "#9085e9", "#e66767",
]
SEQUENTIAL_BLUE = "#3987e5"


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


def weather_icon(descripcion: str) -> str:
    d = descripcion.lower()
    if "tormenta" in d:
        return "⛈️"
    if "nieve" in d:
        return "❄️"
    if "lluvia" in d or "llovizna" in d:
        return "🌧️"
    if "niebla" in d or "neblina" in d or "bruma" in d:
        return "🌫️"
    if "nub" in d:
        return "☁️" if "muy" in d or d.strip() == "nublado" else "⛅"
    if "despejado" in d or "claro" in d:
        return "☀️"
    return "🌡️"


def time_axis_range(df: pd.DataFrame) -> tuple[list, str]:
    """Rango y formato de eje X compartidos por todos los graficos de tiempo,
    para que un dataset con pocos dias de historial no genere ejes absurdos
    (Plotly auto-escala a microsegundos si solo hay 1 punto por serie)."""
    fecha_min, fecha_max = df["fecha"].min(), df["fecha"].max()
    span_days = max((fecha_max - fecha_min).days, 1)
    pad_days = 2 if span_days <= 3 else max(1, span_days // 5)
    rango = [fecha_min - pd.Timedelta(days=pad_days), fecha_max + pd.Timedelta(days=pad_days)]
    return rango, "%d %b"


def style_chart(fig, title, x_range, tick_format, y_title="Temperatura (°C)", show_legend=True):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=TEXT_PRIMARY)),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT_SECONDARY, family="system-ui, -apple-system, Segoe UI, sans-serif"),
        hovermode="x unified",
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="left", x=0, font=dict(color=TEXT_SECONDARY)),
        margin=dict(l=10, r=50, t=50, b=10),
    )
    fig.update_xaxes(
        range=x_range, tickformat=tick_format, dtick="D1" if (x_range[1] - x_range[0]).days <= 14 else None,
        showgrid=False, showline=True, linecolor=AXIS_COLOR, tickfont=dict(color=TEXT_MUTED),
    )
    fig.update_yaxes(
        title=dict(text=y_title, font=dict(color=TEXT_MUTED)),
        showgrid=True, gridcolor=GRID_COLOR, showline=False, tickfont=dict(color=TEXT_MUTED), zeroline=False,
    )
    return fig


def render_weather_card(row):
    icon = weather_icon(row["descripcion"])
    ciudad = html.escape(str(row["ciudad"]))
    pais = html.escape(str(row["pais"]))
    descripcion = html.escape(str(row["descripcion"]))
    st.markdown(
        f"""
        <div style="background:{SURFACE}; border:1px solid {GRID_COLOR}; border-radius:12px;
                    padding:16px 18px; margin-bottom:14px;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <div style="font-size:12px; color:{TEXT_MUTED}; text-transform:uppercase; letter-spacing:.05em;">
                {ciudad}, {pais}
              </div>
              <div style="font-size:32px; font-weight:600; color:{TEXT_PRIMARY}; margin-top:4px;">
                {row['temperatura']:.1f}°C
              </div>
              <div style="font-size:13px; color:{TEXT_SECONDARY};">
                {descripcion} · sensación {row['sensacion']:.1f}°C
              </div>
            </div>
            <div style="font-size:34px; line-height:1;">{icon}</div>
          </div>
          <div style="display:flex; gap:18px; margin-top:12px; font-size:12px; color:{TEXT_MUTED};">
            <span>💧 {row['humedad']}%</span>
            <span>💨 {row['viento_kmh']:.1f} km/h</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---- Sidebar ----
with st.sidebar:
    st.markdown("## 🌤️ Clima ETL")
    st.caption("Dashboard en vivo sobre Azure SQL Database.")
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Los datos se cachean 5 minutos. La primera carga puede tardar si la base (tier Serverless) estaba en pausa.")

with st.spinner("Conectando a Azure SQL..."):
    df = load_data()

if df.empty:
    st.warning("Todavia no hay datos en la base. Corre el ETL (python main.py, o espera al timer trigger) y refresca esta pagina.")
    st.stop()

x_range, tick_format = time_axis_range(df)
latest = df.sort_values("fecha").groupby("ciudad").tail(1).sort_values("ciudad")

st.title("Clima ETL — Dashboard")

# ---- KPIs ----
k1, k2, k3, k4 = st.columns(4)
k1.metric("Ciudades monitoreadas", df["ciudad"].nunique())
k2.metric("Registros históricos", len(df))
k3.metric("Temp. promedio actual", f"{latest['temperatura'].mean():.1f}°C")
k4.metric("Última actualización", pd.to_datetime(df["timestamp"].max()).strftime("%d %b, %H:%M UTC"))

if (df["fecha"].max() - df["fecha"].min()).days < 2:
    st.info(
        "El histórico recién empieza a acumularse (el ETL corre 1 vez al día) — "
        "las tendencias se van a ver mejor en unos días."
    )

st.divider()

tab_resumen, tab_comparar, tab_todas, tab_datos = st.tabs(
    ["📊 Resumen", "📈 Comparar ciudades", "🗺️ Todas las ciudades", "🧾 Datos crudos"]
)

with tab_resumen:
    st.subheader("Clima actual por ciudad")
    cols = st.columns(3)
    for i, (_, row) in enumerate(latest.iterrows()):
        with cols[i % 3]:
            render_weather_card(row)

with tab_comparar:
    comparable_cities = sorted(df["ciudad"].unique())[:8]
    city_color = {city: CATEGORICAL_PALETTE[i] for i, city in enumerate(comparable_cities)}

    if df["ciudad"].nunique() > 8:
        st.caption(
            "Por legibilidad, aquí se pueden comparar hasta 8 ciudades a la vez. "
            "Todas las ciudades (sin límite) están en la pestaña *Todas las ciudades*."
        )

    seleccion = st.multiselect(
        "Ciudades a comparar", options=comparable_cities, default=comparable_cities[:4], max_selections=8,
    )

    if seleccion:
        fig = go.Figure()
        for city in seleccion:
            city_df = df[df["ciudad"] == city].sort_values("fecha")
            fig.add_trace(go.Scatter(
                x=city_df["fecha"], y=city_df["temperatura"],
                mode="lines+markers", name=city,
                line=dict(color=city_color[city], width=2),
                marker=dict(size=7),
            ))
            last_point = city_df.iloc[-1]
            fig.add_annotation(
                x=last_point["fecha"], y=last_point["temperatura"], text=city,
                showarrow=False, xanchor="left", xshift=10,
                font=dict(color=city_color[city], size=12),
            )
        style_chart(fig, "Temperatura en el tiempo", x_range, tick_format)
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Selecciona al menos una ciudad para ver el gráfico.")

with tab_todas:
    cities_all = sorted(df["ciudad"].unique())
    cols_per_row = 3
    for i in range(0, len(cities_all), cols_per_row):
        row_cities = cities_all[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, city in zip(cols, row_cities):
            city_df = df[df["ciudad"] == city].sort_values("fecha")
            with col:
                with st.container(border=True):
                    fig = go.Figure(go.Scatter(
                        x=city_df["fecha"], y=city_df["temperatura"],
                        mode="lines+markers",
                        line=dict(color=SEQUENTIAL_BLUE, width=2),
                        marker=dict(size=6),
                        showlegend=False,
                    ))
                    style_chart(fig, city, x_range, tick_format, show_legend=False)
                    fig.update_layout(height=230, margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig, use_container_width=True)

with tab_datos:
    st.dataframe(
        df.sort_values(["fecha", "ciudad"], ascending=[False, True])
        .rename(columns={
            "ciudad": "Ciudad", "pais": "Pais", "temperatura": "Temp (C)", "sensacion": "Sensacion (C)",
            "humedad": "Humedad (%)", "descripcion": "Clima", "viento_kmh": "Viento (km/h)",
            "timestamp": "Timestamp (UTC)", "fecha": "Fecha",
        }),
        hide_index=True,
        use_container_width=True,
    )
