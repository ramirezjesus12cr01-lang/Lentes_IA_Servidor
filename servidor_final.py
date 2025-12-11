import os
import io
import base64
import tempfile
from flask import Flask, request, jsonify
from PIL import Image
from gtts import gTTS
from google import genai
from google.genai.errors import APIError

app = Flask(__name__)

# ==========================================
# 🛑 CORRECCIÓN DE SEGURIDAD Y ENTORNO
# La clave API se lee de la variable secreta GEMINI_API_KEY en Render.
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    # Esto es vital para saber si la configuración de Render falló.
    print("ERROR FATAL: La variable GEMINI_API_KEY no se ha configurado en Render.")
    exit()

# Inicializa el cliente de Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

# Ruta para almacenar archivos temporales de audio/imagen en el servidor
TEMP_DIR = tempfile.gettempdir()
AUDIO_FILE_PATH = os.path.join(TEMP_DIR, "respuesta_audio.mp3")

# ==========================================
# 1. RUTA PARA ANALIZAR IMAGEN (POST)
# ==========================================
@app.route('/analizar_imagen', methods=['POST'])
def analizar_imagen():
    try:
        data = request.json
        if not data or 'imagen_base64' not in data:
            return jsonify({"status": "error", "message": "Falta imagen_base64 en la solicitud"}), 400

        imagen_base64 = data['imagen_base64']
        imagen_data = base64.b64decode(imagen_base64)
        
        # Abrir la imagen desde bytes
        image = Image.open(io.BytesIO(imagen_data))
        
        # --- Prompt de IA para el contexto de los lentes ---
        prompt_texto = (
            "Eres un asistente de visión para una persona con discapacidad visual. "
            "Describe lo que ves en detalle, pero de manera concisa (máximo 2 oraciones). "
            "Identifica objetos importantes, personas, texto o peligros. "
            "Responde en español. Ejemplo: 'Veo un semáforo en verde y tres personas esperando en la esquina.' "
        )

        # 2. Llamada a la API de Gemini
        print("Llamando a la API de Gemini...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt_texto, image]
        )
        
        texto_respuesta = response.text.strip()
        print(f"Respuesta de Gemini: {texto_respuesta}")

        # 3. Generar Audio (gTTS)
        tts = gTTS(text=texto_respuesta, lang='es')
        
        # Guarda el archivo en la ruta temporal de Render
        tts.save(AUDIO_FILE_PATH)
        
        # Enviar respuesta de éxito (El cliente ahora debe pedir el audio)
        return jsonify({
            "status": "success", 
            "message": "AUDIO_LISTO",
            "texto": texto_respuesta
        }), 200

    except APIError as e:
        print(f"Error de la API de Google Gemini: {e}")
        return jsonify({"status": "error", "message": "Error en la API de Gemini."}), 500
    except Exception as e:
        print(f"Error general en analizar_imagen: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 2. RUTA PARA OBTENER AUDIO (GET)
# ==========================================
@app.route('/obtener_audio', methods=['GET'])
def obtener_audio():
    try:
        if not os.path.exists(AUDIO_FILE_PATH):
            return jsonify({"status": "error", "message": "Archivo de audio no encontrado."}), 404

        # 🛑 Usamos send_file con cabeceras explícitas (mimetype)
        response = send_file(
            AUDIO_FILE_PATH,
            mimetype='audio/mpeg',  # 'audio/mpeg' es el estándar para MP3
            as_attachment=False
        )

        # 🛑 Limpiar el archivo DESPUÉS de enviarlo
        # Importante: Esto lo limpia después de que Render termina la transferencia.
        @response.call_on_close
        def cleanup():
            try:
                os.remove(AUDIO_FILE_PATH)
                print(f"Archivo temporal eliminado: {AUDIO_FILE_PATH}")
            except Exception as e:
                print(f"Error al intentar eliminar el archivo: {e}")
        
        return response

    except Exception as e:
        print(f"Error en obtener_audio: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 3. INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    # Render usa la variable de entorno PORT para decirnos qué puerto usar.
    port = int(os.environ.get('PORT', 5000))
    # El host '0.0.0.0' es necesario para que sea accesible externamente.

    app.run(host='0.0.0.0', port=port)
