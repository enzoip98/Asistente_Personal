SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SEARCH_COLUMN = "phone"
formula_presupuesto  = '=SUMAR.SI.CONJUNTO(Gastos!H:H;Gastos!D:D;">" & FECHA(AÑO(HOY());MES(HOY());1);Gastos!D:D;"<=" & FECHA(AÑO(HOY());MES(HOY())+1;1);Gastos!B:B;INDICE(A:A;FILA()))'
formula_diferencia = '=INDICE(B:B;FILA())-INDICE(C:C;FILA())'

mensaje_bienvenida_usuario = """
Bienvenido al Asistente Financiero. Para continuar con tu registro necesitaré la siguiente información en un solo mensaje:
correo electrónico, categorías de gasto, moneda principal y medio de pago.
Ejemplo:
"""
mensaje_ejemplo_usuario = """
correo electrónico: usuario@gmail.com
categorías de gasto: Servicios, Pareja, Hogar, Comida, Movilidad, Gustos
moneda principal: PEN
medio de pago:Tarjeta de Crédito, Yape, Efectivo
"""

mensaje_confirmacion_usuario = """
Gracias por la información proporcionada.Te enviaré el link de la hoja de cálculo en la que tienes que completar tu información de presupuesto. """

mensaje_pago_usuario = """
Ahora para activar tu usuario debes realizar el pago de 20 soles a este QR de Yape.
Una vez lo realices se realizará la activación de tu usuario."""

class user_info:
    def __init__(self,information_row):
        self.mail = information_row[1]
        self.status = information_row[2]
        self.moneda = information_row[3]
        self.medio_pago = information_row[4]
        self.categories = information_row[5]
        self.url_sheet = information_row[6]
        self.created_at = information_row[7]

