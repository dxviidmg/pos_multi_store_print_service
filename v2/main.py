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
    data = await request.json()
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
        hDC.TextOut(10, 100, "¡Hola desde Python!")
        hDC.TextOut(10, 160, "Gracias por tu compra.")

        hDC.EndPage()
        hDC.EndDoc()
        hDC.DeleteDC()


        printer.cut()
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
        # Obtener los datos de la solicitud
        data = await request.json()
        if "data" not in data:
            raise HTTPException(status_code=400, detail="Falta el campo 'data' en la solicitud")
        
        data = data["data"]

        # Verificar si todos los campos requeridos existen
        required_fields = ["total"]

        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Falta el campo '{field}' en los datos")
            

        required_fields = ["store_products", "products_sale"]
        products = []
        for field in required_fields:
            if field in data:
                products = data[field]
                break
        
        if products == []:
            raise HTTPException(status_code=400, detail=f"Faltan datos de productos")

        # Obtener la fecha y hora actual
        printer.set(align='center', bold=False, double_height=False, double_width=False, font="b")
        now = datetime.datetime.now()
        formatted_date = now.strftime("%d/%m/%Y %H:%M:%S")
        printer.text(formatted_date + "\n\n")

        printer.set(align='left')
        # Imprimir el nombre del cliente, si existe
        # Imprimir tabla de productos
        printer.text("# |    Producto    | Importe\n")
        
        for product in products:
            quantity = str(product['quantity'])  # Convertimos a string antes de aplicar ljust
            name = product['name'][:14].ljust(14)  # Limitamos a 8 caracteres y alineamos
            price = float(product['price'])  # Convertimos a float para cálculos
            total_price = price * product['quantity']  # Multiplicamos correctamente

            printer.text(f"{quantity} | {name} | {total_price:7,.2f}\n")  
        
        # Imprimir total
        printer.text("\n")
#        printer.set(align='right', bold=False, double_height=False, double_width=False)
        printer.set(align='right')
        printer.text(f"Total: ${float(data['total']):.2f}\n\n")

#        printer.set(align='center', bold=False, double_height=False, double_width=False)
        printer.set(align='center')
        printer.text("¡Gracias por su compra!\n")
        printer.text("* SmartVenta *\n")
        printer.cut()

        # Respuesta de éxito
        return JSONResponse(content={"message": "Datos recibidos correctamente"}, status_code=200)
    except HTTPException as http_error:
        # Manejo de errores en la solicitud
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        # Manejo de errores generales
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
