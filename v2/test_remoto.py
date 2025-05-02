import requests

# URL de tu servidor
url = "http://127.0.0.1:5000/test/"  # Cambia esta URL si tu servidor tiene una URL diferente

# Datos a enviar en el cuerpo de la solicitud (JSON)
data = {
    "data": "Este es un mensaje de prueba"
}

# Realizar la solicitud POST
response = requests.post(url, json=data)

print(response)

# Mostrar la respuesta
if response.status_code == 200:
    print("Éxito:", response.json())
else:
    print("Error:", response.status_code, response.text)
