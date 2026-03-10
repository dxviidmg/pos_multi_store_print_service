import requests

def get_store_printer_data(data):
    store_printer = str(data['store_printer'])
    token = data['token']
    api_url = data['api_url']
    url = api_url + store_printer

    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()