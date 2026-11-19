"""NexoLog | Dashboard ejecutivo de desempeño logístico (DATA1002).

Ejecutar localmente:
    pip install -r requirements.txt
    streamlit run app.py

Datos sintéticos de uso educativo. Coloque NexoLog_envios.csv junto a app.py.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="NexoLog | Inteligencia operativa",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Paleta coherente con el dashboard original.
NAVY = "#142D47"
BLUE = "#258EAC"
ORANGE = "#ED9C53"
VIOLET = "#8456B6"
SOFT_BLUE = "#2D85BA"
SOFT_ORANGE = "#EDA36C"
GRID = "#E8EEF5"
CENTROS = ["Norte", "Centro", "Sur", "Occidente", "Oriente"]
MESES = ["2026-08", "2026-09", "2026-10"]
SERVICIOS = ["Express", "Estandar"]
DESTINOS = ["Urbana", "Periferica"]
COLORES_CENTRO = {
    "Norte": "#258EAC",
    "Centro": "#4661BA",
    "Sur": "#E29750",
    "Occidente": "#8753B8",
    "Oriente": "#3DA788",
}


@st.cache_data(show_spinner=False)
def cargar_datos() -> pd.DataFrame:
    """Carga datos de envíos sin modificar la granularidad (un envío por fila)."""
    ruta = Path(__file__).resolve().parent / "NexoLog_envios.csv"
    if not ruta.is_file():
        raise FileNotFoundError(
            "No se encontró NexoLog_envios.csv. "
            "Guárdalo en la misma carpeta que app.py."
        )
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    requeridas = {
        "id_envio", "fecha_despacho", "mes", "centro", "servicio",
        "destino", "a_tiempo", "reclamo", "costo_operativo_miles_cop",
    }
    faltantes = requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en el CSV: {', '.join(sorted(faltantes))}")
    if df["id_envio"].duplicated().any():
        raise ValueError("El CSV contiene id_envio repetidos: revisa la granularidad.")
    df["fecha_despacho"] = pd.to_datetime(df["fecha_despacho"], errors="coerce")
    df["costo_operativo_miles_cop"] = pd.to_numeric(
        df["costo_operativo_miles_cop"], errors="coerce"
    )
    return df


def indicadores(df: pd.DataFrame) -> dict:
    """Calcula métricas al nivel del envío en el subconjunto filtrado."""
    n = len(df)
    a_tiempo = int(df["a_tiempo"].eq("Si").sum())
    reclamos = int(df["reclamo"].eq("Si").sum())
    return {
        "envios": n,
        "a_tiempo": a_tiempo,
        "retrasados": n - a_tiempo,
        "reclamos": reclamos,
        "puntualidad_pct": 100 * a_tiempo / n if n else None,
        "tasa_reclamos_pct": 100 * reclamos / n if n else None,
        "costo_medio": float(df["costo_operativo_miles_cop"].mean()) if n else None,
    }


def resumen_por_centro(df: pd.DataFrame) -> pd.DataFrame:
    """Genera datos de tabla y gráficos, respetando los filtros activos."""
    if df.empty:
        return pd.DataFrame(columns=[
            "centro", "envios", "a_tiempo", "puntualidad_pct",
            "retrasados", "reclamos", "tasa_reclamos_pct", "costo_medio"
        ])
    resumen = (
        df.assign(
            _a_tiempo=df["a_tiempo"].eq("Si").astype(int),
            _reclamo=df["reclamo"].eq("Si").astype(int),
        )
        .groupby("centro", as_index=False, observed=True)
        .agg(
            envios=("id_envio", "size"),
            a_tiempo=("_a_tiempo", "sum"),
            reclamos=("_reclamo", "sum"),
            costo_medio=("costo_operativo_miles_cop", "mean"),
        )
    )
    resumen["retrasados"] = resumen["envios"] - resumen["a_tiempo"]
    resumen["puntualidad_pct"] = 100 * resumen["a_tiempo"] / resumen["envios"]
    resumen["tasa_reclamos_pct"] = 100 * resumen["reclamos"] / resumen["envios"]
    resumen["orden"] = resumen["centro"].map({c: i for i, c in enumerate(CENTROS)})
    return resumen.sort_values("orden").drop(columns="orden")


def estilo(fig: go.Figure, *, alto=305, tasa=False, leyenda=False) -> go.Figure:
    """Formato consistente para todos los gráficos Plotly."""
    fig.update_layout(
        height=alto,
        margin=dict(l=20, r=20, t=22 if not leyenda else 40, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", color=NAVY, size=12),
        showlegend=leyenda,
        legend=dict(orientation="h", x=0, y=1.18, title=None),
        hoverlabel=dict(bgcolor=NAVY, font_color="white"),
        bargap=0.23,
    )
    fig.update_xaxes(showgrid=False, linecolor="#D7E1EA")
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False)
    if tasa:
        fig.update_yaxes(range=[0, 105], ticksuffix="%")
    return fig


def barras_por_centro(tabla: pd.DataFrame, metrica: str, color: str, tasa=False) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tabla["centro"],
        y=tabla[metrica],
        marker_color=color,
        customdata=tabla["envios"],
        text=(tabla[metrica].map(lambda x: f"{x:.1f}%") if tasa else tabla[metrica].map(str)),
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>" +
            ("Puntualidad: %{y:.1f}%" if tasa else "Cantidad: %{y:,.0f}") +
            "<br>Envíos (n): %{customdata:,.0f}<extra></extra>"
        ),
    ))
    fig = estilo(fig, tasa=tasa)
    if not tasa:
        maximo = float(tabla[metrica].max())
        fig.update_yaxes(range=[0, max(1.0, maximo * 1.18)])
    return fig


def puntualidad_por_destino(df: pd.DataFrame, centros_visibles: list[str]) -> go.Figure:
    fig = go.Figure()
    for destino, color in [("Urbana", SOFT_BLUE), ("Periferica", SOFT_ORANGE)]:
        rates, sizes = [], []
        for centro in centros_visibles:
            s = indicadores(df.loc[(df["centro"] == centro) & (df["destino"] == destino)])
            rates.append(s["puntualidad_pct"])
            sizes.append(s["envios"])
        fig.add_trace(go.Bar(
            name=destino,
            x=centros_visibles,
            y=rates,
            marker_color=color,
            customdata=sizes,
            hovertemplate=(
                f"<b>%{{x}} · {destino}</b><br>"
                "Puntualidad: %{y:.1f}%<br>Envíos (n): %{customdata}<extra></extra>"
            ),
        ))
    fig = estilo(fig, tasa=True, leyenda=True)
    fig.update_layout(barmode="group")
    return fig


def evolucion_mensual(df: pd.DataFrame, centros_visibles: list[str]) -> go.Figure:
    fig = go.Figure()
    for centro in centros_visibles:
        rates = []
        for mes in MESES:
            datos = df.loc[(df["centro"] == centro) & (df["mes"] == mes)]
            rates.append(indicadores(datos)["puntualidad_pct"])
        fig.add_trace(go.Scatter(
            x=MESES,
            y=rates,
            mode="lines+markers",
            name=centro,
            line=dict(width=2.6, color=COLORES_CENTRO[centro]),
            marker=dict(size=8),
            connectgaps=False,
            hovertemplate=f"<b>{centro}</b><br>Mes: %{{x}}<br>Puntualidad: %{{y:.1f}}%<extra></extra>",
        ))
    fig = estilo(fig, alto=335, leyenda=True)
    fig.update_yaxes(range=[60, 100], ticksuffix="%")
    return fig


def formatear_entero(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def tasa_o_guion(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:.1f}%".replace(".", ",")


def reiniciar_filtros():
    for llave in ("f_mes", "f_centro", "f_servicio", "f_destino"):
        st.session_state[llave] = "Todos"


# Estilos de la interfaz, sin estilos externos ni recursos de red.
st.markdown("""
<style>
  .stApp { background: #F4F7FB; }
  .block-container { max-width: 1370px; padding-top: 1.55rem; }
  .nx-header {
    background:linear-gradient(115deg,#10213b 0%,#16365b 100%);
    padding:25px 30px; border-radius:18px; color:white;
    margin-bottom:20px;
  }
  .nx-brand {color:#8CDDED; letter-spacing:2.4px; font-size:0.73rem;
    font-weight:800; margin-bottom:12px;}
  .nx-header h1 {color:white; font-size:2.05rem; margin:0; font-weight:800;}
  .nx-header p {color:#D5E1EC; font-size:0.94rem; margin:9px 0 0;}
  .nx-badge {background:#2F566D; display:inline-block; border-radius:14px;
    font-size:0.75rem; padding:5px 10px; margin-top:13px;color:#E8F2F9;}
  .nx-section {font-size:1.28rem; font-weight:750; color:#182F48;
     margin:13px 0 5px;}
  .nx-footnote {color:#6E8095; font-size:0.80rem; line-height:1.5;}
  div[data-testid="stMetric"] {background:#FFFFFF; border:1px solid #E0E7F0;
     border-radius:12px; padding:15px 17px; min-height:123px;}
  div[data-testid="stMetricLabel"] {color:#61738B;}
  div[data-testid="stMetricValue"] {font-size:1.75rem; color:#15324A;}
  div[data-testid="stVerticalBlockBorderWrapper"] {background:#FFFFFF;
     border-radius:14px; border-color:#E0E7F0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<section class="nx-header">
  <div class="nx-brand">NX · NEXOLOG · INTELIGENCIA OPERATIVA</div>
  <h1>Desempeño de entregas</h1>
  <p>Explora volumen, puntualidad, retrasos y reclamos para identificar oportunidades de mejora operativa.</p>
  <span class="nx-badge">Agosto a octubre de 2026 · Datos sintéticos · DATA1002</span>
</section>
""", unsafe_allow_html=True)

try:
    datos = cargar_datos()
except (FileNotFoundError, ValueError) as exc:
    st.error(str(exc))
    st.info("Para publicar la app, sube app.py, NexoLog_envios.csv y requirements.txt al mismo repositorio.")
    st.stop()

st.markdown("#### Explorar segmentos")
c1, c2, c3, c4, c5 = st.columns([1.0, 1.0, 1.0, 1.0, 0.75], vertical_alignment="bottom")
with c1:
    mes = st.selectbox("Mes", ["Todos"] + MESES, key="f_mes")
with c2:
    centro = st.selectbox("Centro", ["Todos"] + CENTROS, key="f_centro")
with c3:
    servicio = st.selectbox("Servicio", ["Todos"] + SERVICIOS, key="f_servicio")
with c4:
    destino = st.selectbox("Destino", ["Todos"] + DESTINOS, key="f_destino")
with c5:
    st.button("Restablecer", on_click=reiniciar_filtros, use_container_width=True)

filtrado = datos.copy()
for columna, valor in [("mes", mes), ("centro", centro), ("servicio", servicio), ("destino", destino)]:
    if valor != "Todos":
        filtrado = filtrado.loc[filtrado[columna] == valor]

m = indicadores(filtrado)
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Envíos despachados", formatear_entero(m["envios"]))
with k2:
    st.metric("Entregas a tiempo", tasa_o_guion(m["puntualidad_pct"]))
with k3:
    st.metric("Entregas retrasadas", formatear_entero(m["retrasados"]))
with k4:
    st.metric("Envíos con reclamo", formatear_entero(m["reclamos"]))
with k5:
    st.metric(
        "Costo operativo medio",
        "—" if m["costo_medio"] is None else f"{m['costo_medio']:.1f}".replace(".", ","),
        help="Miles de pesos colombianos (COP) por envío",
    )
st.caption("El costo operativo medio se presenta en miles de COP por envío.")

if filtrado.empty:
    st.warning("No hay envíos para esta combinación de filtros. Selecciona otros valores o restablece los filtros.")
    st.stop()

resumen = resumen_por_centro(filtrado)
centros_visibles = resumen["centro"].tolist()

st.markdown('<div class="nx-section">¿Dónde se concentran los retrasos?</div>', unsafe_allow_html=True)
st.caption("Compara tasas y cantidades: pueden señalar prioridades operativas distintas.")

col_izq, col_der = st.columns(2, gap="medium")
with col_izq:
    with st.container(border=True):
        st.markdown("**Puntualidad por centro**")
        st.caption("Porcentaje de envíos entregados en el tiempo comprometido.")
        st.plotly_chart(barras_por_centro(resumen, "puntualidad_pct", BLUE, tasa=True), use_container_width=True)
with col_der:
    with st.container(border=True):
        st.markdown("**Volumen de entregas retrasadas**")
        st.caption("Número absoluto de envíos fuera de plazo.")
        st.plotly_chart(barras_por_centro(resumen, "retrasados", ORANGE), use_container_width=True)

col_izq, col_der = st.columns(2, gap="medium")
with col_izq:
    with st.container(border=True):
        st.markdown("**Puntualidad según destino**")
        st.caption("Comparación entre entregas urbanas y periféricas.")
        st.plotly_chart(puntualidad_por_destino(filtrado, centros_visibles), use_container_width=True)
with col_der:
    with st.container(border=True):
        st.markdown("**Reclamos recibidos**")
        st.caption("Número de envíos que registraron un reclamo.")
        st.plotly_chart(barras_por_centro(resumen, "reclamos", VIOLET), use_container_width=True)

with st.container(border=True):
    st.markdown("**Evolución mensual de la puntualidad**")
    st.caption("Tasas por centro, con independencia de diferencias en volumen o composición por mes.")
    st.plotly_chart(evolucion_mensual(filtrado, centros_visibles), use_container_width=True)

st.markdown('<div class="nx-section">Detalle operacional</div>', unsafe_allow_html=True)
st.caption("Valores calculados sobre los mismos filtros que los gráficos.")
mostrada = resumen[[
    "centro", "envios", "puntualidad_pct", "retrasados", "reclamos", "costo_medio"
]].rename(columns={
    "centro": "Centro", "envios": "Envíos", "puntualidad_pct": "A tiempo (%)",
    "retrasados": "Retrasados", "reclamos": "Con reclamo",
    "costo_medio": "Costo medio (miles COP)",
})
st.dataframe(
    mostrada,
    hide_index=True,
    use_container_width=True,
    column_config={
        "A tiempo (%)": st.column_config.NumberColumn(format="%.1f%%"),
        "Costo medio (miles COP)": st.column_config.NumberColumn(format="%.1f"),
    },
)

with st.expander("Notas metodológicas y datos de respaldo", expanded=False):
    st.markdown("""
    - **Granularidad:** cada fila del archivo representa un envío único.
    - **Puntualidad:** envíos con `a_tiempo == 'Si'` / total de envíos de la selección.
    - **Retrasados:** envíos que no se entregaron a tiempo.
    - **Reclamos:** número de envíos con `reclamo == 'Si'` (no número de comunicaciones recibidas).
    - **Costo medio:** promedio de `costo_operativo_miles_cop`, en miles de COP por envío.
    - **Advertencia:** las categorías de retraso son operativas, no evidencias de causalidad.
      Los datos no contienen el costo de los posibles pilotos ni resultados contrafactuales.
    - **Alcance:** todos los registros son simulados y no representan una operación real.
    """)
    st.download_button(
        "Descargar envíos de la selección (CSV)",
        filtrado.to_csv(index=False).encode("utf-8-sig"),
        file_name="NexoLog_envios_filtrados.csv",
        mime="text/csv",
        use_container_width=False,
    )

st.markdown(
    '<p class="nx-footnote">NexoLog · Simulación educativa de DATA1002 · '
    'Los resultados no corresponden a una empresa real.</p>',
    unsafe_allow_html=True,
)
