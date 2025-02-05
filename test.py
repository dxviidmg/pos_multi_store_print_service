import socket

# Dirección del servidor
host = "127.0.0.1"
port = 5000
message = "¡Ticket de prueba desde cliente Python!"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    s.sendall(message.encode('utf-8'))
    data = s.recv(1024)

print("Respuesta del servidor:", data.decode('utf-8'))
