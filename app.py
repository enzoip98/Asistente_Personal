from constants import mensaje_ejemplo_usuario
from constants import mensaje_bienvenida_usuario
import requests
import os
import json
import time
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from functions import *
from constants import *

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
RANGE_REGISTER = f"{SHEET_NAME}!A:I"

# Getting credentials to use the google suit
creds = get_credentials(b64_pickle)

# Creatting the sheets service
sheets_service = build('sheets', 'v4', credentials=creds)

@app.route('/')
def home():
    #Endpoint to be used by the uptime robot to get information about the service status
    return "¡La app está corriendo correctamente!"

@app.route('/webhook', methods=['POST'])
def webhook():
    ### Main process endpoint ###

    # getting the payload from twilio
    data = request.form
    numero: str = data.get("From", "").split("+")[-1]
    mensaje: str = data.get("Body", "")
    #media_url = data.get("MediaUrl0")
    #media_type = data.get("MediaContentType0", "")

    #Start of the process
    try:
        # Check of the  users sheets
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_REGISTER
        ).execute()
        rows = result.get('values', [])
        header: list[str] = rows[0]
        idx = header.index(SEARCH_COLUMN)
        # looking up for the whatsapp sender in the users database
        for row in rows[1:]:
            if row[idx] == numero:
                user_data = user_info(row)
                if user_data.status == "inactive":
                    # User is found but is inactive so is asked for information
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
                        
                        # Parsing the response from the AI
                        json_data = prompt_response.output_text
                        data = json.loads(json_data)
                        print(data)
                        for i in data:
                            if i == "null":
                                whatsapp_reponse(
                                    "Error en el formato de la respuesta, por favor intente de nuevo.",
                                    numero,
                                    TWILIO_ACCOUNT_SID,
                                    TWILIO_AUTH_TOKEN,
                                    TWILIO_WHATSAPP_NUMBER
                                )
                                return jsonify({'error': 'Error en el formato de la respuesta, por favor intente de nuevo.'}), 400
                        #creating and sharing the user sheet
                        new_sheet_id = copy_sheet(PLANTILLA_ID, data['correo_electronico'], b64_pickle)
                        print("sheet created with id: ", new_sheet_id)
                        share_sheet(new_sheet_id, data['correo_electronico'], b64_pickle)
                        print("sheet shared with: ", data['correo_electronico'])

                        # Inserting the user data into the new sheet
                        for i in range(len(data['categorias_gasto'])):
                            print("Adding category: ", data['categorias_gasto'][i])
                            target_range = "Presupuesto!A"+str(i+3)+":D"
                            insertion_row = {'values':[[data['categorias_gasto'][i],'',formula_presupuesto,formula_diferencia]]}
                            insert_row(target_range, insertion_row,new_sheet_id, sheets_service)
                        # Inserting the user data into the new sheet
                        for i in range(len(data['medio_de_pago'])):
                            print("Adding paymenth method: ", data['medio_de_pago'][i])
                            target_range = "Datos_Usuario!A"+str(i+2)
                            insertion_row = {'values':[[data['medio_de_pago'][i]]]}
                            insert_row(target_range, insertion_row, new_sheet_id, sheets_service)
                        # Inserting the user data into the new sheet
                        insert_row( "Datos_Usuario!B2", {'values':[[data['moneda_principal']]]}, new_sheet_id, sheets_service)
                        print("Adding currency")
                        
                        # Inserting the user data into the users database
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
                                str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]]}            
                        insert_row(target_range, insertion_row, SPREADSHEET_ID, sheets_service)
                        whatsapp_reponse(mensaje_confirmacion_usuario + f"https://docs.google.com/spreadsheets/d/{new_sheet_id}/edit", numero, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER)
                        whatsapp_reponse(mensaje_pago_usuario, numero, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER)
                        return jsonify({'status': 'ok', 'message': 'Se añade informacion del usuario.'}), 200
                    except:
                        return jsonify({'error': 'Error al añadir informacion del usuario'}), 500
                elif user_data.status == "active":
                    result = sheets_service.spreadsheets().values().get(
                        spreadsheetId=user_data.url_sheet,
                        range="Registro!A:G"
                    ).execute()
                    rows = result.get('values', [])
                    result_buget = sheets_service.spreadsheets().values().get(
                        spreadsheetId=user_data.url_sheet,
                        range="Presupuesto!A:d"
                    ).execute()
                    budget_rows = result_buget.get('values', [])
                    try:
                        client = OpenAI()
                        prompt_response = client.responses.create(
                            prompt={
                                "id": spent_prompt_id,
                                "version": "3",
                                "variables": {
                                "categorias": f"{user_data.categories}",
                                "metodos": f"{user_data.medio_pago}",
                                "moneda": f"{user_data.moneda}",
                                "mensaje": f"{mensaje}"
                                }
                            }
                            )
                        json_data = prompt_response.output_text
                        data = json.loads(json_data)
                        for i in data:
                            if i == "null":
                                whatsapp_reponse(
                                    "No entendí, puedes repetir pls.",
                                    numero,
                                    TWILIO_ACCOUNT_SID,
                                    TWILIO_AUTH_TOKEN,
                                    TWILIO_WHATSAPP_NUMBER
                                )
                                return jsonify({'error': 'Error en el formato de la respuesta, por favor intente de nuevo.'}), 400
                        insert_row("Registro!A"+str(len(rows)+1), {'values':[[
                            data['descripcion'],
                            data['categoria'],
                            data['monto'],
                            str(datetime.now().strftime('%d/%m/%Y')),
                            data['medio'],
                            data['moneda'],
                            data['tipo']
                            ]]},
                            user_data.url_sheet,
                            sheets_service)
                        
                        time.sleep(3)
                        for row in budget_rows[2:]:
                            if row[0] == data['categoria']:
                                buget = row[3]
                        if data['tipo'] == "Gasto":
                            whatsapp_reponse(
                                f"Se ha registrado el gasto, tu presupuesto restante para la categoria {data['categoria']} es de {buget} {user_data.moneda}.",
                                numero,
                                TWILIO_ACCOUNT_SID,
                                TWILIO_AUTH_TOKEN,
                                TWILIO_WHATSAPP_NUMBER)
                        elif data['tipo'] == "Ingreso":
                            whatsapp_reponse(
                                f"Se ha registrado el ingreso.",
                                numero,
                                TWILIO_ACCOUNT_SID,
                                TWILIO_AUTH_TOKEN,
                                TWILIO_WHATSAPP_NUMBER)
                        return jsonify({'status': 'ok', 'message': 'Se registra evento del usuario.'}), 200
                    except: 
                        return jsonify({'error': 'Error al registrar evento del usuario'}), 500
        
        # If the user is not found in  the database new user is created
        create_user(rows, numero, SHEET_NAME, SPREADSHEET_ID, sheets_service)
        # Sending the welcome message to the user
        whatsapp_reponse(
        mensaje_bienvenida_usuario,
        numero,
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN,
        TWILIO_WHATSAPP_NUMBER)
        time.sleep(3)
        whatsapp_reponse(
        mensaje_ejemplo_usuario,
        numero,
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN,
        TWILIO_WHATSAPP_NUMBER)
        return jsonify({'status': 'ok', 'message': 'Se solicita informacion del usuario.'}), 200
    except:
        return jsonify({'error': 'Error en el proceso, contactar con administrador'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))