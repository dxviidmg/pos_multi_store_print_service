import socket
from escpos.printer import Usb

def listen_for_print_request():
    # Configurar la impresora USB
    # Los valores 0x04b8 y 0x0202 son específicos para Epson TM-T88V, ajústalos según tu impresora
    printer = Usb(0x04b8, 0x0202)

    # Crear socket para escuchar en el puerto
    host = "127.0.0.1"
    port = 5000

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()

        print(f"Escuchando en {host}:{port}...")

        while True:
            client_socket, client_address = server_socket.accept()
            with client_socket:
                print(f"Conexión desde {client_address}")

                # Recibir los datos (texto del ticket) enviados por el servidor Django
                data = client_socket.recv(1024)
                if not data:
                    break
                ticket_text = data.decode('utf-8')

                # Imprimir el ticket usando la impresora USB
                printer.text(ticket_text + "\n")
                printer.cut()

                # Enviar confirmación al servidor
                client_socket.sendall(b"Ticket impreso correctamente")

if __name__ == "__main__":
    listen_for_print_request()
