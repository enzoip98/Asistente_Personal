import requests
import os
import json
import tempfile
import pickle
import base64
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI
from twilio.rest import Client
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()
make_webook_url = os.getenv("WEBHOOK_MAKE_URL")
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
DESTINATION_NUMBER = os.environ.get('DESTINATION_NUMBER')

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
TOKEN_PATH = os.getenv('TOKEN_PICKLE', 'token.pickle')
CLIENT_SECRET_PATH = os.getenv('CLIENT_SECRET', 'credentials.json')

def get_credentials():
    if os.getenv('TOKEN_PICKLE_B64') and not os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'wb') as f:
            f.write(base64.b64decode(os.getenv('TOKEN_PICKLE_B64')))
        print("Archivo creado")
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
        print("Credenciales cargadas")
    return creds

def response(mensaje: str, DESTINATION_NUMBER: str):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        sent = client.messages.create(
            body=mensaje,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=DESTINATION_NUMBER
        )
        return jsonify({"status": "Mensaje enviado", "sid": sent.sid}), 200
    except Exception as e:
        import traceback
        print("Error en /response:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

creds = get_credentials()
sheets_service = build('sheets', 'v4', credentials=creds)
SPREADSHEET_ID = os.getenv('USUARIOS_ID')
SHEET_NAME = os.getenv('SHEET_NAME')
SEARCH_COLUMN = "phone"
RANGE_ALL = f"{SHEET_NAME}!A:G"

mensaje_informacion_usuario = """
    Bienvenido al Asistente Financiero. Para continuar necesitaré la siguiente información:
    correo electrónico: (correo de gmail)
    categorías de gasto: Ejemplo (Servicios, Pareja, Hogar, Comida, Movilidad, Gustos)
"""



@app.route('/')
def home():
    return "¡La app está corriendo correctamente!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.form
    numero: str = data.get("From", "").split("+")[-1]
    mensaje: str = data.get("Body", "")
    #media_url = data.get("MediaUrl0")
    #media_type = data.get("MediaContentType0", "")
    try: 
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_ALL
        ).execute()
        rows = result.get('values', [])
        if not rows:
            return jsonify({'error': 'La hoja está vacía'}), 404
        header: list[str] = rows[0]
        if SEARCH_COLUMN not in header:
            return jsonify({'error': f'Columna "{SEARCH_COLUMN}" no encontrada'}), 400
        idx = header.index(SEARCH_COLUMN)
        for row in rows[1:]:
            if row[idx] == numero:
                mail: str = row[1]
                status: str = row[2]
                categories: str = row[3]
                url_sheet: str = row[4]
                if status == "inactive":
                    print(numero," inactivo")
                    #codigo para llamar a chat gpt preguntando por el la información del usuario usando el mensaje
                    return jsonify({'status': 'ok', 'message': 'Usuario encontrado, se solicita registro.'}), 200
                elif status == "active":
                    print(numero," activo")
                    #codigo para insertar regitro en la hoja de calculo
                    return jsonify({'status': 'ok', 'message': 'Se registra informacion del usuario.'}), 200
        print(numero," no encontrado")
        insertion_row_number = len(rows) + 1
        insertion_row = {'values':[[numero,'','inactive','','',datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]}
        return response(mensaje_informacion_usuario, numero)
    except:
        return jsonify({'error': 'Error en el proceso, contactar con administrador'}), 500

@app.route('/response',methods=['POST'])
def response_twilio(DESTINATION_NUMBER):
    
    data = request.get_json()
    message = data.get('mensaje') or data.get('message')  # soporte para ambos keys

    if not message:
        return jsonify({"error": "Falta el campo 'mensaje' en el cuerpo del request"}), 400
    try:
        response(message, DESTINATION_NUMBER)
    except Exception as e:
        import traceback
        print("Error en /response:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))