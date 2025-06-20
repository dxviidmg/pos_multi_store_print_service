import win32print
import win32ui
from utils import get_store_printer_data

# Formato general de la fuente
FORMAT = {"name": "Arial", "height": 30, "weight": 700}
Y_INIT = 10
SPACING = 40

printer_name = win32print.GetDefaultPrinter()

def start_printing(titulo="Ticket Python", data={}):
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc(titulo)
    hDC.StartPage()
    font = win32ui.CreateFont(FORMAT)
    hDC.SelectObject(font)

    store_printer = get_store_printer_data(data)
    print(store_printer)

    y = Y_INIT
    hDC.TextOut(0, Y_INIT, store_printer['store'['tenant_name']])
    y += Y_INIT

    hDC.TextOut(0, Y_INIT, store_printer['store'['address']])
    y += Y_INIT

    hDC.TextOut(0, Y_INIT, store_printer['store'['phone_number']])
    y += Y_INIT
    return hDC


def end_printing(hDC):
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def print_lines(hDC, lineas, y_inicio=Y_INIT, spacing=SPACING):
    y = y_inicio
    for linea in lineas:
        hDC.TextOut(0, y, linea)
        y += spacing
    return hDC