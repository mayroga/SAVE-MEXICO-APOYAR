```python
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="MEXICANO APOYA MEXICANO", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def inicio():
    return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
    return {"ok": True, "app": "MEXICANO APOYA MEXICANO"}

@app.get("/api/servicio/{servicio}")
def servicio(servicio: str):
    servicios = {
        "cita": {
            "titulo": "TENGO UNA CITA",
            "texto": "Te ayudaremos a preparar la información que necesitas revisar antes de acudir a tu cita."
        },
        "documento": {
            "titulo": "NO SÉ QUÉ DOCUMENTO NECESITO",
            "texto": "Te ayudaremos a identificar qué información debes revisar según lo que necesitas resolver."
        }
    }
    return servicios.get(servicio, {
        "titulo": "SERVICIO NO ENCONTRADO",
        "texto": "Regresa y selecciona una de las opciones."
    })
```
