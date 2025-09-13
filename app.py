import streamlit as st
import pandas as pd
from preprocesamiento import (
    cargar_y_limpiar_csv, 
    inicializar_firebase, 
    procesar_con_gemini, 
    guardar_en_firestore
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Huertas Urbanas | Preprocesamiento",
    page_icon="🌱",
    layout="wide"
)

# --- Main App UI ---
st.title("🌱 Preprocesamiento de Datos de Huertas Urbanas")
st.markdown("""
Esta aplicación te permite cargar un archivo CSV con información sobre metodologías de huertas urbanas, 
limpiarlo, enriquecerlo con resúmenes de IA a través de Gemini y, finalmente, guardarlo en una base de 
datos de Firestore.
""")

# --- State Management ---
# Initialize session state variables
if 'firebase_db' not in st.session_state:
    st.session_state.firebase_db = None
if 'data_cleaned' not in st.session_state:
    st.session_state.data_cleaned = None
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False


# --- Sidebar for Inputs ---
with st.sidebar:
    st.header("1. Configuración")
    
    # Gemini API Key
    gemini_api_key = st.text_input("Ingresa tu API Key de Gemini", type="password", help="Tu clave es necesaria para procesar los textos con IA.")
    
    # File Uploader
    st.header("2. Cargar Datos")
    uploaded_file = st.file_uploader("Selecciona tu archivo CSV", type=["csv"])

    # Process Button
    st.header("3. Ejecutar Proceso")
    process_button = st.button("✨ Iniciar Preprocesamiento", use_container_width=True, disabled=(not uploaded_file or not gemini_api_key))


# --- Main Content Area ---
if process_button:
    st.session_state.processing_done = False # Reset state on new process
    with st.spinner("Inicializando Firebase..."):
        st.session_state.firebase_db = inicializar_firebase()
    
    if st.session_state.firebase_db is None:
        st.error("No se pudo conectar a Firebase. Revisa las credenciales y la configuración.")
    else:
        st.success("Conexión con Firebase exitosa.")

        with st.spinner("Cargando y limpiando el archivo CSV..."):
            st.session_state.data_cleaned = cargar_y_limpiar_csv(uploaded_file)
        
        if st.session_state.data_cleaned is not None:
            st.subheader("Datos Limpios")
            st.dataframe(st.session_state.data_cleaned)
            
            # Check for expected column for Gemini processing
            if 'Descripción' not in st.session_state.data_cleaned.columns:
                st.warning("La columna 'Descripción' no se encontró en el CSV. Se omitirá el paso de enriquecimiento con Gemini.")
                # Save directly to Firestore without Gemini processing
                with st.spinner("Guardando datos en Firestore..."):
                    count = guardar_en_firestore(st.session_state.firebase_db, "metodologias_huertas", st.session_state.data_cleaned)
                    st.success(f"¡Proceso completado! Se guardaron {count} registros en Firestore.")
                    st.session_state.processing_done = True
            else:
                # Process with Gemini
                st.subheader("Enriquecimiento con IA (Gemini)")
                progress_bar = st.progress(0, text="Procesando filas con Gemini...")
                total_rows = len(st.session_state.data_cleaned)
                summaries = []

                for index, row in st.session_state.data_cleaned.iterrows():
                    summary_text = procesar_con_gemini(gemini_api_key, row['Descripción'])
                    summaries.append(summary_text)
                    progress_bar.progress((index + 1) / total_rows, text=f"Procesando fila {index + 1}/{total_rows}")

                st.session_state.data_cleaned['Resumen_IA'] = summaries
                st.success("¡Textos procesados con Gemini!")
                st.dataframe(st.session_state.data_cleaned)
                
                # Save to Firestore
                with st.spinner("Guardando datos enriquecidos en Firestore..."):
                    count = guardar_en_firestore(st.session_state.firebase_db, "metodologias_huertas_enriquecidas", st.session_state.data_cleaned)
                    st.success(f"¡Proceso completado! Se guardaron {count} registros enriquecidos en Firestore.")
                    st.session_state.processing_done = True
        else:
            st.error("El archivo CSV no pudo ser procesado. Revisa que el formato sea correcto.")

# Display a final message and balloons if the process completed successfully
if st.session_state.processing_done:
    st.balloons()

st.info("La aplicación está lista. Carga tu archivo y tu API key en la barra lateral para comenzar.")
