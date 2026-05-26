from __future__ import annotations

import time
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.data import ACTIONS, CAMERAS, LEVEL_ORDER, level_from_score, load_events


COLORS = {
    "BAJO": "#22c55e",
    "MEDIO": "#f59e0b",
    "ALTO": "#ef4444",
    "CRITICO": "#7c3aed",
}


st.set_page_config(
    page_title="SentinelAI Dashboard",
    page_icon="SentinelAI",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background-color: #111827; color: #e5e7eb; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    h1, h2, h3 { color: #38bdf8; letter-spacing: 0; }
    div[data-testid="stMetricValue"] { color: #38bdf8; font-size: 1.8rem !important; }
    div[data-testid="stMetricLabel"] { color: #9ca3af; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def cached_events() -> tuple[pd.DataFrame, str]:
    return load_events()


with st.sidebar:
    st.markdown("## SentinelAI")
    data, mode = cached_events()
    st.caption(mode)
    st.divider()

    page = st.radio(
        "Seccion",
        ["Resumen General", "AgenteTracking", "AgenteMemoria", "Eventos en Vivo"],
        label_visibility="collapsed",
    )
    st.divider()
    hours_filter = st.slider("Ultimas N horas", 1, 72, 24)
    camera_options = sorted(data["camara_id"].dropna().unique().tolist()) or CAMERAS
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
        template="plotly_dark",
        paper_bgcolor="#1f2937",
        plot_bgcolor="#111827",
        margin=dict(t=20, b=20, l=10, r=10),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


if page == "Resumen General":
    st.title("Resumen General")
    st.caption(f"{len(df)} eventos en las ultimas {hours_filter}h. Fuente: {mode}.")

    total = len(df)
    critical = len(df[df["nivel_riesgo"] == "CRITICO"])
    high = len(df[df["nivel_riesgo"] == "ALTO"])
    score_avg = df["score_riesgo"].mean() if total else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total eventos", total)
    col2.metric("Criticos", critical)
    col3.metric("Altos", high)
    col4.metric("Score promedio", f"{score_avg:.2f}")
    col5.metric("Camaras activas", df["camara_id"].nunique())

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Eventos por hora")
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
            st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_b:
        st.subheader("Distribucion de riesgo")
        counts = df["nivel_riesgo"].value_counts().reindex(LEVEL_ORDER, fill_value=0)
        fig = px.pie(
            values=counts.values,
            names=counts.index,
            color=counts.index,
            color_discrete_map=COLORS,
            hole=0.5,
        )
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Objetos detectados")
        objects = df["objeto"].value_counts().reset_index()
        objects.columns = ["objeto", "eventos"]
        fig = px.bar(objects, x="eventos", y="objeto", orientation="h", color="eventos")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    with col_d:
        st.subheader("Score promedio por camara")
        camera_score = df.groupby("camara_id")["score_riesgo"].mean().reset_index()
        fig = px.bar(
            camera_score,
            x="camara_id",
            y="score_riesgo",
            color="score_riesgo",
            range_color=[0, 1],
            color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444", "#7c3aed"],
        )
        fig.add_hline(y=0.60, line_dash="dash", line_color="#ef4444")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

    st.subheader("Ultimas alertas alto / critico")
    alerts = df[df["nivel_riesgo"].isin(["ALTO", "CRITICO"])].head(10).copy()
    if alerts.empty:
        st.info("No hay alertas altas o criticas en el periodo.")
    else:
        alerts["timestamp"] = alerts["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        st.dataframe(
            alerts[
                [
                    "timestamp",
                    "camara_id",
                    "objeto",
                    "confianza",
                    "score_riesgo",
                    "nivel_riesgo",
                    "accion_tomada",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

elif page == "AgenteTracking":
    st.title("AgenteTracking")
    st.caption("Vista preparada para IDs, permanencia y reincidencia.")
    people = df[df["objeto"] == "person"].copy()

    if people.empty:
        st.info("No hay detecciones de personas en el periodo seleccionado.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("IDs unicos", people["track_id"].nunique())
        col2.metric("Permanencia promedio", f"{people['permanencia_s'].mean():.1f}s")
        col3.metric("Permanencia maxima", f"{people['permanencia_s'].max():.1f}s")
        recurrent = people.groupby("track_id").size()
        col4.metric("IDs reincidentes", int((recurrent > 3).sum()))

        col_a, col_b = st.columns(2)
        with col_a:
            track_counts = (
                people.groupby("track_id", dropna=False)
                .agg(eventos=("track_id", "count"), score_max=("score_riesgo", "max"))
                .sort_values("eventos", ascending=False)
                .head(15)
                .reset_index()
            )
            fig = px.bar(track_counts, x="track_id", y="eventos", color="score_max")
            st.plotly_chart(plot_layout(fig), use_container_width=True)

        with col_b:
            fig = px.histogram(people.dropna(subset=["permanencia_s"]), x="permanencia_s", nbins=25)
            fig.add_vline(x=30, line_dash="dash", line_color="#f59e0b")
            st.plotly_chart(plot_layout(fig), use_container_width=True)

        st.subheader("Heatmap camara por hora")
        heatmap_data = people.groupby(["camara_id", "hora"]).size().reset_index(name="eventos")
        pivot = heatmap_data.pivot(index="camara_id", columns="hora", values="eventos").fillna(0)
        fig = px.imshow(pivot, color_continuous_scale="Blues", aspect="auto")
        st.plotly_chart(plot_layout(fig), use_container_width=True)

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
    st.dataframe(
        memory[["timestamp", "camara_id", "zona", "objeto", "confianza", "score_riesgo", "nivel_riesgo"]],
        use_container_width=True,
        hide_index=True,
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
        color = COLORS.get(level, "#94a3b8")
        st.markdown(
            f"""
<div style="background:#1f2937;border-left:4px solid {color};border-radius:8px;padding:0.8rem 1rem;margin-bottom:0.5rem;">
<span style="color:#9ca3af">{row['timestamp'].strftime('%H:%M:%S')}</span>
&nbsp; <strong>{row['camara_id']}</strong>
&nbsp; {row['objeto']}
&nbsp; <span style="color:{color};font-weight:700">{level}</span>
&nbsp; score {row['score_riesgo']:.2f}
&nbsp; {row['accion_tomada']}
</div>
""",
            unsafe_allow_html=True,
        )

    live = df.head(50).copy()
    live["timestamp"] = live["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(
        live[
            [
                "timestamp",
                "camara_id",
                "objeto",
                "confianza",
                "score_riesgo",
                "nivel_riesgo",
                "track_id",
                "accion_tomada",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
