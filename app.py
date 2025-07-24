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


# Load of environment variables
load_dotenv()
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
DESTINATION_NUMBER = os.environ.get('DESTINATION_NUMBER')
b64_pickle = os.getenv('TOKEN_PICKLE_B64')
register_promt_id = os.getenv('register_promt_id')
spent_prompt_id = os.getenv('spent_prompt_id')
app = Flask(__name__)
SPREADSHEET_ID: str = os.getenv('USUARIOS_ID','none')
PLANTILLA_ID: str  = os.getenv('PLANTILLA_ID','none')
SHEET_NAME: str = os.getenv('SHEET_NAME','none')
RANGE_ALL = f"{SHEET_NAME}!A:I"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SEARCH_COLUMN = "phone"

mensaje_informacion_usuario = """
    Bienvenido al Asistente Financiero. Para continuar necesitaré la siguiente información:
    correo electrónico: (correo de gmail)
    categorías de gasto: Ejemplo (Servicios, Pareja, Hogar, Comida, Movilidad, Gustos)
    moneda principal: (Ejemplo: EUR, COP, PEN)
    medio de pago: (Ejemplo: Tarjeta de Crédito, Yape, etc.)
"""

mensaje_confirmacion_usuario = """
    Gracias por la información proporcionada. He creado una hoja de cálculo para ti. """

def get_credentials():
    if b64_pickle:
        try:
            token_bytes = base64.b64decode(b64_pickle)
            creds = pickle.loads(token_bytes)
        except Exception:
            creds = None
    return creds

def response(mensaje: str, DESTINATION_NUMBER: str):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        sent = client.messages.create(
            body=mensaje,
            from_=TWILIO_WHATSAPP_NUMBER,
            to="whatsapp:"+DESTINATION_NUMBER
        )
        return jsonify({"status": "Mensaje enviado", "sid": sent.sid}), 200
    except Exception as e:
        import traceback
        return jsonify({"error": str(e)}), 500


def insert_row(target_range, insertion_row, id):
    sheets_service.spreadsheets().values().update(
        spreadsheetId=id,
        range=target_range,
        valueInputOption="USER_ENTERED",
        body=insertion_row
    ).execute()

def copy_sheet(file_id: str, new_title: str):
    drive = build('drive', 'v3', credentials=get_credentials())
    body = {'name': "gastos_" + new_title}
    copied = drive.files().copy(fileId=file_id, body=body).execute()
    return copied['id']

def share_sheet(file_id: str, new_owner_email: str):
    drive = build('drive', 'v3', credentials=get_credentials())

    try:
        # 1. Compartir como editor (opcional, pero a veces necesario)
        drive.permissions().create(
            fileId=file_id,
            body={
                'type': 'user',
                'role': 'writer',
                'emailAddress': new_owner_email
            },
            fields='id'
        ).execute()
    except:
        pass

creds = get_credentials()
sheets_service = build('sheets', 'v4', credentials=creds)

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
        header: list[str] = rows[0]
        idx = header.index(SEARCH_COLUMN)
        for row in rows[1:]:
            if row[idx] == numero:
                mail: str = row[1]
                status: str = row[2]
                moneda: str = row[3]
                medio_pago: str = row[4]
                categories: str = row[5]
                url_sheet: str = row[6]
                created_at : str = row[7]
                if status == "inactive":
                    try:
                        client = OpenAI()
                        prompt_response = client.responses.create(
                        prompt={
                            "id": register_promt_id,
                            "version": "5",
                            "variables": {
                            "mensaje": f"{mensaje}"
                            }
                        }
                        )
                        json_data = prompt_response.output_text
                        data = json.loads(json_data)

                        new_sheet_id = copy_sheet(PLANTILLA_ID, data['correo_electronico'])
                        share_sheet(new_sheet_id, data['correo_electronico'])

                        for i in range(len(data['categorias_gasto'])):
                            target_range = "Presupuesto!A"+str(i+3)+":D"
                            insertion_row = {'values':[[data['categorias_gasto'][i],'','=SUMAR.SI.CONJUNTO(Gastos!H:H;Gastos!D:D;">" & FECHA(AÑO(HOY()-9);MES(HOY()-9);9);Gastos!D:D;"<=" & FECHA(AÑO(HOY()-9);MES(HOY()-9)+1;9);Gastos!B:B;INDICE(A:A;FILA()))','=INDICE(B:B;FILA())-INDICE(C:C;FILA())']]}
                            insert_row(target_range, insertion_row,new_sheet_id)
                        

                        for i in range(len(data['medio_de_pago'])):
                            target_range = "Datos_Usuario!A"+str(i+2)
                            insertion_row = {'values':[[data['medio_de_pago'][i]]]}
                            insert_row(target_range, insertion_row, new_sheet_id)
                        
                        insert_row( "Datos_Usuario!B2", {'values':[[data['moneda_principal']]]}, new_sheet_id)

                        insertion_row_number = rows.index(row) + 1
                        target_range = f"{SHEET_NAME}!A{insertion_row_number}"
                        insertion_row = {
                            'values':[
                                [numero,
                                data['correo_electronico'],
                                'pendiente_de_pago',
                                data['moneda_principal'],
                                ','.join(data['medio_de_pago']),
                                ','.join(data['categorias_gasto']),
                                new_sheet_id,
                                str(created_at)]]}            
                        insert_row(target_range, insertion_row, SPREADSHEET_ID)
                        response(mensaje_confirmacion_usuario + f"https://docs.google.com/spreadsheets/d/{new_sheet_id}/edit", numero)
                        return jsonify({'status': 'ok', 'message': 'Se añade informacion del usuario.'}), 200
                    except:
                        return jsonify({'error': 'Error al añadir informacion del usuario'}), 500
                elif status == "active":
                    result = sheets_service.spreadsheets().values().get(
                        spreadsheetId=url_sheet,
                        range="Registro!A:G"
                    ).execute()
                    rows = result.get('values', [])
                    try:
                        client = OpenAI()
                        prompt_response = client.responses.create(
                            prompt={
                                "id": spent_prompt_id,
                                "version": "3",
                                "variables": {
                                "categorias": f"{categories}",
                                "metodos": f"{medio_pago}",
                                "moneda": f"{moneda}",
                                "mensaje": f"{mensaje}"
                                }
                            }
                            )
                        json_data = prompt_response.output_text
                        data = json.loads(json_data)
                        insert_row("Registro!A"+str(len(rows)+1), {'values':[[
                            data['descripcion'],
                            data['categoria'],
                            data['monto'],
                            str(datetime.now().strftime('%d/%m/%Y')),
                            data['medio'],
                            data['moneda'],
                            data['tipo']
                            ]]}, url_sheet)
                        response(f"Se ha registrado el gasto: {data['descripcion']} de {data['monto']} {data['moneda']}", numero)
                        return jsonify({'status': 'ok', 'message': 'Se registra evento del usuario.'}), 200
                    except: 
                        return jsonify({'error': 'Error al registrar evento del usuario'}), 500
        insertion_row_number = len(rows) + 1
        insertion_row = {'values':[
            [numero,
            '',
            'inactive',
            '',
            '',
            '',
            '',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')]]}
        target_range = f"{SHEET_NAME}!A{insertion_row_number}"
        insert_row(target_range, insertion_row,SPREADSHEET_ID)
        response(mensaje_informacion_usuario, numero)
        return jsonify({'status': 'ok', 'message': 'Se solicita informacion del usuario.'}), 200
    except:
        return jsonify({'error': 'Error en el proceso, contactar con administrador'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))