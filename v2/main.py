from escpos.printer import Usb
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime
from logging_config import logger 


import win32print
import win32ui





app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos
    allow_headers=["*"],  # Permite todos los encabezados
)

#Quitar
printer = Usb(0x04b8, 0x0202)

printer_name = win32print.GetDefaultPrinter()
hprinter = win32print.OpenPrinter(printer_name)
printer_info = win32print.GetPrinter(hprinter, 2)

@app.get("/")
def read_root():
    return {"message": "Hola Mundo"}

@app.post("/test/")
async def post_test(request: Request):
    try:
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        hDC.StartDoc("Ticket Python")
        hDC.StartPage()

        # Crear una fuente más grande
        font = win32ui.CreateFont({
            "name": "Arial",
            "height": 40,  # Tamaño de la fuente (cuanto más grande el número, más grande el texto)
            "weight": 700,  # Negrita (opcional)
        })

        hDC.SelectObject(font)

        # Escribir texto alineado a la izquierda (x cercano a 0)
        hDC.TextOut(0, 100, "¡Hola desde Python!")
        hDC.TextOut(0, 160, "Gracias por tu compra.")

        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()

        print(f"POST recibido")
        return JSONResponse(content={"message": "Datos recibidos correctamente"})


    except HTTPException as http_error:
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        # Manejo de errores generales
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)

@app.post("/ticket/")
async def post_ticket(request: Request):
    try:
        data = await request.json()
        if "total" not in data:
            raise HTTPException(status_code=400, detail="Falta el campo 'total'")

        required_fields = ["store_products", "products_sale"]
        products = []
        for field in required_fields:
            if field in data:
                products = data[field]
                break

        if not products:
            raise HTTPException(status_code=400, detail="Faltan datos de productos")

        # Obtener la fecha y hora actual
        now = datetime.datetime.now()
        formatted_date = now.strftime("%d/%m/%Y %H:%M:%S")

        # === INICIO IMPRESIÓN CON GDI ===
        hDC = win32ui.CreateDC()
        hDC.CreatePrinterDC(printer_name)
        hDC.StartDoc("Ticket Python")
        hDC.StartPage()

        font = win32ui.CreateFont({
            "name": "Arial",
            "height": 30,
            "weight": 500,
        })
        hDC.SelectObject(font)

        y = 10
        spacing = 40
        hDC.TextOut(0, y, f"Fecha: {formatted_date}")
        y += spacing
        y += spacing
        # Tabla

        if 'sale_exchange' in data:
            products_refund = data['sale_exchange']['products_sale']

            hDC.TextOut(0, y, "Productos devueltos")
            y += spacing
            hDC.TextOut(0, y, "Cant |     Producto     | Importe")
            y += spacing


            for product in products_refund:
                qty = product["returned_quantity"]
                name = str(product["name"])[:18].ljust(18)
                price = float(product["price"])
                total = qty * price
                line = f"{qty:<7} | {name} | {total:7.2f}"
                hDC.TextOut(0, y, line)
                y += spacing


        hDC.TextOut(0, y, "# |     Producto     | Importe")
        y += spacing

        products = data[field]
        for product in products:
            qty = product["quantity"]
            name = str(product["name"])[:18].ljust(18)
            price = float(product["price"])
            total = qty * price
            line = f"{qty:<7} | {name} | {total:7.2f}"
            hDC.TextOut(0, y, line)
            y += spacing

        # Total
        y += spacing
        hDC.TextOut(0, y, f"TOTAL: ${float(data['total']):.2f}")
        if data['reservation_in_progress']:
            hDC.TextOut(0, y, f"Pagado: ${float(data['paid']):.2f}")
            y += spacing
            debit = data['total'] - data['paid']
            hDC.TextOut(0, y, f"Pendiente a pagar: ${float(debit):.2f}")

        y += spacing
        hDC.TextOut(0, y, f"* SmartVenta *")
        y += spacing
        hDC.TextOut(0, y, f"¡¡¡Gracias por su compra!!!")
        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()
        # === FIN IMPRESIÓN ===

        return JSONResponse(content={"message": "Ticket impreso correctamente"}, status_code=200)

    except HTTPException as http_error:
        print(http_error)
        logger.exception("Unexpected error occurred")
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    except Exception as e:
        print(e)
        logger.exception("Unexpected error occurred")
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)