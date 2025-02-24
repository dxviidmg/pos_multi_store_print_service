import socket
from escpos.printer import Usb
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
    
    printer.text(text + "\n")
    printer.cut()
    print(f"POST recibido: {text}")
    return JSONResponse(content={"message": "Datos recibidos correctamente"})