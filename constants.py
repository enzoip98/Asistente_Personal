SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SEARCH_COLUMN = "phone"
formula_presupuesto  = '=SUMAR.SI.CONJUNTO(Gastos!H:H;Gastos!D:D;">" & FECHA(AÑO(HOY());MES(HOY());1);Gastos!D:D;"<=" & FECHA(AÑO(HOY());MES(HOY())+1;1);Gastos!B:B;INDICE(A:A;FILA()))'
formula_diferencia = '=INDICE(B:B;FILA())-INDICE(C:C;FILA())'

mensaje_bienvenida_usuario = """
Bienvenide al Asistente Financiero 🙌. Para continuar con tu registro necesitaré la siguiente información
Correo eletrónico con acceso a google (vamos crearte una hoja de google sheets)
Todas las categorías de gasto que vayas a utilizar para registrar tus gastos
Moneda principal para tus gastos
Medios de pago que utilizarás para registrar tus gatos
Aquí te envío un ejemplo:
"""
mensaje_ejemplo_usuario = """
correo electrónico: usuario@gmail.com
categorías de gasto: Servicios, Pareja, Hogar, Comida, Movilidad, Gustos
moneda principal: PEN
medio de pago:Tarjeta de Crédito, Yape, Efectivo
"""
mensaje_de_recibido = """
Listo, recibí el mensaje, dejame pienso un momento. 🤓
"""
mensaje_confirmacion_usuario = """
Te envio el link de la hoja de cálculo que creé para ti, recuerda que igual debes completar tu información de presupuestos en la pestaña de presupuestos en la hoja, estará resaltado en amarillo. """

mensaje_pago_usuario = """
Ahora, para activar tu usuario deberás realizar un pago de 20 soles al 922478866 (Yape) o si están en el extranjero puedes usar global66 o paypal por un total de 8 dolares 💰💰"""

class user_info:
    def __init__(self,information_row):
        self.mail = information_row[1]
        self.status = information_row[2]
        self.moneda = information_row[3]
        self.medio_pago = information_row[4]
        self.categories = information_row[5]
        self.url_sheet = information_row[6]
        self.created_at = information_row[7]

