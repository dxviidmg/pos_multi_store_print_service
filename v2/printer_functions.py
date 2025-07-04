import win32print
import win32ui
import win32con


from utils import get_store_printer_data

Y_INIT = 20
SPACING = 40

printer_name = win32print.GetDefaultPrinter()

def start_printing(titulo="Ticket Python", data={}):
    store_printer = get_store_printer_data(data)
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc(titulo)
    hDC.StartPage()
    FORMAT = {"name": "Arial", "height": store_printer['printer']['font_height'], "weight": 600}
    font = win32ui.CreateFont(FORMAT)
    hDC.SelectObject(font)



    y = Y_INIT
    hDC.TextOut(0, y, store_printer['store']['tenant_name'])
    y += SPACING

    if store_printer['store']['address']:
        hDC.TextOut(0, y, store_printer['store']['address'])
        y += SPACING

    if store_printer['store']['phone_number']:
        hDC.TextOut(0, y, store_printer['store']['phone_number'])
        y += SPACING
    return hDC, y, store_printer['store']['accepts_exchanges']



def end_printing(hDC):
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def print_lines(hDC, lineas, y_inicio, is_test=False):
    if is_test:
        max_width = hDC.GetDeviceCaps(win32con.HORZRES)
        y_inicio += Y_INIT
        hDC.TextOut(0, y_inicio, 'Ancho maximo: ' + str(max_width) + 'pxs.')
        return hDC
    else:
        y = y_inicio
        for linea in lineas:
            hDC.TextOut(0, y, linea)
            y += SPACING
        return hDC, y