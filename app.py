from flask import Flask, request, jsonify
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime
import json
import tempfile

load_dotenv()
make_webook_url = os.getenv("WEBHOOK_MAKE_URL")

app = Flask(__name__)


@app.route('/')
def home():
    return "¡La app está corriendo correctamente!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form
    mensaje = data.get("Body", "")
    media_url = data.get("MediaUrl0")
    media_type = data.get("MediaContentType0", "")
    
    try:
        client = OpenAI()

        if media_url and "audio" in media_type:
            audio_response = requests.get(media_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_audio:
                    tmp_audio.write(audio_response.content)
                    tmp_audio_path = tmp_audio.name
            
            with open(tmp_audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    mensaje_texto = transcript.strip()

        if mensaje_texto:
            mensaje = mensaje_texto

        prompt = f"""
        Extrae los siguientes campos desde este mensaje de WhatsApp y estructura la respuesta en JSON:

        - descripcion
        - monto
        - categoria
        - medio (Signature o Yape)
        - moneda (PEN o USD)
        - tipo (Gasto o Ingreso)

        Ejemplo de mensaje: "{mensaje}"

        Respondeme solo con el json, sin texto adicional. Si no encuentras un campo, infierelo.
        """

        response = client.responses.create(
            model = "gpt-4.1",
            input = prompt
        )
        json_data =  response.output_text
        datos = json.loads(json_data)
        datos["fecha"] = datetime.now().strftime("%Y-%m-%d")
        if make_webook_url:
            requests.post(make_webook_url,json = datos)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)