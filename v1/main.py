from escpos.printer import Usb
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import datetime
from contextlib import asynccontextmanager
from logging_config import logger 
import os

# Intervalo (segundos) para sondear el estado de la impresora y detectar cambios.
STATUS_POLL_INTERVAL = float(os.getenv('STATUS_POLL_INTERVAL', '2'))

# Configurar la impresora USB (ajusta los valores según tu impresora)
# La creación se hace tolerante a fallos: si la impresora no está disponible al
# arrancar, el servidor debe seguir en pie para aceptar conexiones WebSocket y
# reportar connected=false. Se reintenta la conexión bajo demanda.
PRINTER_VID = 0x04b8
PRINTER_PID = 0x0202

printer = None


def _connect_printer():
    """Intenta (re)crear el objeto de impresora USB. Devuelve el objeto o None."""
    global printer
    try:
        printer = Usb(PRINTER_VID, PRINTER_PID)
    except Exception:
        printer = None
    return printer


# Intento inicial de conexión (no bloquea el arranque si falla).
_connect_printer()


# ---------------------------------------------------------------------------
# Detección del estado de la impresora (python-escpos)
# ---------------------------------------------------------------------------

def get_printer_status() -> dict:
    """Consulta la impresora USB y devuelve el estado normalizado.

    Retorna: {"connected": bool, "error": str | None}
    """
    global printer
    try:
        # Reintentar la conexión si aún no existe (impresora apagada al arrancar).
        if printer is None and _connect_printer() is None:
            return {"connected": False, "error": "Impresora apagada"}

        # Verifica que el dispositivo USB siga presente.
        if getattr(printer, "device", None) is None:
            printer = None
            return {"connected": False, "error": "Impresora apagada"}

        # Consulta de papel (si el driver/firmware lo soporta).
        # paper_status(): 0 = sin papel, 1 = por acabarse, 2 = OK
        try:
            paper = printer.paper_status()
            if paper == 0:
                return {"connected": False, "error": "Sin papel"}
        except Exception:
            # Algunos modelos no responden a la consulta de estado; no es fatal.
            pass

        return {"connected": True, "error": None}
    except Exception as e:
        # Falla de comunicación => impresora apagada/desconectada.
        printer = None
        return {"connected": False, "error": str(e) or "Impresora no disponible"}


# ---------------------------------------------------------------------------
# Gestor de conexiones WebSocket + difusión de cambios de estado
# ---------------------------------------------------------------------------

class PrinterStatusHub:
    """Mantiene las conexiones WebSocket y difunde los cambios de estado."""

    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._last_status: dict | None = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._clients.discard(ws)

    @staticmethod
    def _build_message(status: dict) -> dict:
        return {
            "type": "printer_status",
            "connected": status["connected"],
            "error": status["error"],
        }

    async def send_current(self, ws: WebSocket):
        """Envía el estado actual a un solo cliente (al conectarse)."""
        status = self._last_status or get_printer_status()
        try:
            await ws.send_json(self._build_message(status))
        except Exception:
            logger.exception("Error enviando estado inicial por WebSocket")

    async def broadcast(self, status: dict):
        message = self._build_message(status)
        async with self._lock:
            clients = list(self._clients)
        stale = []
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    self._clients.discard(ws)

    async def poll_loop(self):
        """Sondea el estado periódicamente y difunde solo cuando cambia."""
        self._last_status = await asyncio.to_thread(get_printer_status)
        while True:
            try:
                await asyncio.sleep(STATUS_POLL_INTERVAL)
                status = await asyncio.to_thread(get_printer_status)
                if status != self._last_status:
                    self._last_status = status
                    await self.broadcast(status)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error en el bucle de sondeo de estado")


hub = PrinterStatusHub()


@asynccontextmanager
async def lifespan(app: FastAPI):
    poll_task = asyncio.create_task(hub.poll_loop())
    try:
        yield
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos
    allow_headers=["*"],  # Permite todos los encabezados
)


@app.get("/")
def read_root():
    return {"message": "Hola Mundo"}

@app.get("/status/")
def printer_status():
    status = get_printer_status()
    if status["connected"]:
        return JSONResponse(status_code=200, content={})
    return JSONResponse(content={"error": status["error"]}, status_code=503)


@app.websocket("/printer-status/")
async def printer_status_ws(websocket: WebSocket):
    await hub.connect(websocket)
    # 1) Empuja el estado actual de inmediato al conectar.
    await hub.send_current(websocket)
    try:
        # 2) Los cambios se empujan desde el poll_loop vía broadcast.
        #    Aquí solo escuchamos mensajes del cliente (heartbeat opcional).
        while True:
            data = await websocket.receive_json()
            if isinstance(data, dict) and data.get("type") == "ping":
                # 3) Heartbeat: respondemos pong para mantener viva la conexión.
                await websocket.send_json({"type": "pong"})
            # Cualquier otro mensaje del cliente se ignora (el cliente solo escucha).
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Error en la conexión WebSocket de estado")
    finally:
        await hub.disconnect(websocket)

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
        printer.set(align='right')
        printer.text(f"Total: ${float(data['total']):.2f}\n")

        if data.get('reservation_in_progress'):
            # Es un apartado
            paid = sum(float(p.get('amount', 0)) for p in data.get('payments', []))
            debit = float(data['total']) - paid
            printer.set(align='center')
            printer.text("*** APARTADO ***\n")
            printer.set(align='right')
            printer.text(f"Abonado: ${paid:.2f}\n")
            printer.text(f"Resta por pagar: ${debit:.2f}\n\n")
        elif 'payment' in data:
            printer.text(f"Pagó con: ${float(data['payment']['paidWith']):.2f}\n")
            printer.text(f"Cambio: ${float(data['payment']['change']):.2f}\n\n")
        else:
            printer.text(f"Soy un ticket de respaldo\n\n")

        printer.set(align='center')
        printer.text("¡Gracias por su compra!\n")
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
