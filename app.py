import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Audit-Bot: Análisis Global y Riesgos - Compañía El Sol S.A.",
    page_icon="📊",
    layout="wide",
)

st.title("🛡️ Dashboard Interactivo de Procedimientos Analíticos y Riesgos")
st.markdown("### Grupo 5: Auditoría Financiera 2026-2 | Universidad María Auxiliadora")
st.markdown(
    "Herramienta basada en **NIA 520** (procedimientos analíticos), **NIA 240** (fraude), "
    "**NIA 315** (valoración de riesgos), **NIA 320** (materialidad) y el **Marco de Control Interno** "
    "para la Compañía El Sol S.A."
)

COLUMNAS = ["Cuenta_Codigo", "Nombre_Cuenta", "Tipo", "Anio_Anterior", "Anio_Actual"]


@st.cache_data
def cargar_datos_ejemplo():
    return pd.DataFrame({
        "Cuenta_Codigo": ["10", "12", "20", "33", "40", "42", "50", "60", "69", "70"],
        "Nombre_Cuenta": [
            "Efectivo y Equivalentes de Efectivo", "Cuentas por Cobrar Comerciales",
            "Existencias (Inventarios)", "Propiedades, Planta y Equipo", "Tributos por Pagar",
            "Cuentas por Pagar Comerciales", "Capital Social", "Compras", "Costo de Ventas",
            "Ventas (Ingresos Operacionales)",
        ],
        "Tipo": ["Activo", "Activo", "Activo", "Activo", "Pasivo", "Pasivo", "Patrimonio",
                 "Resultado", "Resultado", "Resultado"],
        "Anio_Anterior": [120000, 450000, 600000, 1500000, 80000, 320000, 1000000, 1400000, 1100000, 2200000],
        "Anio_Actual": [95000, 680000, 550000, 1550000, 95000, 510000, 1000000, 1350000, 1050000, 2450000],
    })


# ---------------------------------------------------------------- Sidebar
st.sidebar.header("📁 Configuración de Datos")
archivo = st.sidebar.file_uploader("Sube tu Balance de Comprobación (CSV o Excel)", type=["csv", "xlsx"])
st.sidebar.download_button(
    "Descargar plantilla CSV",
    cargar_datos_ejemplo().to_csv(index=False).encode("utf-8"),
    "plantilla_BC2.csv",
    "text/csv",
)
st.sidebar.caption("Columnas requeridas: " + ", ".join(COLUMNAS) + ". Tipo: Activo, Pasivo, Patrimonio o Resultado.")

if archivo is not None:
    try:
        df = pd.read_excel(archivo) if archivo.name.lower().endswith(".xlsx") else pd.read_csv(archivo)
    except Exception as e:
        st.sidebar.error(f"No se pudo leer el archivo: {e}")
        st.stop()
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        st.sidebar.error("Faltan columnas: " + ", ".join(faltan))
        st.stop()
    st.sidebar.success("¡Archivo cargado correctamente!")
    usando_ejemplo = False
else:
    df = cargar_datos_ejemplo()
    usando_ejemplo = True

if usando_ejemplo:
    st.warning("Estás viendo datos simulados. Sube el BC-2 real del caso desde la barra lateral.")

st.sidebar.header("⚙️ Parámetros de auditoría")
umbral_var = st.sidebar.slider("Umbral de variación inusual (%)", 5, 50, 20)
pct_mat = st.sidebar.number_input("Materialidad global (% de ventas)", 0.1, 5.0, 1.0, 0.1)
pct_tol = st.sidebar.slider("Error tolerable (% de la materialidad)", 50, 90, 75)
brecha = st.sidebar.slider("Brecha cartera/pasivos vs. ventas/compras (puntos %)", 5, 50, 20)

# ---------------------------------------------------------------- Limpieza
df = df[COLUMNAS].copy()
df["Cuenta_Codigo"] = df["Cuenta_Codigo"].astype(str).str.strip()
df["Nombre_Cuenta"] = df["Nombre_Cuenta"].astype(str).str.strip()
df["Tipo"] = df["Tipo"].astype(str).str.strip().str.capitalize()
for c in ("Anio_Anterior", "Anio_Actual"):
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

# ---------------------------------------------------------------- Saldos clave
CUENTAS = {
    "efectivo": (("10",), ["^Efectivo"]),
    "cxc": (("12",), ["Cuentas por Cobrar"]),
    "exist": (("20",), ["Existencias", "Inventario"]),
    "tributos": (("40",), ["^Tributos"]),
    "cxp": (("42",), ["Cuentas por Pagar"]),
    "compras": (("60",), ["^Compras"]),
    "costo": (("69",), ["Costo de Ventas"]),
    "ventas": (("70",), ["^Ventas", "Ingresos Operacionales"]),
}


def mask_cuenta(codigos, palabras):
    por_codigo = df["Cuenta_Codigo"].str.startswith(tuple(codigos))
    por_nombre = df["Nombre_Cuenta"].str.contains("|".join(palabras), case=False, regex=True, na=False)
    return por_codigo | por_nombre


def saldos(col):
    return {k: float(df.loc[mask_cuenta(*v), col].sum()) for k, v in CUENTAS.items()}


def pct(a, b):
    return (a - b) / b * 100 if b else np.nan


def razon(a, b):
    return a / b if b else np.nan


def ratios(s):
    return {
        "margen": razon(s["ventas"] - s["costo"], s["ventas"]) * 100,
        "dso": razon(s["cxc"], s["ventas"]) * 365,
        "rot_cxc": razon(s["ventas"], s["cxc"]),
        "dio": razon(s["exist"], s["costo"]) * 365,
        "rot_inv": razon(s["costo"], s["exist"]),
        "dpo": razon(s["cxp"], s["compras"]) * 365,
        "rot_cxp": razon(s["compras"], s["cxp"]),
        "liq": razon(s["efectivo"] + s["cxc"] + s["exist"], s["tributos"] + s["cxp"]),
    }


S0, S1 = saldos("Anio_Anterior"), saldos("Anio_Actual")
R0, R1 = ratios(S0), ratios(S1)

# ---------------------------------------------------------------- Materialidad (NIA 320)
act0 = df.loc[df["Tipo"] == "Activo", "Anio_Anterior"].sum()
act1 = df.loc[df["Tipo"] == "Activo", "Anio_Actual"].sum()
base_mat = S1["ventas"] if S1["ventas"] else act1
materialidad = base_mat * pct_mat / 100
tolerable = materialidad * pct_tol / 100

# ---------------------------------------------------------------- Análisis horizontal y vertical
df["Variacion_Absoluta"] = df["Anio_Actual"] - df["Anio_Anterior"]
df["Variacion_Porcentual"] = df["Variacion_Absoluta"] / df["Anio_Anterior"].replace(0, np.nan) * 100


def vertical(col, base_act, base_ventas):
    base = np.where(df["Tipo"] == "Resultado", base_ventas, base_act).astype(float)
    base = np.where(base == 0, np.nan, base)
    return df[col] / base * 100


df["Vertical_Anterior_%"] = vertical("Anio_Anterior", act0, S0["ventas"])
df["Vertical_Actual_%"] = vertical("Anio_Actual", act1, S1["ventas"])
df["Revisar"] = np.where(
    (df["Variacion_Porcentual"].abs() > umbral_var) & (df["Variacion_Absoluta"].abs() > tolerable),
    "🚨 Sí", "✅ No",
)

# ---------------------------------------------------------------- Alertas (NIA 240 / 315 / 520)
alertas = []
cubiertas = pd.Series(False, index=df.index)


def monto(m):
    return abs(df.loc[m, "Variacion_Absoluta"].sum())


def add(nivel, indicador, hallazgo, m, aseveracion, triangulo, grupo, control):
    mt = monto(m)
    alertas.append({
        "Nivel": nivel, "Cuenta_Indicador": indicador, "Hallazgo": hallazgo,
        "Monto_Variacion": mt, "Supera_Error_Tolerable": "Sí" if mt > tolerable else "No",
        "Aseveracion": aseveracion, "Triangulo_Fraude": triangulo,
        "Grupo_Relacionado": grupo, "Control_a_Evaluar": control,
    })


v_ventas, v_cxc = pct(S1["ventas"], S0["ventas"]), pct(S1["cxc"], S0["cxc"])
v_cxp, v_compras = pct(S1["cxp"], S0["cxp"]), pct(S1["compras"], S0["compras"])
v_efectivo, v_costo = pct(S1["efectivo"], S0["efectivo"]), pct(S1["costo"], S0["costo"])

m_cxc, m_cxp = mask_cuenta(*CUENTAS["cxc"]), mask_cuenta(*CUENTAS["cxp"])
m_efe, m_costo = mask_cuenta(*CUENTAS["efectivo"]), mask_cuenta(*CUENTAS["costo"])

if pd.notna(v_cxc) and pd.notna(v_ventas) and v_cxc - v_ventas > brecha:
    add("ALTA", "Cuentas por Cobrar vs. Ventas",
        f"Cartera {v_cxc:+.1f}% frente a ventas {v_ventas:+.1f}%. Días de cobro: {R0['dso']:.0f} → {R1['dso']:.0f}.",
        m_cxc, "Existencia y Valuación",
        "Presión (metas de ventas) + Oportunidad (colusión caja/cartera)",
        "Grupo 2 – circularización y deterioro",
        "Segregación de funciones caja/cartera; conciliación periódica de saldos")
    cubiertas |= m_cxc

if pd.notna(v_cxp) and pd.notna(v_compras) and v_cxp - v_compras > brecha:
    add("ALTA", "Cuentas por Pagar vs. Compras",
        f"Cuentas por pagar {v_cxp:+.1f}% frente a compras {v_compras:+.1f}%. Días de pago: {R0['dpo']:.0f} → {R1['dpo']:.0f}.",
        m_cxp, "Integridad y Corte",
        "Presión (mejorar resultados/liquidez) + Racionalización",
        "Grupo 3 – pasivos omitidos y corte de operaciones",
        "Control de recepción y registro oportuno de facturas al cierre")
    cubiertas |= m_cxp

if pd.notna(v_efectivo) and v_efectivo < -umbral_var:
    add("MEDIA", "Efectivo y Equivalentes",
        f"El efectivo cae {v_efectivo:.1f}% ({S0['efectivo']:,.0f} → {S1['efectivo']:,.0f}).",
        m_efe, "Existencia y Derechos", "Oportunidad (jineteo de fondos, faltantes)",
        "Grupo 1 – arqueos y conciliaciones bancarias",
        "Arqueos sorpresivos y conciliaciones bancarias mensuales")
    cubiertas |= m_efe

dif_margen = R1["margen"] - R0["margen"]
if pd.notna(dif_margen) and abs(dif_margen) > 5:
    add("MEDIA", "Margen bruto",
        f"Margen bruto {R0['margen']:.1f}% → {R1['margen']:.1f}% (costo de ventas {v_costo:+.1f}%, ventas {v_ventas:+.1f}%).",
        m_costo, "Ocurrencia e Integridad del costo",
        "Presión (resultados) + Racionalización",
        "Grupos 3 y 4 – corte de compras y existencias",
        "Revisión de costeo, inventarios y corte de ventas")
    cubiertas |= m_costo

for i, r in df.iterrows():
    if cubiertas[i]:
        continue
    vp, va = r["Variacion_Porcentual"], r["Variacion_Absoluta"]
    if pd.notna(vp) and abs(vp) > umbral_var and abs(va) > tolerable:
        add("MEDIA", r["Nombre_Cuenta"], f"Variación atípica de {vp:+.1f}% ({va:+,.0f}).",
            df.index == i, "Por determinar", "Por evaluar", "Pruebas de detalle según la cuenta",
            "Revisar autorizaciones y soporte de los movimientos")

COLS_ALERTA = ["Nivel", "Cuenta_Indicador", "Hallazgo", "Monto_Variacion", "Supera_Error_Tolerable",
               "Aseveracion", "Triangulo_Fraude", "Grupo_Relacionado", "Control_a_Evaluar"]
alertas_df = pd.DataFrame(alertas, columns=COLS_ALERTA)
alertas_df = alertas_df.sort_values("Nivel", key=lambda s: s.map({"ALTA": 0, "MEDIA": 1}), kind="stable")
n_alta = int((alertas_df["Nivel"] == "ALTA").sum())
n_media = int((alertas_df["Nivel"] == "MEDIA").sum())

# ---------------------------------------------------------------- Tabla de ratios
ETIQUETAS = {
    "margen": "Margen bruto (%)", "dso": "Días de cobro (DSO)", "rot_cxc": "Rotación de cartera (veces)",
    "dio": "Días de inventario (DIO)", "rot_inv": "Rotación de inventarios (veces)",
    "dpo": "Días de pago (DPO)", "rot_cxp": "Rotación de cuentas por pagar (veces)",
    "liq": "Liquidez corriente (veces)",
}
df_ratios = pd.DataFrame({
    "Indicador": [ETIQUETAS[k] for k in ETIQUETAS],
    "Anio_Anterior": [R0[k] for k in ETIQUETAS],
    "Anio_Actual": [R1[k] for k in ETIQUETAS],
})
df_ratios["Variacion"] = df_ratios["Anio_Actual"] - df_ratios["Anio_Anterior"]


# ---------------------------------------------------------------- Reporte
def construir_reporte():
    L = [
        "### INFORME TÉCNICO PRELIMINAR - PROCEDIMIENTOS ANALÍTICOS GLOBALES (NIA 520)",
        "**Compañía El Sol S.A.** | Auditoría Financiera 2026-2 | Grupo 5",
        "",
        f"**1. Base de evaluación (NIA 315 / NIA 320).** Materialidad global: {materialidad:,.0f} UM "
        f"({pct_mat:.1f}% de {base_mat:,.0f}). Error tolerable: {tolerable:,.0f} UM ({pct_tol}% de la materialidad). "
        f"Umbral de variación inusual: {umbral_var}%.",
        "",
        f"**2. Resumen ejecutivo.** Se aplicó análisis horizontal, vertical y de rotaciones al balance de comprobación "
        f"comparativo. Se identificaron **{n_alta} alertas de riesgo alto** y **{n_media} de riesgo medio** que requieren "
        f"pruebas sustantivas adicionales.",
        "",
        "**3. Hallazgos clave:**",
    ]
    if alertas_df.empty:
        L.append("- No se detectaron variaciones que superen los umbrales definidos.")
    for r in alertas_df.itertuples(index=False):
        L.append(f"- **[{r.Nivel}] {r.Cuenta_Indicador}:** {r.Hallazgo} "
                 f"Aseveración: {r.Aseveracion}. Triángulo del Fraude: {r.Triangulo_Fraude}. {r.Grupo_Relacionado}.")
    controles = [c for c in alertas_df["Control_a_Evaluar"].unique() if c]
    L += ["", "**4. Evaluación preliminar de control interno:**"]
    L += [f"- Evaluar: {c}." for c in controles] or ["- Sin debilidades preliminares identificadas."]
    L += [
        "",
        "**5. Conclusión y dictamen propuesto (preliminar):** Los procedimientos analíticos no sustentan por sí solos una "
        + ("opinión. Las alertas altas exigen pruebas de detalle de los Grupos 1 al 4 antes de concluir; si se confirman "
           "incorrecciones materiales, correspondería un dictamen con salvedad." if n_alta else
           "opinión. No se observan alertas altas; se recomienda completar las pruebas de los Grupos 1 al 4."),
    ]
    return "\n".join(L)


def exportar_excel():
    buf = io.BytesIO()
    params = pd.DataFrame({
        "Parametro": ["Umbral variacion (%)", "Materialidad global", "Error tolerable", "Brecha (pts %)"],
        "Valor": [umbral_var, round(materialidad, 2), round(tolerable, 2), brecha],
    })
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        params.to_excel(w, sheet_name="Parametros", index=False)
        df.to_excel(w, sheet_name="Cedula_Sumaria", index=False)
        df_ratios.to_excel(w, sheet_name="Ratios", index=False)
        alertas_df.to_excel(w, sheet_name="Alertas", index=False)
    return buf.getvalue()


# ---------------------------------------------------------------- Pestañas
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Análisis Horizontal y Vertical",
    "🚨 Alertas de Fraude y Riesgos (NIA 240/315)",
    "📈 Gráficos Interactivos",
    "📝 Reporte Sintético de Auditoría",
])

with tab1:
    st.subheader("Cédula Sumaria: Balance de Comprobación Comparativo")
    st.caption("Análisis vertical: cuentas de balance sobre el total activo; cuentas de resultados sobre las ventas.")
    st.dataframe(df.style.format({
        "Anio_Anterior": "{:,.2f}", "Anio_Actual": "{:,.2f}", "Variacion_Absoluta": "{:,.2f}",
        "Variacion_Porcentual": "{:.2f}%", "Vertical_Anterior_%": "{:.2f}%", "Vertical_Actual_%": "{:.2f}%",
    }, na_rep="-"), use_container_width=True)
    st.subheader("Indicadores de rotación y liquidez")
    st.caption("Calculados con saldos finales de cada año; días sobre base de 365.")
    st.dataframe(df_ratios.style.format({
        "Anio_Anterior": "{:,.2f}", "Anio_Actual": "{:,.2f}", "Variacion": "{:+,.2f}",
    }, na_rep="-"), use_container_width=True)

with tab2:
    st.subheader("Matriz Automatizada de Alertas e Indicadores de Riesgo")
    st.markdown("Variaciones inusuales según **NIA 520**, vinculadas a los factores del **Triángulo del Fraude** "
                "(presión, oportunidad y racionalización).")
    c1, c2, c3 = st.columns(3)
    c1.metric("Alertas ALTAS", n_alta)
    c2.metric("Alertas MEDIAS", n_media)
    c3.metric("Materialidad (UM)", f"{materialidad:,.0f}")
    if alertas_df.empty:
        st.success("No se detectaron alertas con los umbrales actuales.")
    else:
        vista = alertas_df.copy()
        vista["Nivel"] = vista["Nivel"].map({"ALTA": "🚨 ALTA", "MEDIA": "⚠️ MEDIA"})
        st.dataframe(vista.style.format({"Monto_Variacion": "{:,.0f}"}), use_container_width=True)

with tab3:
    st.subheader("Visualización Gráfica de Variaciones")
    col1, col2 = st.columns(2)
    with col1:
        fig_b = px.bar(df[df["Tipo"] != "Resultado"], x="Nombre_Cuenta", y=["Anio_Anterior", "Anio_Actual"],
                       barmode="group", title="Cuentas de balance: periodo N vs N-1")
        fig_b.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_b, use_container_width=True)
        fig_v = px.bar(df, x="Nombre_Cuenta", y="Variacion_Porcentual",
                       color=df["Variacion_Porcentual"].abs() > umbral_var,
                       color_discrete_map={True: "#d62728", False: "#1f77b4"},
                       title=f"Variación porcentual (rojo = supera ±{umbral_var}%)")
        fig_v.add_hline(y=umbral_var, line_dash="dash")
        fig_v.add_hline(y=-umbral_var, line_dash="dash")
        fig_v.update_layout(xaxis_tickangle=-45, showlegend=False)
        st.plotly_chart(fig_v, use_container_width=True)
    with col2:
        fig_r = px.bar(df[df["Tipo"] == "Resultado"], x="Nombre_Cuenta", y=["Anio_Anterior", "Anio_Actual"],
                       barmode="group", title="Cuentas de resultados: periodo N vs N-1")
        st.plotly_chart(fig_r, use_container_width=True)
        dias = df_ratios[df_ratios["Indicador"].str.contains("Días")].melt(
            id_vars="Indicador", value_vars=["Anio_Anterior", "Anio_Actual"])
        fig_d = px.bar(dias, x="Indicador", y="value", color="variable", barmode="group",
                       title="Días de cobro, inventario y pago")
        st.plotly_chart(fig_d, use_container_width=True)
    fig_p = px.pie(df[df["Tipo"] == "Activo"], names="Nombre_Cuenta", values="Anio_Actual",
                   title="Composición del Activo (año actual)")
    st.plotly_chart(fig_p, use_container_width=True)

with tab4:
    st.subheader("Generador Automático de Conclusiones y Reporte de Riesgos")
    reporte_texto = construir_reporte()
    st.markdown(reporte_texto)
    d1, d2 = st.columns(2)
    d1.download_button("📥 Descargar reporte (texto)", reporte_texto,
                       file_name="Reporte_Sintetico_Riesgos_El_Sol.txt")
    d2.download_button("📥 Descargar papeles de trabajo (Excel)", exportar_excel(),
                       file_name="Papeles_Trabajo_Grupo5_El_Sol.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
