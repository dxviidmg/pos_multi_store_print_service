from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime
import json
import os
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "tickets")
Path(LOG_DIR).mkdir(exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hola Mundo"}


@app.get("/status/")
def printer_status():
    return JSONResponse(status_code=200, content={})


@app.post("/test/")
async def post_test(request: Request):
    try:
        data = await request.json()
        print("[SIMULADOR] Test de impresión recibido")
        return JSONResponse(content={"message": "Datos recibidos correctamente"})
    except Exception as e:
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)


@app.post("/ticket/")
async def post_ticket(request: Request):
    try:
        data = await request.json()

        if "total" not in data:
            raise HTTPException(status_code=400, detail="Falta el campo 'total'")

        required_fields = ["store_products", "products_sale"]
        products = next((data[field] for field in required_fields if field in data), [])

        if not products:
            raise HTTPException(status_code=400, detail="Faltan datos de productos")

        date = data.get('created_at', datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        # Simular impresión guardando en archivo
        ticket_data = {
            "folio": data.get('id'),
            "fecha": date,
            "productos": products,
            "total": float(data['total']),
            "pago": data.get('payment'),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        ticket_file = os.path.join(LOG_DIR, f"ticket_{data.get('id', 'sin_id')}.json")
        with open(ticket_file, 'w') as f:
            json.dump(ticket_data, f, indent=2)
        
        print(f"[SIMULADOR] Ticket guardado en: {ticket_file}")
        return JSONResponse(content={"message": "Ticket impreso correctamente"})
    
    except HTTPException as http_error:
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    
    except Exception as e:
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
