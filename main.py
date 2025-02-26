from escpos.printer import Usb
from fastapi import FastAPI, Request, HTTPException
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
    printer.set(align='center', bold=False, double_height=False, double_width=False)    
    printer.text(text + "\n")
    # Imprimir con alineación centrada, negrita, altura doble, y ancho doble
    printer.set(align='center', bold=True, double_height=True, double_width=True)
    printer.text("Texto con formato centrado, negrita, altura y ancho doble.\n")

    # Imprimir con alineación a la izquierda, fuente B, subrayado y sin negrita
    printer.set(align='left', font='b', underline=True, bold=False)
    printer.text("Texto con fuente B, subrayado y alineación a la izquierda.\n")

    # Imprimir texto con tachado y alineado a la derecha
    printer.text("Texto tachado y alineado a la derecha.\n")


    printer.cut()
    print(f"POST recibido: {text}")
    return JSONResponse(content={"message": "Datos recibidos correctamente"})

@app.post("/ticket/")
async def post_ticket(request: Request):
    try:
        # Obtener los datos de la solicitud
        data = await request.json()
        if "data" not in data:
            raise HTTPException(status_code=400, detail="Falta el campo 'data' en la solicitud")
        
        data = data["data"]

        # Verificar si todos los campos requeridos existen
        required_fields = ["tenant_name", "client", "store_products", "total"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Falta el campo '{field}' en los datos")

        # Obtener la fecha y hora actual
        now = datetime.datetime.now()
        formatted_date = now.strftime("%d/%m/%Y %H:%M:%S")

        # Imprimir el nombre del inquilino
        printer.set(align='center', bold=True, double_height=True, double_width=True)
        printer.text(data["tenant_name"] + "\n")
        printer.set(align='left', bold=False, double_height=False, double_width=False, font="b")

        printer.text("----------------------------\n")

        printer.text("Fecha y hora: " + formatted_date + "\n")
        printer.text("----------------------------\n")

        # Imprimir el nombre del cliente, si existe
        if 'full_name' in data['client']:
            printer.text("Cliente: " + data['client']['full_name'] + "\n")
            printer.text("----------------------------\n")

        # Imprimir tabla de productos

        printer.text("Producto | Cantidad | Precio | Importe\n")
        printer.text("----------------------------\n")
        
        # Recorrer los productos y mostrar la información
        for product in data['store_products']:
            description = product['description']
            quantity = product['quantity']
            price = product['price']
            total_price = price * quantity
            printer.text(f"{description} | {quantity} | ${price:6.2f} | ${total_price:7.2f}\n")
        
        # Imprimir total
        printer.text("----------------------------\n")
        printer.set(align='right', bold=False, double_height=False, double_width=False)
        printer.text(f"Total: ${data['total']:.2f}\n")

        printer.text("----------------------------\n")

        printer.set(align='center', bold=False, double_height=False, double_width=False)
        printer.text("🔹Este negocio usa SmartVenta🔹\n")
        printer.text("📞 Informes: +52 55 61 65 25 99\n")
        printer.cut()

        # Respuesta de éxito
        return JSONResponse(content={"message": "Datos recibidos correctamente"}, status_code=200)

    except HTTPException as http_error:
        # Manejo de errores en la solicitud
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    except Exception as e:
        # Manejo de errores generales
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
