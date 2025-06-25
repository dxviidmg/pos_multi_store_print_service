import requests

def get_store_printer_data(data):

    store_printer = str(data['store_printer'])
    token = data['token']
    api_url = data['api_url']

    url = api_url + store_printer

    # Si requiere headers (por ejemplo, autenticación):
    headers = {
        'Authorization': 'Token ' +  token,
        'Content-Type': 'application/json'
    }

    # Haces la petición GET
    response = requests.get(url, headers=headers)

    # Verificas que la petición fue exitosa
    if response.status_code == 200:
        data = response.json()
        return data