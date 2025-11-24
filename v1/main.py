from escpos.printer import Usb
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime
from logging_config import logger 


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
    try:
        printer.set(align='center', bold=False, double_height=False, double_width=False)    
        printer.text("Hola Python\n")
        # Imprimir con alineación centrada, negrita, altura doble, y ancho doble
        printer.set(align='center', bold=True, double_height=True, double_width=True)
        printer.text("Texto con formato centrado, negrita, altura y ancho doble.\n")

        # Imprimir con alineación a la izquierda, fuente B, subrayado y sin negrita
        printer.set(align='left', font='b', underline=True, bold=False)
        printer.text("Texto con fuente B, subrayado y alineación a la izquierda.\n")

        # Imprimir texto con tachado y alineado a la derecha
        printer.text("Texto tachado y alineado a la derecha.\n")


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
        printer.text(f"Total: ${float(data['total']):.2f}\n")

        if 'payment' in data:
            printer.text(f"Pagó con: ${float(data['payment']['paidWith']):.2f}\n")
            printer.text(f"Cambio: ${float(data['payment']['change']):.2f}\n\n")

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
