from flask import Flask, request, jsonify
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime
import json
import tempfile
from twilio.rest import Client

load_dotenv()
make_webook_url = os.getenv("WEBHOOK_MAKE_URL")
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
DESTINATION_NUMBER = os.environ.get('DESTINATION_NUMBER')

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
        Actúa como un asistente financiero que me va a ayudar a registrar mis ingresos y egresos de manera precisa y estructurada.
        Analiza el siguiente mensaje de WhatsApp y extrae la información que te solicito a continuación en un JSON.

        - descripcion
        - monto
        - categoria (Debe estar en una de las siguientes:Servicios (Pago de internet, Pago de Luz, Pago de telefono, Pago de Servicios de nube), Pareja(almuerzos, salidas y citas con mi pareja), Hogar(compras en supermercados de comida y de cosas de limpieza), Entretenimiento(fiestas y o salidas sin pareja), Movilidad (gasolina y taxis), Paz Mental(regalos a mi mismo o a mi familia))
        - medio (Signature o Yape, asume Signature si no lo menciono)
        - moneda (PEN o USD, asume PEN si no lo mencionos)
        - tipo (Gasto o Ingreso)

        El mensaje es: "{mensaje}"

        Tu respuesta debe ser un json que va a pasar por la librería de json de python, sin texto adicional. No inventes información.
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
@app.route('/response',methods=['POST'])
def response():
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    data = request.get_json()
    message = data.get('mensaje') or data.get('message')  # soporte para ambos keys

    if not message:
        return jsonify({"error": "Falta el campo 'mensaje' en el cuerpo del request"}), 400

    try:
        sent = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=DESTINATION_NUMBER
        )
        return jsonify({"status": "Mensaje enviado", "sid": sent.sid}), 200
    except Exception as e:
        import traceback
        print("❌ Error en /response:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)