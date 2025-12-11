from flask import Flask, request, send_file
import requests
from gtts import gTTS
import os

# 🛑 ¡TU CLAVE DE GEMINI!
GEMINI_API_KEY = "AIzaSyDTrF8GOKI_vL7GLB3wVQ5Cmcc_vepvJVU" 

app = Flask(__name__)

# Variable global para guardar el nombre del último audio generado
AUDIO_FILE = "alerta.mp3"

@app.route('/analizar_imagen', methods=['POST'])
def analizar_imagen():
    try:
        print("--- Recibiendo imagen... ---")
        base64_data = request.data.decode('utf-8')
        
        # Limpieza de base64
        if base64_data.startswith('data='):
            base64_image = base64_data[5:]
        else:
            base64_image = base64_data

        prompt = "Describe muy brevemente (máximo 4 palabras) el objeto principal o peligro frente a mi. Ej: 'Escaleras abajo', 'Persona enfrente'."
        
        # Payload para Gemini 2.5
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}],
            "generationConfig": {"maxOutputTokens": 2048}
        }

        headers = {'Content-Type': 'application/json'}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

        # Llamada a Gemini
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        gemini_response = response.json()
        
        # Obtener texto
        if gemini_response.get('candidates'):
            texto_ia = gemini_response['candidates'][0]['content']['parts'][0]['text']
            # Limpiar asteriscos o formato markdown que Gemini a veces pone
            texto_ia = texto_ia.replace("*", "")
            print(f"👁️ IA vio: {texto_ia}")
        else:
            texto_ia = "Error en visión"

        # 🛑 GENERAR AUDIO (TTS)
        # Convertimos el texto a español y lo guardamos
        tts = gTTS(text=texto_ia, lang='es')
        tts.save(AUDIO_FILE)
        print("✅ Audio generado y guardado.")

        # Le respondemos al ESP32 solo una señal de que el audio está listo
        return "AUDIO_LISTO", 200

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return "ERROR", 500

# 🛑 NUEVA RUTA: El ESP32 vendrá aquí a buscar el MP3
@app.route('/obtener_audio', methods=['GET'])
def obtener_audio():
    try:
        return send_file(AUDIO_FILE, mimetype="audio/mp3")
    except Exception as e:
        return str(e), 404

if __name__ == '__main__':
    # Escucha en todas las interfaces
    app.run(host='0.0.0.0', port=5000)