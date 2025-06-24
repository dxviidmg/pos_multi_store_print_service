import win32print
import win32ui
import win32con

from utils import get_store_printer_data

# Constantes de formato
FONT_CONFIG = {"name": "Arial", "height": 12, "weight": 600}
Y_INIT = 20
SPACING = 40

printer_name = win32print.GetDefaultPrinter()

def start_printing(title="Ticket Python", data={}):
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc(title)
    hDC.StartPage()

    font = win32ui.CreateFont(FONT_CONFIG)
    hDC.SelectObject(font)

    y = print_store_info(hDC, data)
    return hDC, y

def print_store_info(hDC, data):
    store_printer = get_store_printer_data(data)
    print(store_printer)  # Supongo es para debug

    y = Y_INIT

    def print_line_if_exists(value):
        nonlocal y
        if value:
            hDC.TextOut(0, y, value)
            y += Y_INIT

    print_line_if_exists(store_printer['store']['tenant_name'])
    print_line_if_exists(store_printer['store']['address'])
    print_line_if_exists(store_printer['store']['phone_number'])

    y += Y_INIT  # Espacio adicional después del encabezado
    return y

def print_lines(hDC, lines, y_start, is_test=False):
    y = y_start

    if is_test:
        max_width = hDC.GetDeviceCaps(win32con.HORZRES)
        hDC.TextOut(0, y, f'Ancho máximo: {max_width}px.')
        return hDC

    for line in lines:
        hDC.TextOut(0, y, line)
        y += SPACING

    return hDC, y

def end_printing(hDC):
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()