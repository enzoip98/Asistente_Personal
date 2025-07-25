import base64
import pickle
from twilio.rest import Client
from flask import jsonify
from googleapiclient.discovery import build
from datetime import datetime

def get_credentials(b64_pickle):
    if b64_pickle:
        try:
            token_bytes = base64.b64decode(b64_pickle)
            creds = pickle.loads(token_bytes)
        except Exception:
            creds = None
    return creds

def whatsapp_reponse(mensaje: str, DESTINATION_NUMBER: str, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER):
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

def insert_row(target_range, insertion_row, id, sheets_service):
    sheets_service.spreadsheets().values().update(
        spreadsheetId=id,
        range=target_range,
        valueInputOption="USER_ENTERED",
        body=insertion_row
    ).execute()

def copy_sheet(file_id: str, new_title: str, b64_pickle):
    drive = build('drive', 'v3', credentials=get_credentials(b64_pickle))
    body = {'name': "gastos_" + new_title}
    copied = drive.files().copy(fileId=file_id, body=body).execute()
    return copied['id']

def share_sheet(file_id: str, new_owner_email: str,b64_pickle):
    drive = build('drive', 'v3', credentials=get_credentials(b64_pickle))

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

def create_user(rows, numero,SHEET_NAME, SPREADSHEET_ID,sheets_service):
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
    insert_row(target_range, insertion_row,SPREADSHEET_ID, sheets_service)