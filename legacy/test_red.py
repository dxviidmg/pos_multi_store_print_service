from escpos.printer import Network

# Sustituye con la IP de tu impresora
printer = Network("192.168.1.100")

# Imprimir texto
printer.text("¡Hola desde Epson TM-T88V en Linux!\n")
printer.text("Impresión por red con Python.\n")

# Cortar papel
printer.cut()