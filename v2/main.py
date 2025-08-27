from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime
from logging_config import logger 
from dotenv import load_dotenv
import os

from printer_functions import *

load_dotenv()

ADD_CODE = os.getenv('ADD_CODE', 'False')
ADD_CODE = ADD_CODE.lower() in ("true", "1", "yes", "y")

print('ADD_CODE', ADD_CODE, type(ADD_CODE))

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


@app.post("/test/")
async def post_test(request: Request):
    try:
        data = await request.json()
        hDC, y, _ = start_printing("Ticket Test", data)
        print_lines(hDC, [], y, True)

        end_printing(hDC)

        logger.info("Impresión test completada")
        return JSONResponse(content={"message": "Datos recibidos correctamente"})
    
    except Exception as e:
        print(e)
        logger.exception("Unexpected error occurred")
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
        
        hDC, y, accepts_exchanges = start_printing("Ticket Venta", data)

        # Encabezado
        lineas = [
            f"Folio: {data['id']}",
            f"Fecha: {date}",
            "",
            "#  |      Producto       | Importe"
        ]
        hDC, y = print_lines(hDC, lineas, y)

        # Productos
        for product in products:
            print(product.keys())
            qty = product["quantity"]
            name = str(product["name"])[:14].ljust(14)
            if ADD_CODE:
                code_name = f'{product["code"]} {product["name"]}'
                print(code_name)
                name = code_name[:14].ljust(14)
            price = float(product["price"])
            total = qty * price
            linea = f"{qty:<3} | {name} | {total:7.2f}"
            hDC.TextOut(0, y, linea)
            y += SPACING

        # Total general
        y += SPACING
        hDC.TextOut(0, y, f"Total: ${float(data['total']):.2f}")
        y += SPACING
        if 'payment' in data:
            hDC.TextOut(0, y, f"Pagó con: ${float(data['payment']['paidWith']):.2f}")
            y += SPACING
            hDC.TextOut(0, y, f"Cambio: ${float(data['payment']['change']):.2f}")
            y += SPACING
        else:
            hDC.TextOut(0, y, f"Soy un ticket de respaldo")
            y += SPACING

        if data.get('reservation_in_progress'):
            hDC.TextOut(0, y, f"Pagado: ${float(data['paid']):.2f}")
            y += SPACING
            debit = float(data['total']) - float(data['paid'])
            hDC.TextOut(0, y, f"Pendiente a pagar: ${debit:.2f}")
            y += SPACING

        # Devoluciones
        if 'sale_exchange' in data and 'products_sale' in data['sale_exchange']:
            amount_refund = 0
            products_refund = data['sale_exchange']['products_sale']
            lineas = [
                "",
                "Productos devueltos",
                "# |      Producto      | Importe"
            ]
            hDC, y = print_lines(hDC, lineas, y_inicio=y)

            for product in products_refund:
                qty = product["returned_quantity"]
                if qty == 0:
                    continue
                name = str(product["name"])[:14].ljust(14)
                price = float(product["price"])
                total = qty * price
                amount_refund += total
                linea = f"{qty:<3} | {name} | {total:7.2f}"
                hDC.TextOut(0, y, linea)
                y += SPACING

            y += SPACING
            hDC.TextOut(0, y, f"Total devolución: ${amount_refund:.2f}")
            y += SPACING
            hDC.TextOut(0, y, f"Total a pagar: ${float(data['total']) - amount_refund:.2f}")
            y += SPACING

        # Pie de ticket
        lineas = [
            "",
            "* SmartVenta *",
            "¡¡¡Gracias por su compra!!!"
        ]

        if accepts_exchanges is True:
            lineas.extend(["Para cualquier cambio,", "presentar su ticket"])
        print_lines(hDC, lineas, y_inicio=y)

        end_printing(hDC)

        logger.info("Ticket impreso correctamente")
        return JSONResponse(content={"message": "Ticket impreso correctamente"})
    
    except HTTPException as http_error:
        logger.exception("Error HTTP")
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    
    except Exception as e:
        print(e)
        logger.exception("Unexpected error occurred")
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
