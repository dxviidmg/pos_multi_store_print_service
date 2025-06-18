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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración global de la impresora
printer_name = win32print.GetDefaultPrinter()

# Formato general de la fuente
FORMAT = {"name": "Arial", "height": 30, "weight": 700}
Y_INIT = 10
SPACING = 40


def iniciar_impresion(titulo="Ticket Python"):
    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    hDC.StartDoc(titulo)
    hDC.StartPage()
    font = win32ui.CreateFont(FORMAT)
    hDC.SelectObject(font)
    return hDC


def finalizar_impresion(hDC):
    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()


def imprimir_lineas(hDC, lineas, y_inicio=Y_INIT, spacing=SPACING):
    y = y_inicio
    for linea in lineas:
        hDC.TextOut(0, y, linea)
        y += spacing
    return y


@app.get("/")
def read_root():
    return {"message": "Hola Mundo"}


@app.post("/test/")
async def post_test(request: Request):
    try:
        hDC = iniciar_impresion("Ticket Test")

        lineas = [
            "¡Hola desde Python!",
            "Gracias por tu compra."
        ]
        imprimir_lineas(hDC, lineas)

        finalizar_impresion(hDC)

        logger.info("Impresión test completada")
        return JSONResponse(content={"message": "Datos recibidos correctamente"})
    
    except Exception as e:
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

        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        hDC = iniciar_impresion("Ticket Venta")

        # Encabezado
        lineas = [
            f"Folio: {data['id']}",
            f"Fecha: {now}",
            "",
            "Cant |     Producto     | Importe"
        ]
        y = imprimir_lineas(hDC, lineas)

        # Productos
        for product in products:
            qty = product["quantity"]
            name = str(product["name"])[:15].ljust(15)
            price = float(product["price"])
            total = qty * price
            linea = f"{qty:<3} | {name} | {total:7.2f}"
            hDC.TextOut(0, y, linea)
            y += SPACING

        # Total general
        y += SPACING
        hDC.TextOut(0, y, f"TOTAL: ${float(data['total']):.2f}")
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
                "Cant |     Producto     | Importe"
            ]
            y = imprimir_lineas(hDC, lineas, y_inicio=y)

            for product in products_refund:
                qty = product["returned_quantity"]
                if qty == 0:
                    continue
                name = str(product["name"])[:15].ljust(15)
                price = float(product["price"])
                total = qty * price
                amount_refund += total
                linea = f"{qty:<3} | {name} | {total:7.2f}"
                hDC.TextOut(0, y, linea)
                y += SPACING

            y += SPACING
            hDC.TextOut(0, y, f"TOTAL DEVUELTO: ${amount_refund:.2f}")
            y += SPACING
            hDC.TextOut(0, y, f"TOTAL FINAL: ${float(data['total']) - amount_refund:.2f}")
            y += SPACING

        # Pie de ticket
        lineas = [
            "",
            "* SmartVenta *",
            "¡¡¡Gracias por su compra!!!"
        ]
        imprimir_lineas(hDC, lineas, y_inicio=y)

        finalizar_impresion(hDC)

        logger.info("Ticket impreso correctamente")
        return JSONResponse(content={"message": "Ticket impreso correctamente"})
    
    except HTTPException as http_error:
        logger.exception("Error HTTP")
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
