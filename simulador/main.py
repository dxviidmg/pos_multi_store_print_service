from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import datetime
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "tickets")
Path(LOG_DIR).mkdir(exist_ok=True)

# Intervalo (segundos) para sondear el estado de la impresora y detectar cambios.
STATUS_POLL_INTERVAL = float(os.getenv('STATUS_POLL_INTERVAL', '2'))


# ---------------------------------------------------------------------------
# Estado simulado de la impresora
# ---------------------------------------------------------------------------
# En el simulador el estado se guarda en memoria y puede cambiarse mediante el
# endpoint auxiliar POST /simular-estado/ para probar la difusión por WebSocket.
_simulated_status = {"connected": True, "error": None}


def get_printer_status() -> dict:
    """Devuelve el estado simulado normalizado: {connected, error}."""
    return dict(_simulated_status)


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
            print("[SIMULADOR] Error enviando estado inicial por WebSocket")

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
        self._last_status = get_printer_status()
        while True:
            try:
                await asyncio.sleep(STATUS_POLL_INTERVAL)
                status = get_printer_status()
                if status != self._last_status:
                    self._last_status = status
                    await self.broadcast(status)
            except asyncio.CancelledError:
                break
            except Exception:
                print("[SIMULADOR] Error en el bucle de sondeo de estado")


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
        print("[SIMULADOR] Error en la conexión WebSocket de estado")
    finally:
        await hub.disconnect(websocket)


@app.post("/simular-estado/")
async def simular_estado(request: Request):
    """Endpoint auxiliar (solo simulador) para cambiar el estado de la impresora.

    Cuerpo JSON esperado: {"connected": bool, "error": str | null}
    El cambio se difunde por WebSocket a través del poll_loop.
    """
    data = await request.json()
    connected = bool(data.get("connected", True))
    error = data.get("error")
    _simulated_status["connected"] = connected
    _simulated_status["error"] = None if connected else (error or "Impresora no disponible")
    print(f"[SIMULADOR] Estado cambiado a: {_simulated_status}")
    return JSONResponse(content={"message": "Estado actualizado", "status": _simulated_status})


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
        
        # Calcular info de apartado si aplica
        is_reservation = data.get('reservation_in_progress', False)
        paid = sum(float(p.get('amount', 0)) for p in data.get('payments', [])) if is_reservation else 0
        debit = float(data['total']) - paid if is_reservation else 0

        # Simular impresión guardando en archivo
        ticket_data = {
            "folio": data.get('id'),
            "fecha": date,
            "productos": products,
            "total": float(data['total']),
            "pago": data.get('payment'),
            "es_apartado": is_reservation,
            "timestamp": datetime.datetime.now().isoformat()
        }

        if is_reservation:
            ticket_data["abonado"] = paid
            ticket_data["resta_por_pagar"] = debit
        
        ticket_file = os.path.join(LOG_DIR, f"ticket_{data.get('id', 'sin_id')}.json")
        with open(ticket_file, 'w') as f:
            json.dump(ticket_data, f, indent=2)
        
        print(f"[SIMULADOR] Ticket guardado en: {ticket_file}")
        return JSONResponse(content={"message": "Ticket impreso correctamente"})
    
    except HTTPException as http_error:
        return JSONResponse(content={"message": str(http_error.detail)}, status_code=http_error.status_code)
    
    except Exception as e:
        return JSONResponse(content={"message": f"Error al procesar la solicitud: {str(e)}"}, status_code=500)
