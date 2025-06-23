import win32print
import win32ui
import win32con


from utils import get_store_printer_data

# Formato general de la fuente
FORMAT = {"name": "Arial", "height": 15, "weight": 600}
Y_INIT = 20
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
    hDC.TextOut(0, y, store_printer['store']['tenant_name'])
    y += Y_INIT

    if store_printer['store']['address']:
        hDC.TextOut(0, y, store_printer['store']['address'])
        y += Y_INIT

    if store_printer['store']['phone_number']:
        hDC.TextOut(0, y, store_printer['store']['phone_number'])
        y += Y_INIT
    return hDC, y



def end_printing(hDC):
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def print_lines(hDC, lineas, y_inicio, is_test=False):
    if is_test:
        max_width = hDC.GetDeviceCaps(win32con.HORZRES)
        y_inicio += Y_INIT
        hDC.TextOut(0, y_inicio, 'Ancho maximo' + max_width)
        return hDC
    else:
        y = y_inicio
        for linea in lineas:
            hDC.TextOut(0, y, linea)
            y += SPACING
        return hDC