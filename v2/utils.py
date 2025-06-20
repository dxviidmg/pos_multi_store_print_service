import requests

def get_store_printer_data(data):

    id = str(data['store'])
    token = data['token']
    api_url = data['api_url']

    url = api_url + id
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