from __future__ import annotations

import base64
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.data import LEVEL_ORDER, load_events


COLORS = {
    "BAJO": "#059669",
    "MEDIO": "#d97706",
    "ALTO": "#dc2626",
    "CRITICO": "#7c2d12",
}

ICON_PATH = Path(__file__).with_name("assets") / "sentinel_icon.svg"


def asset_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


ICON_URI = asset_data_uri(ICON_PATH)


st.set_page_config(
    page_title="SentinelAI Dashboard",
    page_icon=str(ICON_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background-color: #eef2f6; color: #172033; }
    header[data-testid="stHeader"] {
        background: #0b1220;
        border-bottom: 1px solid #1e293b;
        height: 3rem;
    }
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"] {
        display: none !important;
    }
    div[data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        right: 0.5rem !important;
        top: 0.35rem !important;
    }
    div[data-testid="stToolbar"] * {
        color: #dbe4ef !important;
    }
    header[data-testid="stHeader"] button {
        color: #dbe4ef !important;
        background: transparent !important;
    }
    div[data-testid="collapsedControl"] {
        display: flex !important;
        align-items: center;
        gap: 0.45rem;
        position: fixed !important;
        top: 0.45rem !important;
        left: 0.65rem !important;
        z-index: 999999 !important;
        background: #2563eb !important;
        border: 1px solid #60a5fa !important;
        border-radius: 999px !important;
        padding: 0.15rem 0.55rem !important;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.35);
    }
    div[data-testid="collapsedControl"]::after {
        content: "Menu";
        color: #ffffff;
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1;
        pointer-events: none;
    }
    div[data-testid="collapsedControl"] button {
        color: #ffffff !important;
        width: 1.8rem !important;
        height: 1.8rem !important;
        min-height: 1.8rem !important;
        padding: 0 !important;
    }
    button[aria-label="Hide sidebar"],
    button[aria-label="Show sidebar"] {
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: #2563eb !important;
        border: 1px solid #60a5fa !important;
        border-radius: 999px !important;
        color: #ffffff !important;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.25);
        z-index: 999999 !important;
    }
    button[aria-label="Show sidebar"] {
        position: fixed !important;
        top: 0.55rem !important;
        left: 0.65rem !important;
    }
    button[aria-label="Hide sidebar"] svg,
    button[aria-label="Show sidebar"] svg,
    div[data-testid="collapsedControl"] svg {
        color: #ffffff !important;
        stroke: #ffffff !important;
        fill: none !important;
    }
    .block-container { padding-top: 3.25rem; padding-bottom: 1.4rem; max-width: 1460px; }
    section[data-testid="stSidebar"] {
        background: #101827;
        border-right: 1px solid #243044;
    }
    section[data-testid="stSidebar"] * { color: #dbe4ef !important; }
    section[data-testid="stSidebar"] h2 {
        color: #ffffff !important;
        font-size: 1.15rem !important;
        padding-top: 0.35rem;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #8ea0b8 !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #253249;
        margin: 1rem 0;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: transparent;
        border-radius: 8px;
        padding: 0.25rem 0.35rem;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: #17233a;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: #0b1220;
        border-color: #34445f;
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] span[data-baseweb="tag"] {
        background: #2563eb !important;
        border-radius: 6px;
    }
    section[data-testid="stSidebar"] .stButton button {
        background: #2563eb;
        border: 1px solid #3b82f6;
        color: #ffffff !important;
        border-radius: 8px;
        width: 100%;
        height: 2.5rem;
    }
    section[data-testid="stSidebar"] .stCheckbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #b8c4d6 !important;
        font-size: 0.85rem;
    }
    .sentinel-sidebar-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.35rem 0 0.2rem 0;
    }
    .sentinel-sidebar-brand img {
        width: 2.1rem;
        height: 2.1rem;
        border-radius: 10px;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.22);
    }
    .sentinel-sidebar-title {
        color: #ffffff;
        font-weight: 800;
        font-size: 1rem;
        line-height: 1.1;
    }
    .sentinel-sidebar-subtitle {
        color: #8ea0b8;
        font-size: 0.78rem;
        margin-top: 0.15rem;
    }
    h1, h2, h3 { color: #172033; letter-spacing: 0; }
    h1 { font-size: 1.9rem !important; margin-bottom: 0.2rem; }
    h2, h3 { font-size: 1.15rem !important; }
    div[data-testid="stCaptionContainer"] { color: #667085; }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d6dee9;
        border-radius: 8px;
        padding: 0.8rem 0.95rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }
    div[data-testid="stMetricValue"] { color: #0f766e; font-size: 1.55rem !important; }
    div[data-testid="stMetricLabel"] { color: #64748b; }
    div[data-testid="stDataFrame"] {
        border: 1px solid #d8dee8;
        border-radius: 8px;
        overflow: hidden;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border-color: #d6dee9 !important;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    .sentinel-titlebar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1rem;
        background: #ffffff;
        border: 1px solid #d6dee9;
        border-left: 5px solid #2563eb;
        border-radius: 8px;
        padding: 1rem 1.1rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
    }
    .sentinel-titlebar h1 {
        margin: 0 0 0.2rem 0 !important;
        line-height: 1.15;
    }
    .sentinel-heading {
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }
    .sentinel-heading img {
        width: 2.8rem;
        height: 2.8rem;
        border-radius: 12px;
        box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
        flex: 0 0 auto;
    }
    .sentinel-subtitle {
        color: #667085;
        font-size: 0.92rem;
    }
    .sentinel-actions {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        flex-wrap: wrap;
    }
    .sentinel-status {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 999px;
        padding: 0.35rem 0.75rem;
        color: #166534;
        font-size: 0.85rem;
        white-space: nowrap;
    }
    .sentinel-mode {
        background: #f8fafc;
        border: 1px solid #d6dee9;
        border-radius: 999px;
        color: #475569;
        font-size: 0.85rem;
        padding: 0.35rem 0.75rem;
        white-space: nowrap;
    }
    .sentinel-dot {
        width: 0.55rem;
        height: 0.55rem;
        border-radius: 999px;
        background: #059669;
        display: inline-block;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def cached_events() -> tuple[pd.DataFrame, str]:
    return load_events()


with st.sidebar:
    data, mode = cached_events()
    st.markdown(
        f"""
<div class="sentinel-sidebar-brand">
  <img src="{ICON_URI}" alt="SentinelAI">
  <div>
    <div class="sentinel-sidebar-title">SentinelAI</div>
    <div class="sentinel-sidebar-subtitle">{mode}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.radio(
        "Seccion",
        ["Resumen General", "AgenteRiesgo", "Interfaz Humana", "AgenteMemoria", "Eventos en Vivo"],
        label_visibility="collapsed",
    )
    st.divider()
    hours_filter = st.slider("Ultimas N horas", 1, 72, 24)
    camera_options = sorted(data["camara_id"].dropna().unique().tolist())
    selected_cameras = st.multiselect("Camaras", camera_options, default=camera_options)
    selected_levels = st.multiselect("Nivel riesgo", LEVEL_ORDER, default=LEVEL_ORDER)
    auto_refresh = st.checkbox("Auto-refresh 30s", value=False)

    if st.button("Refrescar"):
        st.cache_data.clear()
        st.rerun()

    if auto_refresh:
        time.sleep(30)
        st.rerun()


df_all, mode = cached_events()
cutoff = datetime.now() - timedelta(hours=hours_filter)
df = df_all[
    (df_all["timestamp"] >= cutoff)
    & (df_all["camara_id"].isin(selected_cameras))
    & (df_all["nivel_riesgo"].isin(selected_levels))
].copy()


def plot_layout(fig):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#172033", size=12),
        margin=dict(t=8, b=52, l=48, r=18),
        legend=dict(
            orientation="h",
            y=-0.2,
            x=0,
            title_font=dict(color="#172033"),
            font=dict(color="#172033", size=11),
        ),
        height=340,
        hovermode="x unified",
        bargap=0.28,
    )
    fig.update_xaxes(
        gridcolor="#edf1f5",
        zeroline=False,
        color="#172033",
        tickfont=dict(color="#172033", size=11),
        title_font=dict(color="#172033", size=12),
        linecolor="#cbd5e1",
    )
    fig.update_yaxes(
        gridcolor="#edf1f5",
        zeroline=False,
        color="#172033",
        tickfont=dict(color="#172033", size=11),
        title_font=dict(color="#172033", size=12),
        linecolor="#cbd5e1",
    )
    return fig


def paginated_dataframe(
    df_table: pd.DataFrame,
    key: str,
    columns: list[str],
    rename: dict[str, str],
    page_size: int = 10,
) -> None:
    total_rows = len(df_table)
    if total_rows == 0:
        st.info("No hay datos para mostrar.")
        return

    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page = st.number_input(
        "Pagina",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key=f"{key}_page",
    )
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df_table.iloc[start:end].copy()

    st.caption(f"Mostrando {start + 1}-{min(end, total_rows)} de {total_rows} registros")
    st.dataframe(
        page_df[columns].rename(columns=rename),
        use_container_width=True,
        hide_index=True,
    )


if page == "Resumen General":
    st.markdown(
        f"""
<div class="sentinel-titlebar">
  <div class="sentinel-heading">
    <img src="{ICON_URI}" alt="SentinelAI">
    <div>
      <h1>Panel de Seguridad SentinelAI</h1>
      <div class="sentinel-subtitle">{len(df)} eventos en las ultimas {hours_filter}h. Fuente: {mode}.</div>
    </div>
  </div>
  <div class="sentinel-actions">
    <div class="sentinel-mode">{len(selected_cameras)} camara(s) | {len(selected_levels)} nivel(es)</div>
    <div class="sentinel-status"><span class="sentinel-dot"></span> Sistema operativo</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    total = len(df)
    critical = len(df[df["nivel_riesgo"] == "CRITICO"])
    high = len(df[df["nivel_riesgo"] == "ALTO"])
    score_avg = df["score_riesgo"].mean() if total else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Eventos", total)
    col2.metric("Criticos", critical)
    col3.metric("Altos", high)
    col4.metric("Score promedio", f"{score_avg:.2f}")
    col5.metric("Camaras activas", df["camara_id"].nunique())

    st.write("")
    col_a, col_b = st.columns([2, 1], gap="medium")
    with col_a:
        with st.container(border=True):
            st.subheader("Actividad por hora")
            timeline_df = df.copy()
            timeline_df["hora_bin"] = timeline_df["timestamp"].dt.floor("h")
            timeline = timeline_df.groupby(["hora_bin", "nivel_riesgo"]).size().reset_index(name="eventos")
            if timeline.empty:
                st.info("No hay eventos para graficar.")
            else:
                fig = px.bar(
                    timeline,
                    x="hora_bin",
                    y="eventos",
                    color="nivel_riesgo",
                    color_discrete_map=COLORS,
                    labels={"hora_bin": "Hora", "eventos": "Eventos"},
                )
                fig.update_traces(marker_line_width=0, width=1000 * 60 * 42)
                fig.update_xaxes(tickformat="%H:%M<br>%d %b", title_text="")
                fig.update_yaxes(title_text="Eventos")
                fig.update_layout(legend_title_text="Nivel")
                st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_b:
        with st.container(border=True):
            st.subheader("Distribucion de riesgo")
            counts = df["nivel_riesgo"].value_counts().reindex(LEVEL_ORDER, fill_value=0).reset_index()
            counts.columns = ["nivel_riesgo", "eventos"]
            counts["nivel"] = counts["nivel_riesgo"].map(
                {"BAJO": "Bajo", "MEDIO": "Medio", "ALTO": "Alto", "CRITICO": "Critico"}
            )
            chart_counts = counts[counts["eventos"] > 0].copy()
            if chart_counts.empty:
                chart_counts = counts.head(1).assign(eventos=1, nivel="Sin datos")
            fig = px.pie(
                chart_counts,
                values="eventos",
                names="nivel",
                color="nivel_riesgo",
                color_discrete_map=COLORS,
                hole=0.55,
            )
            fig.update_traces(textposition="inside", textinfo="percent")
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.12, x=0.05))
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    col_c, col_d = st.columns(2, gap="medium")
    with col_c:
        with st.container(border=True):
            st.subheader("Objetos detectados")
            objects = df["objeto_nombre"].value_counts().reset_index()
            objects.columns = ["objeto", "eventos"]
            objects = objects.sort_values("eventos", ascending=True)
            fig = px.bar(
                objects,
                x="eventos",
                y="objeto",
                orientation="h",
                color="eventos",
                color_continuous_scale=["#dbeafe", "#2563eb"],
            )
            fig.update_traces(
                marker_line_width=0,
                text=objects["eventos"],
                textposition="outside",
                textfont=dict(color="#172033"),
                cliponaxis=False,
            )
            fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=88, r=42, t=8, b=52))
            fig.update_xaxes(title_text="Eventos")
            fig.update_yaxes(title_text="")
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_d:
        with st.container(border=True):
            st.subheader("Score promedio por camara")
            camera_score = df.groupby("camara_id")["score_riesgo"].mean().reset_index()
            fig = px.bar(
                camera_score,
                x="camara_id",
                y="score_riesgo",
                color="score_riesgo",
                range_color=[0, 1],
                color_continuous_scale=["#059669", "#d97706", "#dc2626", "#7c2d12"],
            )
            fig.add_hline(y=0.60, line_dash="dash", line_color="#dc2626")
            fig.update_traces(marker_line_width=0)
            fig.update_layout(showlegend=False, coloraxis_showscale=False)
            fig.update_yaxes(range=[0, 1], title_text="Score")
            fig.update_xaxes(title_text="")
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    with st.container(border=True):
        st.subheader("Ultimas alertas alto / critico")
        alerts = df[df["nivel_riesgo"].isin(["ALTO", "CRITICO"])].head(10).copy()
        if alerts.empty:
            st.info("No hay alertas altas o criticas en el periodo.")
        else:
            alerts["timestamp"] = alerts["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
            paginated_dataframe(
                alerts,
                "alerts",
                [
                    "timestamp",
                    "camara_id",
                    "objeto_nombre",
                    "confianza",
                    "score_riesgo",
                    "nivel_nombre",
                    "accion_nombre",
                ],
                {
                    "timestamp": "fecha",
                    "camara_id": "camara",
                    "objeto_nombre": "objeto",
                    "score_riesgo": "score",
                    "nivel_nombre": "nivel",
                    "accion_nombre": "accion",
                },
            )

elif page == "AgenteRiesgo":
    st.title("AgenteRiesgo")
    st.caption("Validacion del score final, factores de contexto y salida IA/n8n.")

    total = len(df)
    review = len(df[df["nivel_riesgo"].isin(["ALTO", "CRITICO"])])
    erratic = int(df["movimiento_erratico"].sum()) if total else 0
    avg_speed = df["velocidad"].mean() if total else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Eventos analizados", total)
    col2.metric("Revision humana", review)
    col3.metric("Movimiento erratico", erratic)
    col4.metric("Velocidad promedio", f"{avg_speed:.1f}")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Riesgo por objeto")
        risk_by_object = (
            df.groupby(["objeto_nombre", "nivel_riesgo"])
            .size()
            .reset_index(name="eventos")
        )
        if risk_by_object.empty:
            st.info("No hay eventos para analizar.")
        else:
            fig = px.bar(
                risk_by_object,
                x="objeto_nombre",
                y="eventos",
                color="nivel_riesgo",
                color_discrete_map=COLORS,
                labels={"objeto_nombre": "Objeto"},
            )
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_b:
        st.subheader("Acciones")
        actions = df["accion_nombre"].value_counts().reset_index()
        actions.columns = ["accion", "eventos"]
        fig = px.bar(actions, x="eventos", y="accion", orientation="h", color="eventos")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    st.subheader("Eventos con mayor score")
    top_risk = df.sort_values("score_riesgo", ascending=False).copy()
    top_risk["timestamp"] = top_risk["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    paginated_dataframe(
        top_risk,
        "top_risk",
        [
            "timestamp",
            "camara_id",
            "zona",
            "objeto_nombre",
            "confianza",
            "score_riesgo",
            "nivel_nombre",
            "accion_nombre",
            "track_id",
            "velocidad",
            "permanencia_s",
            "resumen_ia",
        ],
        {
            "timestamp": "fecha",
            "camara_id": "camara",
            "objeto_nombre": "objeto",
            "score_riesgo": "score",
            "nivel_nombre": "nivel",
            "accion_nombre": "accion",
            "permanencia_s": "permanencia",
            "resumen_ia": "analisis_ia",
        },
    )

elif page == "Interfaz Humana":
    st.title("Interfaz Humana")
    st.caption("Revision de supervisor, bloqueo operativo y trazabilidad de decisiones.")
    reviews = df[df["requiere_revision_humana"]].copy()
    pending = reviews[reviews["estado_revision_humana"] == "PENDIENTE"]
    blocked = df[df["automatizacion_bloqueada"]]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pendientes", len(pending))
    col2.metric("Bloqueadas", len(blocked))
    col3.metric("Revision humana", len(reviews))
    col4.metric("Criticas/Altas", len(df[df["nivel_riesgo"].isin(["ALTO", "CRITICO"])]))

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader("Estado de revisiones")
        status_counts = (
            df["estado_revision_humana"]
            .fillna("NO_REQUERIDA")
            .value_counts()
            .reset_index()
        )
        status_counts.columns = ["estado", "eventos"]
        fig = px.bar(status_counts, x="estado", y="eventos", color="eventos")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_b:
        st.subheader("Cola por prioridad")
        queue = reviews.groupby(["nivel_riesgo", "accion_nombre"]).size().reset_index(name="eventos")
        if queue.empty:
            st.info("No hay eventos esperando revision humana.")
        else:
            fig = px.bar(
                queue,
                x="nivel_riesgo",
                y="eventos",
                color="accion_nombre",
                category_orders={"nivel_riesgo": LEVEL_ORDER},
            )
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    st.subheader("Eventos para supervisor")
    supervisor = reviews.sort_values(["nivel_riesgo", "score_riesgo"], ascending=[False, False]).copy()
    if supervisor.empty:
        st.info("La cola de supervisor esta limpia.")
    else:
        supervisor["timestamp"] = supervisor["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        paginated_dataframe(
            supervisor,
            "supervisor",
            [
                "timestamp",
                "camara_id",
                "zona",
                "objeto_nombre",
                "confianza",
                "score_riesgo",
                "nivel_nombre",
                "accion_nombre",
                "estado_revision_humana",
                "review_id",
                "resumen_ia",
            ],
            {
                "timestamp": "fecha",
                "camara_id": "camara",
                "objeto_nombre": "objeto",
                "score_riesgo": "score",
                "nivel_nombre": "nivel",
                "accion_nombre": "accion",
                "estado_revision_humana": "revision",
                "resumen_ia": "analisis_ia",
            },
        )

elif page == "AgenteMemoria":
    st.title("AgenteMemoria")
    st.caption("Patrones temporales y reincidencia por camara.")

    hourly = (
        df.groupby("hora")
        .agg(eventos=("hora", "count"), score_avg=("score_riesgo", "mean"))
        .reset_index()
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=hourly["hora"], y=hourly["eventos"], name="Eventos"), secondary_y=False)
    fig.add_trace(
        go.Scatter(x=hourly["hora"], y=hourly["score_avg"], name="Score promedio", mode="lines+markers"),
        secondary_y=True,
    )
    st.plotly_chart(plot_layout(fig), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        last_24h = df_all[df_all["timestamp"] >= datetime.now() - timedelta(hours=24)]
        recurrence = (
            last_24h.groupby("camara_id")
            .agg(
                total=("camara_id", "count"),
                alertas=("nivel_riesgo", lambda values: values.isin(["ALTO", "CRITICO"]).sum()),
                score_max=("score_riesgo", "max"),
            )
            .reset_index()
        )
        fig = px.scatter(recurrence, x="total", y="alertas", size="score_max", text="camara_id")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_b:
        sorted_df = df.sort_values("timestamp").copy()
        sorted_df["score_rolling"] = sorted_df["score_riesgo"].rolling(window=10, min_periods=1).mean()
        fig = px.line(sorted_df, x="timestamp", y="score_rolling", color="camara_id")
        fig.add_hline(y=0.60, line_dash="dash", line_color="#ef4444")
        fig.add_hline(y=0.80, line_dash="dash", line_color="#7c3aed")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    st.subheader("Historial alto / critico")
    memory = df[df["nivel_riesgo"].isin(["ALTO", "CRITICO"])].copy()
    memory["timestamp"] = memory["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    paginated_dataframe(
        memory,
        "memory",
        [
            "timestamp",
            "camara_id",
            "zona",
            "objeto_nombre",
            "confianza",
            "score_riesgo",
            "nivel_nombre",
            "eventos_previos_24h",
            "resumen_ia",
        ],
        {
            "timestamp": "fecha",
            "camara_id": "camara",
            "objeto_nombre": "objeto",
            "score_riesgo": "score",
            "nivel_nombre": "nivel",
            "eventos_previos_24h": "eventos_24h",
            "resumen_ia": "analisis_ia",
        },
    )

    hourly_risk = df.groupby("hora")["score_riesgo"].mean().reset_index()
    top_hours = hourly_risk.nlargest(5, "score_riesgo")
    if not top_hours.empty:
        text = " | ".join([f"{int(row.hora):02d}:00 ({row.score_riesgo:.2f})" for _, row in top_hours.iterrows()])
        st.info(f"Horas con mayor score historico: {text}")

else:
    st.title("Eventos en Vivo")
    st.caption("Ultimos eventos detectados.")

    if st.button("Refrescar ahora"):
        st.cache_data.clear()
        st.rerun()

    for _, row in df.head(5).iterrows():
        level = row["nivel_riesgo"]
        color = COLORS.get(level, "#64748b")
        st.markdown(
            f"""
<div style="background:#ffffff;border:1px solid #d8dee8;border-left:4px solid {color};border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.5rem;box-shadow:0 1px 2px rgba(15,23,42,0.05);">
<span style="color:#64748b">{row['timestamp'].strftime('%H:%M:%S')}</span>
&nbsp; <strong>{row['camara_id']}</strong>
&nbsp; {row['objeto_nombre']}
&nbsp; <span style="color:{color};font-weight:700">{row['nivel_nombre']}</span>
&nbsp; score {row['score_riesgo']:.2f}
&nbsp; {row['accion_nombre']}
</div>
""",
            unsafe_allow_html=True,
        )

    live = df.copy()
    live["timestamp"] = live["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    paginated_dataframe(
        live,
        "live",
        [
            "timestamp",
            "camara_id",
            "objeto_nombre",
            "confianza",
            "score_riesgo",
            "nivel_nombre",
            "track_id",
            "velocidad",
            "permanencia_s",
            "resumen_ia",
            "accion_nombre",
        ],
        {
            "timestamp": "fecha",
            "camara_id": "camara",
            "objeto_nombre": "objeto",
            "score_riesgo": "score",
            "nivel_nombre": "nivel",
            "permanencia_s": "permanencia",
            "resumen_ia": "analisis_ia",
            "accion_nombre": "accion",
        },
    )
