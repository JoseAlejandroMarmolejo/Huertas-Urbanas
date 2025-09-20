import streamlit as st
import pandas as pd
# --- CORRECCIÓN ---
# Se ha corregido el nombre del módulo importado.
from preprocesamiento import (
    cargar_y_limpiar_csv, 
    inicializar_firebase, 
    procesar_con_gemini, 
    guardar_en_firestore
)

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Huertas Urbanas | Preprocesamiento",
    page_icon="🌱",
    layout="wide"
)

# --- Interfaz Principal de la App ---
st.title("🌱 Preprocesamiento de Datos de Huertas Urbanas")
st.markdown("""
Esta aplicación te permite cargar un archivo CSV con información sobre metodologías de huertas urbanas, 
limpiarlo, enriquecerlo con resúmenes de IA a través de Gemini y, finalmente, guardarlo en una base de 
datos de Firestore.
""")

# --- Manejo de Estado ---
if 'firebase_db' not in st.session_state:
    st.session_state.firebase_db = None
if 'data_cleaned' not in st.session_state:
    st.session_state.data_cleaned = None
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False

# --- Verificación de Secretos (API Keys) ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("API Key de Gemini cargada desde secretos.", icon="✅")
except (KeyError, FileNotFoundError):
    st.sidebar.warning("API Key de Gemini no encontrada en los secretos.")
    GEMINI_API_KEY = st.sidebar.text_input(
        "Ingresa tu API Key de Gemini", 
        type="password", 
        help="Es necesario para procesar los textos con IA."
    )

# --- Barra Lateral para Entradas ---
with st.sidebar:
    st.header("1. Cargar Datos")
    uploaded_file = st.file_uploader("Selecciona tu archivo CSV", type=["csv"])

    st.header("2. Ejecutar Proceso")
    is_disabled = not uploaded_file or not GEMINI_API_KEY
    process_button = st.button("✨ Iniciar Preprocesamiento", use_container_width=True, disabled=is_disabled)

# --- Área de Contenido Principal ---
if process_button:
    st.session_state.processing_done = False 
    with st.spinner("Inicializando Firebase..."):
        st.session_state.firebase_db = inicializar_firebase()
    
    if st.session_state.firebase_db is None:
        st.error("🔴 No se pudo conectar a Firebase. Revisa las credenciales en los secretos de Streamlit.")
    else:
        st.success("🟢 Conexión con Firebase exitosa.")

        with st.spinner("Cargando y limpiando el archivo CSV..."):
            st.session_state.data_cleaned = cargar_y_limpiar_csv(uploaded_file)
        
        # --- CORRECCIÓN ---
        # Se ha corregido el error de sintaxis "is not in None" a "is not None".
        if st.session_state.data_cleaned is not None:
            st.subheader("📊 Datos Limpios")
            st.dataframe(st.session_state.data_cleaned.head())
            
            if 'Descripción' not in st.session_state.data_cleaned.columns:
                st.warning("⚠️ La columna 'Descripción' no se encontró. Se guardarán los datos sin enriquecer.")
                with st.spinner("Guardando datos en Firestore..."):
                    count = guardar_en_firestore(st.session_state.firebase_db, "metodologias_huertas", st.session_state.data_cleaned)
                    st.success(f"¡Proceso completado! Se guardaron {count} registros en Firestore.")
                    st.session_state.processing_done = True
            else:
                st.subheader("🧠 Enriquecimiento con IA (Gemini)")
                progress_bar = st.progress(0, text="Procesando filas con Gemini...")
                total_rows = len(st.session_state.data_cleaned)
                summaries = []

                for index, row in st.session_state.data_cleaned.iterrows():
                    summary_text = procesar_con_gemini(GEMINI_API_KEY, row['Descripción'])
                    summaries.append(summary_text)
                    progress_bar.progress((index + 1) / total_rows, text=f"Fila {index + 1}/{total_rows}")

                st.session_state.data_cleaned['Resumen_IA'] = summaries
                st.success("¡Textos procesados con Gemini!")
                st.dataframe(st.session_state.data_cleaned.head())
                
                with st.spinner("Guardando datos enriquecidos en Firestore..."):
                    count = guardar_en_firestore(st.session_state.firebase_db, "metodologias_huertas_enriquecidas", st.session_state.data_cleaned)
                    st.success(f"¡Proceso completado! Se guardaron {count} registros enriquecidos en Firestore.")
                    st.session_state.processing_done = True
        else:
            st.error("🔴 El archivo CSV no pudo ser procesado. Revisa que el formato sea correcto.")

if st.session_state.processing_done:
    st.balloons()
