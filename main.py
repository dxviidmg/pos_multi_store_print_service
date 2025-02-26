from escpos.printer import Usb
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos
    allow_headers=["*"],  # Permite todos los encabezados
)

# Configurar la impresora USB (ajusta los valores según tu impresora)
printer = Usb(0x04b8, 0x0202)

@app.get("/")
def read_root():
    return {"message": "Hola Mundo"}

@app.post("/test/")
async def post_test(request: Request):
    data = await request.json()

    text = data['data']
    printer.set(align='center', bold=True, double_height=True, double_width=True)    
    printer.text(text + "\n")
    printer.set(align='center', bold=True, double_height=False, double_width=False)    
    printer.text(text + "\n")
    printer.set(align='center', bold=True, double_height=False, double_width=True)    
    printer.text(text + "\n")
    printer.set(align='center', bold=True, double_height=True, double_width=False)    
    printer.text(text + "\n")
    printer.set(align='center', bold=True, double_height=True, double_width=True)
    printer.text("Texto con alto y ancho dobles en negrita y centrado.\n")

    printer.set(align='right', font='b', underline=True)
    printer.text("Texto en fuente B, subrayado y alineado a la derecha.\n")

    printer.set(align='left', invert=False)
    printer.text("Texto invertido y alineado a la izquierda.\n")

    printer.set(align='center', double_height=False, double_width=False, font='a')
    printer.text("Texto normal, alineado al centro.\n")
    printer.cut()
    print(f"POST recibido: {text}")
    return JSONResponse(content={"message": "Datos recibidos correctamente"})

@app.post("/ticket/")
async def post_test(request: Request):
    data = await request.json()
    data = data['data']
    
    
    printer.set(align='center', bold=True, double_height=True, double_width=True)
    printer.text(data["tenant_name"] + "\n")
    printer.text("--------------------\n")
    now = datetime.datetime.now()
    printer.text("Fecha y hora:" + str(now) +"\n")
    printer.text("--------------------\n")

    if 'full_name' in data['client']:

        printer.text("Cliente:" + data['client']['full_name'] + "\n")
        printer.text("--------------------\n")

    printer.set(align='left', bold=False, double_height=False, double_width=False)
    printer.text("Producto | Cantidad | Precio | Importe\n")
    for product in data['store_products']:
        printer.text(f"{product['description']} | {product['quantity']} | ${product['price']:.2f} | {product['price'] * product['quantity']:.2f}\n" )
    
    printer.set(align='right', bold=False, double_height=False, double_width=False)
    printer.text(f"Total: ${data['total']:.2f}\n")
    printer.cut()

    return JSONResponse(content={"message": "Datos recibidos correctamente"})