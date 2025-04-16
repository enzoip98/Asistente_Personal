from flask import Flask, request, jsonify
import requests
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()
make_webook_url = os.getenv("WEBHOOK_MAKE_URL")

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form
    mensaje = data.get("Body", "")
    
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
    try:
        client = OpenAI()
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