# Formato general de la fuente
FORMAT = {"name": "Arial", "height": 30, "weight": 700}
Y_INIT = 10
SPACING = 40

from utils import get_store_printer_data

def start_printing(titulo="Ticket Python", data={}):

    store_printer = get_store_printer_data(data)
    print(store_printer)

    return [titulo]


def end_printing(hDC):
    return hDC


def print_lines(hDC, lineas, y_inicio=Y_INIT, spacing=SPACING):
    for linea in lineas:
        hDC.append(linea)
    
    return hDC