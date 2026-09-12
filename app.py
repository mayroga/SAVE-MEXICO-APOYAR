# app.py
import os, io, re
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from consular_engine import (
    APP, VERSION, iniciar, seleccionar_caso, continuar, catalogo
)

app = FastAPI(title=APP, version=VERSION)
app.mount("/static", StaticFiles(directory="static"), name="static")

class Inicio(BaseModel):
    perfil: Dict[str, Any] = Field(default_factory=dict)
    texto: str = ""

class Continuacion(BaseModel):
    caso: str
    pregunta_id: str = ""
    respuesta: Any = ""
    respuestas: Dict[str, Any] = Field(default_factory=dict)
    perfil: Dict[str, Any] = Field(...)

class Seleccion(BaseModel):
    caso: str
    perfil: Dict[str, Any] = Field(default_factory=dict)
    respuestas: Dict[str, Any] = Field(default_factory=dict)

def construir_pdf(r):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=letter)
    c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
    
    # Encabezado Limpio e Institucional
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.07, 0.25, 0.40)
    c.drawString(55, 740, "MEXICANO APOYA MEXICANO")
    
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(55, 715, "TU HOJA DE RUTA CONSULAR SIMPLIFICADA")
    
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(55, 700, 555, 700)
    
    # 1. Datos del Ciudadano
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 675, "1. TUS DATOS")
    c.setFont("Helvetica", 11)
    c.drawString(55, 655, f"Nombre completo: {r.get('nombre_ciudadano', 'Ciudadano Mexicano')}")
    c.drawString(55, 635, f"Teléfono registrado: {r.get('telefono_ciudadano', 'No indicado')}")
    
    # 2. Tu Trámite
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 600, f"2. TU TRÁMITE: {r.get('nombre_tramite', '').upper()}")
    
    c.setFont("Helvetica", 11)
    c.drawString(55, 580, f"Estatus General: {r.get('estado', '')}")
    c.drawString(55, 560, f"Mensaje: {r.get('mensaje_estado', '')}")
    
    # 3. Costo y Cita
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 525, "3. COSTO Y CITA OBLIGATORIA")
    c.setFont("Helvetica", 11)
    c.drawString(55, 505, f"Costo estimado en ventanilla: {r.get('pago_estimado', '')}")
    c.drawString(55, 485, f"Estado de la cita: {r.get('cita_estatus', '')}")
    
    # 4. Tu Consulado
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 450, "4. TU SEDE CONSULAR ASIGNADA")
    c.setFont("Helvetica", 11)
    c.drawString(55, 430, f"Oficina: {r.get('consulado_nombre', '')}")
    c.drawString(55, 410, f"Dirección: {r.get('consulado_direccion', '')}")
    c.drawString(55, 390, f"Teléfono central: {r.get('consulado_telefono', '')}")
    
    # 5. Lista de Documentos Oficiales
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 355, "5. REQUISITOS OFICIALES")
    y = 335
    for req in r.get("requisitos_oficiales", []):
        c.setFont("Helvetica", 11)
        c.drawString(70, y, f"• {req}")
        y -= 20
        
    # 6. Faltantes (Si existen)
    faltantes = r.get("faltantes", [])
    if faltantes:
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.7, 0.1, 0.1)
        c.drawString(55, y, "6. ¡ATENCIÓN! TE FALTA ESTO:")
        y -= 20
        for f in faltantes:
            c.setFont("Helvetica", 11)
            c.drawString(70, y, f"• {f}")
            y -= 20
    
    # Pie de página de Deslinde
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(55, 50, "Aviso: Mexicano Apoya Mexicano es una herramienta de preparación ciudadana independiente.")
    c.drawString(55, 40, "No sustituye al Gobierno de México. Valida siempre tus documentos antes de salir.")
    
    c.save()
    out.seek(0)
    return out

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/catalogo")
def api_catalogo():
    return catalogo()

@app.post("/api/iniciar")
def api_iniciar(x: Inicio):
    try:
        return iniciar(x.texto, x.perfil)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/seleccionar-caso")
def api_seleccionar(x: Seleccion):
    try:
        return seleccionar_caso(x.caso, x.perfil, x.respuestas)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/continuar")
def api_continuar(x: Continuacion):
    try:
        res = dict(x.respuestas or {})
        perfil = dict(x.perfil or {})
        return continuar(x.caso, res, perfil, x.pregunta_id, x.respuesta)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/pdf")
def api_pdf(r: Dict[str, Any]):
    try:
        pdf = construir_pdf(r)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="Hoja_de_Ruta_Consular.pdf"',
                "Cache-Control": "no-store"
            }
        )
    except Exception as e:
        raise HTTPException(400, f"Error al generar el PDF: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
