import requests
from dotenv import load_dotenv
import os

# Carga las variables de entorno desde el archivo .env
load_dotenv()
API_URL = os.getenv("API_URL")

def get_store_printer_data(data):

    id = str(data['store'])
    token = data['token']

    url = API_URL + '/api/store-printer/' + id
    print(url)

    # Si requiere headers (por ejemplo, autenticación):
    headers = {
        'Authorization': 'Token ' +  token,
        'Content-Type': 'application/json'
    }

    # Haces la petición GET
    response = requests.get(url, headers=headers)
    print(response)

    # Verificas que la petición fue exitosa
    if response.status_code == 200:
        data = response.json()
        return data