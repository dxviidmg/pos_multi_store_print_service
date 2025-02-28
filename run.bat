@echo off
:: Asegúrate de que las dependencias estén instaladas
echo Instalando dependencias...
pip install -r requirements.txt

:: Ejecutar el servidor FastAPI con Uvicorn
echo Iniciando FastAPI con Uvicorn...
uvicorn main:app --host 0.0.0.0 --port 5000

pause
