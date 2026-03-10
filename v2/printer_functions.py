import win32print
import win32ui
import win32con
from utils import get_store_printer_data

Y_INIT = 20
SPACING = 40

def start_printing(titulo="Ticket Python", data={}):
    store_printer = get_store_printer_data(data)
    printer_name = store_printer['printer'].get('name', win32print.GetDefaultPrinter())
    
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc(titulo)
    hDC.StartPage()
    
    font = win32ui.CreateFont({
        "name": "Arial", 
        "height": store_printer['printer']['font_height'], 
        "weight": 600
    })
    hDC.SelectObject(font)

    y = Y_INIT
    for field in ['tenant_name', 'address', 'phone_number']:
        value = store_printer['store'].get(field)
        if value:
            hDC.TextOut(0, y, value)
            y += SPACING
    
    return hDC, y, store_printer



def end_printing(hDC):
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def print_lines(hDC, lineas, y_inicio, is_test=False):
    if is_test:
        max_width = hDC.GetDeviceCaps(win32con.HORZRES)
        hDC.TextOut(0, y_inicio + Y_INIT, f'Ancho maximo: {max_width}pxs.')
        return hDC, y_inicio
    
    y = y_inicio
    for linea in lineas:
        hDC.TextOut(0, y, linea)
        y += SPACING
    return hDC, y