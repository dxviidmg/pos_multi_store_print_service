from escpos.printer import Usb

# Ajusta estos valores según tu impresora
VENDOR_ID = 0x04b8  # ID de Epson
PRODUCT_ID = 0x0202  # ID de TM-T88V
INTERFACE = 0  # Interfaz USB

# Crear objeto de impresora
printer = Usb(VENDOR_ID, PRODUCT_ID, INTERFACE)

# Imprimir texto
printer.text("¡Hola desde Epson TM-T88V!\n")
printer.text("Gracias por tu compra.\n")

# Cortar papel
printer.cut()