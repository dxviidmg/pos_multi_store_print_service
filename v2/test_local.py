import win32print
import win32ui

printer_name = win32print.GetDefaultPrinter()
hprinter = win32print.OpenPrinter(printer_name)
printer_info = win32print.GetPrinter(hprinter, 2)

# Crear contexto de dispositivo
hDC = win32ui.CreateDC()
hDC.CreatePrinterDC(printer_name)
hDC.StartDoc("Ticket Python")
hDC.StartPage()

# Crear una fuente más grande
font = win32ui.CreateFont({
    "name": "Arial",
    "height": 40,  # Tamaño de la fuente (cuanto más grande el número, más grande el texto)
    "weight": 700,  # Negrita (opcional)
})

hDC.SelectObject(font)

# Escribir texto alineado a la izquierda (x cercano a 0)
hDC.TextOut(10, 100, "¡Hola desde Python!")
hDC.TextOut(10, 160, "Gracias por tu compra.")

hDC.EndPage()
hDC.EndDoc()
hDC.DeleteDC()