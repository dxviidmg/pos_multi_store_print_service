import win32print
import win32ui

printer_name = win32print.GetDefaultPrinter()  # O puedes especificar el nombre exacto
hprinter = win32print.OpenPrinter(printer_name)
printer_info = win32print.GetPrinter(hprinter, 2)

# Crear un contexto de dispositivo
hDC = win32ui.CreateDC()
hDC.CreatePrinterDC(printer_name)
hDC.StartDoc("Ticket Python")
hDC.StartPage()

# Escribe texto simple
hDC.TextOut(100, 100, "¡Hola desde Python!")
hDC.TextOut(100, 150, "Gracias por tu compra.")

hDC.EndPage()
hDC.EndDoc()
hDC.DeleteDC()