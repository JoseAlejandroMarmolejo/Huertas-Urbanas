import pandas as pd
import os
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
import time

# --- Firebase Initialization ---

def inicializar_firebase():
    """
    Initializes the Firebase Admin SDK.
    Checks if the app is already initialized.
    It's recommended to use environment variables for production.
    """
    if not firebase_admin._apps:
        # NOTE: For use in GitHub, it's safer to load credentials from an environment variable
        # or a secure location, rather than having the JSON file in the repository.
        cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'path/to/your/serviceAccountKey.json')
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase inicializado correctamente.")
            return firestore.client()
        except Exception as e:
            print(f"Error al inicializar Firebase: {e}")
            print("Asegúrate de que el archivo 'serviceAccountKey.json' existe o la variable de entorno está configurada.")
            return None
    else:
        print("Firebase ya estaba inicializado.")
        return firestore.client()

# --- Data Loading and Cleaning ---

def cargar_y_limpiar_csv(uploaded_file):
    """
    Loads a CSV file from a Streamlit uploaded file object and performs basic cleaning.
    
    Args:
        uploaded_file: The file object from Streamlit's file_uploader.

    Returns:
        A cleaned pandas DataFrame or None if an error occurs.
    """
    if uploaded_file is None:
        return None
    try:
        df = pd.read_csv(uploaded_file)
        
        # Basic cleaning steps
        # 1. Handle missing values (dropping rows with any missing value)
        df.dropna(inplace=True)
        
        # 2. Remove duplicate rows
        df.drop_duplicates(inplace=True)

        # 3. Trim whitespace from all string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()
            
        print("CSV cargado y limpiado exitosamente.")
        return df

    except Exception as e:
        print(f"Error al cargar o limpiar el CSV: {e}")
        return None

# --- Gemini API Processing ---

def procesar_con_gemini(api_key, texto, retries=3, delay=5):
    """
    Processes text using the Gemini API to generate a summary.
    Includes retry logic with exponential backoff for handling API rate limits.

    Args:
        api_key (str): Your Google Gemini API key.
        texto (str): The text to be processed.
        retries (int): Number of retry attempts.
        delay (int): Initial delay in seconds for retries.


    Returns:
        The generated summary as a string, or an error message.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"Actúa como un experto en agricultura urbana. Resume la siguiente descripción de una metodología de investigación en 3 puntos clave para que sea fácil de entender:\n\n---\n{texto}\n---"
        
        for attempt in range(retries):
            try:
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "429" in str(e): # Specific check for rate limit error
                    print(f"Rate limit hit. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2 # Exponential backoff
                else:
                    raise e # Re-raise other exceptions
        return "Error: Se superaron los reintentos por límite de tasa de la API."

    except Exception as e:
        print(f"Error al conectar con la API de Gemini: {e}")
        return f"Error al procesar con Gemini: {e}"


# --- Firestore Data Saving ---

def guardar_en_firestore(db, collection_name, dataframe):
    """
    Saves a pandas DataFrame to a specified Firestore collection.
    Each row of the DataFrame becomes a document in the collection.

    Args:
        db: The Firestore client instance.
        collection_name (str): The name of the collection to save data to.
        dataframe (pd.DataFrame): The DataFrame to be saved.
    
    Returns:
        The number of documents successfully added.
    """
    if db is None or dataframe is None:
        print("Error: Base de datos no inicializada o DataFrame vacío.")
        return 0
        
    batch = db.batch()
    collection_ref = db.collection(collection_name)
    count = 0
    
    for index, row in dataframe.iterrows():
        # Convert row to dictionary, ensuring data types are Firestore-compatible
        doc_data = row.to_dict()
        doc_ref = collection_ref.document() # Create a new document with a random ID
        batch.set(doc_ref, doc_data)
        count += 1
        
        # Firestore batch has a limit of 500 operations. Commit every 499.
        if count % 499 == 0:
            batch.commit()
            batch = db.batch() # Start a new batch
            
    # Commit any remaining operations in the last batch
    if count % 499 != 0:
        batch.commit()
        
    print(f"Se guardaron {count} documentos en la colección '{collection_name}'.")
    return count
