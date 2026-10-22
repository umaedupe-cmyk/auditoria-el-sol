import streamlit as pd_st  # Usamos un alias para evitar conflictos de nombres
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
pd_st.set_page_config(
    page_title="Audit-Bot: Análisis Global y Riesgos - Compañía El Sol S.A.",
    page_icon="📊",
    layout="wide"
)

pd_st.title("🛡️ Dashboard Interactivo de Procedimientos Analíticos y Riesgos")
pd_st.markdown("### Grupo 5: Auditoría Financiera 2026-2 | Universidad María Auxiliadora")
pd_st.markdown("Herramienta basada en **NIA 520, NIA 240, NIA 315** y el **Marco de Control Interno** para la Compañía El Sol S.A.")

# 1. Crear datos de ejemplo (Simulación del Balance de Comprobación BC-2 de El Sol S.A.)
@pd_st.cache_data
def cargar_datos_ejemplo():
    data = {
        "Cuenta_Codigo": ["10", "12", "20", "33", "40", "42", "50", "60", "69", "70"],
        "Nombre_Cuenta": [
            "Efectivo y Equivalentes de Efectivo",
            "Cuentas por Cobrar Comerciales",
            "Existencias (Inventarios)",
            "Propiedades, Planta y Equipo",
            "Tributos por Pagar",
            "Cuentas por Pagar Comerciales",
            "Capital Social",
            "Compras",
            "Costo de Ventas",
            "Ventas (Ingresos Operacionales)"
        ],
        "Tipo": ["Activo", "Activo", "Activo", "Activo", "Pasivo", "Pasivo", "Patrimonio", "Resultado", "Resultado", "Resultado"],
        "Anio_Anterior": [120000, 450000, 600000, 1500000, 80000, 320000, 1000000, 1400000, 1100000, 2200000],
        "Anio_Actual": [95000, 680000, 550000, 1550000, 95000, 510000, 1000000, 1350000, 1050000, 2450000]
    }
    return pd.DataFrame(data)

# Sidebar para carga de datos o uso de ejemplo
pd_st.sidebar.header("📁 Configuración de Datos")
uploaded_file = pd_st.sidebar.file_uploader("Sube tu Balance de Comprobación (CSV)", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    pd_st.sidebar.success("¡Archivo cargado correctamente!")
else:
    pd_st.sidebar.info("Usando datos simulados estándar de la Compañía El Sol S.A. (Puedes subir tu CSV con columnas: Cuenta_Codigo, Nombre_Cuenta, Tipo, Anio_Anterior, Anio_Actual)")
    df = cargar_datos_ejemplo()

# 2. Cálculos Financieros y Análisis Horizontal / Vertical
df["Variacion_Absoluta"] = df["Anio_Actual"] - df["Anio_Anterior"]
df["Variacion_Porcentual"] = (df["Variacion_Absoluta"] / df["Anio_Anterior"]) * 100

# Análisis Vertical sobre el Total Activo o Total Ventas aproximado
total_activo_act = df[df["Tipo"] == "Activo"]["Anio_Actual"].sum()
total_ventas_act = df[df["Nombre_Cuenta"].str.contains("Ventas", case=False, na=False)]["Anio_Actual"].values
total_ventas_act = total_ventas_act[0] if len(total_ventas_act) > 0 else 1

df["Participacion_Activo_%"] = np.where(df["Tipo"] == "Activo", (df["Anio_Actual"] / total_activo_act) * 100, 0)

# 3. Módulo de Alertas de Auditoría y Triángulo del Fraude (NIA 240 / NIA 520)
def evaluar_riesgo(row):
    nombre_cta = str(row["Nombre_Cuenta"])
    variacion = float(row["Variacion_Porcentual"])
    
    if "Cuentas por Cobrar" in nombre_cta and variacion > 30:
        return "🚨 ALTA (Presión de metas / Posible colusión o ventas ficticias)"
    elif "Efectivo" in nombre_cta and variacion < -20:
        return "⚠️ MEDIA (Riesgo de faltantes / Jineteo de fondos)"
    elif "Cuentas por Pagar" in nombre_cta and variacion > 50:
        return "🚨 ALTA (Pasivos omitidos / Corte de operaciones deficiente)"
    elif variacion > 25:
        return "⚠️ MEDIA (Variación atípica significativa - NIA 520)"
    elif variacion < -25:
        return "⚠️ MEDIA (Reducción abrupta inusual)"
    else:
        return "✅ Normal"

df["Alerta_Riesgo"] = df.apply(evaluar_riesgo, axis=1)

# 4. Dashboard Visual - Pestañas principales
tab1, tab2, tab3, tab4 = pd_st.tabs([
    "📊 Análisis Horizontal y Vertical", 
    "🚨 Alertas de Fraude y Riesgos (NIA 240/315)", 
    "📈 Gráficos Interactivos", 
    "📝 Reporte Sintético de Auditoría"
])

with tab1:
    pd_st.subheader("Cédula Sumaria: Balance de Comprobación Comparativo")
    pd_st.dataframe(df.style.format({
        "Anio_Anterior": "{:,.2f}",
        "Anio_Actual": "{:,.2f}",
        "Variacion_Absoluta": "{:,.2f}",
        "Variacion_Porcentual": "{:.2f}%",
        "Participacion_Activo_%": "{:.2f}%"
    }), use_container_width=True)

with tab2:
    pd_st.subheader("Matriz Automatizada de Alertas e Indicadores de Riesgo")
    pd_st.markdown("Detección de variaciones inusuales según **NIA 520** vinculadas a los factores del **Triángulo del Fraude**:")
    
    # Filtrar solo cuentas con alertas importantes
    df_alertas = df[df["Alerta_Riesgo"] != "✅ Normal"]
    if not df_alertas.empty:
        pd_st.dataframe(df_alertas[["Cuenta_Codigo", "Nombre_Cuenta", "Anio_Anterior", "Anio_Actual", "Variacion_Porcentual", "Alerta_Riesgo"]], use_container_width=True)
    else:
        pd_st.success("No se detectaron alertas críticas con los umbrales actuales.")

with tab3:
    pd_st.subheader("Visualización Gráfica de Variaciones")
    col1, col2 = pd_st.columns(2)
    
    with col1:
        fig_bar = px.bar(df, x="Nombre_Cuenta", y=["Anio_Anterior", "Anio_Actual"], barmode="group", title="Comparativa Periodo N vs N-1")
        fig_bar.update_layout(xaxis_tickangle=-45)
        pd_st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        fig_pie = px.pie(df[df["Tipo"] == "Activo"], names="Nombre_Cuenta", values="Anio_Actual", title="Composición del Activo (Año Actual)")
        pd_st.plotly_chart(fig_pie, use_container_width=True)

with tab4:
    pd_st.subheader("Generador Automático de Conclusiones y Reporte de Riesgos")
    
    # Redacción automática basada en los hallazgos
    cuentas_criticas = len(df[df["Alerta_Riesgo"].str.contains("ALTA")])
    
    reporte_texto = f"""
    ### INFORME TÉCNICO PRELIMINAR - PROCEDIMIENTOS ANALÍTICOS GLOBALES (NIA 520)
    **Compañía El Sol S.A.**
    
    1. **Resumen Ejecutivo:** Se ha efectuado el análisis horizontal y vertical del Balance de Comprobación comparativo. El sistema ha identificado un total de **{cuentas_criticas} cuentas con alertas de riesgo alto** que requieren pruebas sustantivas de detalle adicionales por parte del equipo de auditoría.
    2. **Hallazgos Clave:**
       - Se observa un incremento desproporcionado en las Cuentas por Cobrar Comerciales y Cuentas por Pagar, lo que sugiere posibles riesgos en la gestión del recaudo, políticas agresivas de reconocimiento de ingresos o acumulación de pasivos no registrados al cierre del ejercicio.
       - Las variaciones superan los umbrales de materialidad definidos en la planeación bajo NIA 315.
    3. **Conclusión y Recomendación de Auditoría:** Se recomienda cruzar estos resultados con las pruebas específicas de los Grupos 1 al 4 (Efectivo, Cartera, Compras y Activos Fijos) para mitigar el riesgo de incorrección material debido a fraude o error.
    """
    pd_st.markdown(reporte_texto)
    pd_st.download_button(label="📥 Descargar Reporte en Texto", data=reporte_texto, file_name="Reporte_Sintetico_Riesgos_El_Sol.txt")
