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

# Solución definitiva al error de inicialización del trámite
class ExpedientePerfil(BaseModel):
    nombre_completo: Optional[str] = ""
    fecha_nacimiento: Optional[str] = ""
    origen_mexico: Optional[str] = ""
    direccion_usa: Optional[str] = ""
    telefono: Optional[str] = ""
    estado: Optional[str] = "Otro"
    nacionalidad: Optional[str] = "mexicana"

class Inicio(BaseModel):
    perfil: Optional[ExpedientePerfil] = None
    texto: str = ""

class Continuacion(BaseModel):
    caso: str
    pregunta_id: str = ""
    respuesta: Any = ""
    respuestas: Dict[str, Any] = Field(default_factory=dict)
    perfil: Optional[ExpedientePerfil] = None

class Seleccion(BaseModel):
    caso: str
    perfil: Optional[ExpedientePerfil] = None
    respuestas: Dict[str, Any] = Field(default_factory=dict)

def construir_pdf(r):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=letter)
    c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
    
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.07, 0.25, 0.40)
    c.drawString(55, 740, "MEXICANO APOYA MEXICANO")
    
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(55, 715, "TU HOJA DE RUTA CONSULAR SIMPLIFICADA")
    
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.line(55, 700, 555, 700)
    
    # 1. Datos del Ciudadano para Ventanilla
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 675, "1. TUS DATOS PARA DECLARAR EN VENTANILLA")
    c.setFont("Helvetica", 11)
    c.drawString(55, 655, f"Nombre Completo: {r.get('nombre_ciudadano', '')}")
    c.drawString(55, 635, f"Fecha de Nacimiento: {r.get('fecha_nacimiento', '')}")
    c.drawString(55, 615, f"Lugar de Origen (México): {r.get('origen_mexico', '')}")
    c.drawString(55, 595, f"Dirección en EE. UU.: {r.get('direccion_usa', '')}")
    c.drawString(55, 575, f"Teléfono Registrado: {r.get('telefono_ciudadano', '')}")
    c.drawString(55, 555, f"Estado Actual de Residencia: {r.get('estado_residencia', '')}")
    
    # 2. Tu Trámite
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 520, f"2. TU TRÁMITE: {r.get('nombre_tramite', '').upper()}")
    c.setFont("Helvetica", 11)
    c.drawString(55, 500, f"Estatus General: {r.get('estado', '')}")
    c.drawString(55, 480, f"Mensaje: {r.get('mensaje_estado', '')}")
    
    # 3. Costo y Cita
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 445, "3. COSTO Y CITA OBLIGATORIA")
    c.setFont("Helvetica", 11)
    c.drawString(55, 425, f"Costo estimado en ventanilla: {r.get('pago_estimado', '')}")
    c.drawString(55, 405, f"Estado de tu cita: {r.get('cita_estatus', '')}")
    
    # 4. Tu Consulado
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 370, "4. TU SEDE CONSULAR ASIGNADA")
    c.setFont("Helvetica", 11)
    c.drawString(55, 350, f"Oficina: {r.get('consulado_nombre', '')}")
    c.drawString(55, 330, f"Dirección: {r.get('consulado_direccion', '')}")
    c.drawString(55, 310, f"Teléfono central: {r.get('consulado_telefono', '')}")
    c.drawString(55, 290, f"Página oficial de internet: {r.get('url_consulado') or ''}")
    
    # 5. Lista de Documentos Oficiales
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, 255, "5. REQUISITOS OFICIALES QUE DEBES LLEVAR")
    y = 235
    for req in r.get("requisitos_oficiales", []):
        c.setFont("Helvetica", 11)
        c.drawString(70, y, f"• {req}")
        y -= 20
        
    # 6. Faltantes desglosados (Limpieza contra puntos huérfanos)
    faltantes = r.get("faltantes", [])
    if faltantes:
        y -= 5
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.7, 0.1, 0.1)
        c.drawString(55, y, "6. ¡ATENCIÓN! TE FALTA CONSEGUIR ESTO EXACTAMENTE:")
        y -= 20
        for f in faltantes:
            c.setFont("Helvetica", 10)
            if len(f) > 85:
                c.drawString(70, y, f"• {f[:85]}")
                y -= 15
                c.drawString(80, y, f"{f[85:]}")
            else:
                c.drawString(70, y, f"• {f}")
            y -= 20
    
    # Pie de página de Deslinde
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(55, 45, "Aviso: Mexicano Apoya Mexicano es una herramienta de preparación ciudadana independiente propiedad de MAY ROGA LLC.")
    c.drawString(55, 35, "No sustituye al Gobierno de México. Diseñada como soporte de datos para el ciudadano.")
    
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
        p_dict = x.perfil.dict() if x.perfil else {}
        return iniciar(x.texto, p_dict)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/seleccionar-caso")
def api_seleccionar(x: Seleccion):
    try:
        p_dict = x.perfil.dict() if x.perfil else {}
        return seleccionar_caso(x.caso, p_dict, x.respuestas)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/continuar")
def api_continuar(x: Continuacion):
    try:
        res = dict(x.respuestas or {})
        p_dict = x.perfil.dict() if x.perfil else {}
        return continuar(x.caso, res, p_dict, x.pregunta_id, x.respuesta)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/pdf-preview")
def api_pdf_preview(r: Dict[str, Any]):
    try:
        pdf = construir_pdf(r)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="Hoja_de_Ruta_Preliminar.pdf"',
                "Cache-Control": "no-store"
            }
        )
    except Exception as e:
        raise HTTPException(400, f"Error al generar la vista previa: {e}")

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
