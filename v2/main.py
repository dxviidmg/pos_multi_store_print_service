from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import datetime
from contextlib import asynccontextmanager
from logging_config import logger 
from dotenv import load_dotenv
import os

from printer_functions import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

ADD_CODE = os.getenv('ADD_CODE', 'False')
ADD_CODE = ADD_CODE.lower() in ("true", "1", "yes", "y")

# Intervalo (segundos) para sondear el estado de la impresora y detectar cambios.
STATUS_POLL_INTERVAL = float(os.getenv('STATUS_POLL_INTERVAL', '2'))


# ---------------------------------------------------------------------------
# Detección del estado de la impresora
# ---------------------------------------------------------------------------

# Mapeo de los bits de estado de Windows (win32print) a mensajes legibles.
# Referencia: valores PRINTER_STATUS_* de la API de Windows.
PRINTER_STATUS_MESSAGES = [
    (0x00000001, "Impresora en pausa"),          # PRINTER_STATUS_PAUSED
    (0x00000002, "Error de impresora"),           # PRINTER_STATUS_ERROR
    (0x00000004, "Impresora no disponible"),      # PRINTER_STATUS_PENDING_DELETION
    (0x00000008, "Atasco de papel"),              # PRINTER_STATUS_PAPER_JAM
    (0x00000010, "Sin papel"),                    # PRINTER_STATUS_PAPER_OUT
    (0x00000020, "Falta alimentación manual"),    # PRINTER_STATUS_MANUAL_FEED
    (0x00000040, "Problema de papel"),            # PRINTER_STATUS_PAPER_PROBLEM
    (0x00000080, "Impresora sin conexión"),       # PRINTER_STATUS_OFFLINE
    (0x00000100, "Entrada/salida activa"),        # PRINTER_STATUS_IO_ACTIVE
    (0x00000200, "Impresora ocupada"),            # PRINTER_STATUS_BUSY
    (0x00000400, "Imprimiendo"),                  # PRINTER_STATUS_PRINTING
    (0x00000800, "Bandeja de salida llena"),      # PRINTER_STATUS_OUTPUT_BIN_FULL
    (0x00001000, "Impresora no disponible"),      # PRINTER_STATUS_NOT_AVAILABLE
    (0x00002000, "Esperando"),                    # PRINTER_STATUS_WAITING
    (0x00004000, "Procesando"),                   # PRINTER_STATUS_PROCESSING
    (0x00008000, "Inicializando"),                # PRINTER_STATUS_INITIALIZING
    (0x00010000, "Calentando"),                   # PRINTER_STATUS_WARMING_UP
    (0x00020000, "Poco tóner"),                   # PRINTER_STATUS_TONER_LOW
    (0x00040000, "Sin tóner"),                    # PRINTER_STATUS_NO_TONER
    (0x00080000, "Expulsión de página pendiente"),# PRINTER_STATUS_PAGE_PUNT
    (0x00100000, "Se requiere intervención del usuario"),  # PRINTER_STATUS_USER_INTERVENTION
    (0x00200000, "Sin memoria"),                  # PRINTER_STATUS_OUT_OF_MEMORY
    (0x00400000, "Puerta abierta"),               # PRINTER_STATUS_DOOR_OPEN
    (0x00800000, "No se pudo recuperar el estado"),# PRINTER_STATUS_SERVER_UNKNOWN
    (0x01000000, "Modo de ahorro de energía"),    # PRINTER_STATUS_POWER_SAVE
]

# Bits que NO impiden imprimir (estados transitorios/informativos).
# Si el estado solo contiene estos bits, la impresora se considera lista.
NON_BLOCKING_STATUS_MASK = (
    0x00000100  # IO_ACTIVE
    | 0x00000200  # BUSY
    | 0x00000400  # PRINTING
    | 0x00002000  # WAITING
    | 0x00004000  # PROCESSING
    | 0x00008000  # INITIALIZING
    | 0x00010000  # WARMING_UP
    | 0x01000000  # POWER_SAVE
)


def _describe_status(status: int) -> str:
    """Devuelve un texto legible a partir de los bits de estado de Windows."""
    messages = [msg for bit, msg in PRINTER_STATUS_MESSAGES if status & bit]
    if messages:
        return ", ".join(messages)
    return f"Impresora con estado: {status}"


def get_printer_status() -> dict:
    """Consulta la impresora predeterminada y devuelve el estado normalizado.

    Retorna un dict con la forma:
        {"connected": bool, "error": str | None}
    """
    try:
        printer_name = win32print.GetDefaultPrinter()
        handle = win32print.OpenPrinter(printer_name)
        try:
            info = win32print.GetPrinter(handle, 2)
        finally:
            win32print.ClosePrinter(handle)

        status = info.get('Status', 0)

        # Estado 0 o solo bits no bloqueantes => lista para imprimir.
        if status == 0 or (status & ~NON_BLOCKING_STATUS_MASK) == 0:
            return {"connected": True, "error": None}

        return {"connected": False, "error": _describe_status(status)}
    except Exception as e:
        # No hay impresora / apagada / driver no responde.
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
        # Inicializa el estado sin difundir (aún no hay clientes garantizados).
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
    try:
        data = await request.json()
        hDC, y, _ = start_printing("Ticket Test", data)
        hDC, y = print_lines(hDC, [], y, True)
        end_printing(hDC)

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

        date = data.get('created_at', datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        hDC, y, _ = start_printing("Ticket Venta", data)

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
            qty = product["quantity"]
            name = str(product["name"])[:14].ljust(14)
            if ADD_CODE:
                name = f'{product["code"]} {product["name"]}'[:14].ljust(14)
            price = float(product["price"])
            total = qty * price
            hDC.TextOut(0, y, f"{qty:<3} | {name} | {total:7.2f}")
            y += SPACING

        # Total general
        y += SPACING
        hDC.TextOut(0, y, f"Total: ${float(data['total']):.2f}")
        y += SPACING

        if data.get('reservation_in_progress'):
            # Es un apartado
            paid = sum(float(p.get('amount', 0)) for p in data.get('payments', []))
            debit = float(data['total']) - paid
            hDC.TextOut(0, y, f"*** APARTADO ***")
            y += SPACING
            hDC.TextOut(0, y, f"Abonado: ${paid:.2f}")
            y += SPACING
            hDC.TextOut(0, y, f"Resta por pagar: ${debit:.2f}")
            y += SPACING
        elif 'payment' in data:
            hDC.TextOut(0, y, f"Pagó con: ${float(data['payment']['paidWith']):.2f}")
            y += SPACING
            hDC.TextOut(0, y, f"Cambio: ${float(data['payment']['change']):.2f}")
            y += SPACING
        else:
            hDC.TextOut(0, y, f"Soy un ticket de respaldo")
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
            hDC, y = print_lines(hDC, lineas, y)

            for product in products_refund:
                qty = product["returned_quantity"]
                if qty == 0:
                    continue
                name = str(product["name"])[:14].ljust(14)
                price = float(product["price"])
                total = qty * price
                amount_refund += total
                hDC.TextOut(0, y, f"{qty:<3} | {name} | {total:7.2f}")
                y += SPACING

            y += SPACING
            hDC.TextOut(0, y, f"Total devolución: ${amount_refund:.2f}")
            y += SPACING
            hDC.TextOut(0, y, f"Total a pagar: ${float(data['total']) - amount_refund:.2f}")
            y += SPACING

        # Pie de ticket
        lineas = [
            "",
            "¡¡¡Gracias por su compra!!!"
        ]
        hDC, y = print_lines(hDC, lineas, y)

        end_printing(hDC)

        logger.info("Ticket impreso correctamente")
        return JSONResponse(content={"message": "Ticket impreso correctamente"})
    
    except HTTPException as http_error:
        logger.exception("Error HTTP")
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
