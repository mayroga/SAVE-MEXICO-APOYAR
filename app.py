# app.py
import os, io, re
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from consular_engine import (
    APP, VERSION, iniciar, seleccionar_caso, continuar, interpretar,
    resultado, catalogo, obtener_fuentes, obtener_contacto, obtener_tarifas,
    obtener_manual, tramite_oficial, caso_info, procesar
)

app = FastAPI(title=APP, version=VERSION)
app.mount("/static", StaticFiles(directory="static"), name="static")

class Inicio(BaseModel):
    perfil: Dict[str, Any] = Field(default_factory=dict)
    texto: str = ""

class Interpretacion(BaseModel):
    texto: str = ""
    perfil: Dict[str, Any] = Field(default_factory=dict)
    caso: Optional[str] = None
    respuestas: Dict[str, Any] = Field(default_factory=dict)

class Continuacion(BaseModel):
    caso: str
    pregunta_id: str = ""
    respuesta: Any = ""
    texto: str = ""
    respuestas: Dict[str, Any] = Field(default_factory=dict)
    perfil: Dict[str, Any] = Field(..., description="El objeto perfil es obligatorio en cada petición")

class Seleccion(BaseModel):
    caso: str
    perfil: Dict[str, Any] = Field(default_factory=dict)
    respuestas: Dict[str, Any] = Field(default_factory=dict)

class ResultadoRequest(BaseModel):
    caso: str
    respuestas: Dict[str, Any] = Field(default_factory=dict)
    perfil: Dict[str, Any] = Field(..., description="El objeto perfil es obligatorio en cada petición")

def limpiar(x):
    x = "" if x is None else str(x)
    x = re.sub(r"[ \t]+", " ", x)
    x = re.sub(r"\n{3,}", "\n\n", x)
    return x.strip()

def lista_pdf(x):
    if x is None: return []
    if isinstance(x, str):
        x = limpiar(x)
        return [x] if x else []
    if isinstance(x, dict):
        return [f"{k}: {limpiar(v)}" for k, v in x.items() if limpiar(v)]
    if isinstance(x, (list, tuple)):
        return [limpiar(v) for v in x if limpiar(v)]
    x = limpiar(x)
    return [x] if x else []

def texto_pdf(c, txt, y, size=10, bold=False, leading=14):
    txt = limpiar(txt)
    if not txt: return y
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, size)
    line = ""
    for word in txt.split():
        test = (line + " " + word).strip()
        if c.stringWidth(test, font, size) <= 500:
            line = test
        else:
            if line:
                if y < 60: c.showPage(); y = 750
                c.setFont(font, size); c.drawString(55, y, line); y -= leading
            line = word
    if line:
        if y < 60: c.showPage(); y = 750
        c.setFont(font, size); c.drawString(55, y, line); y -= leading
    return y

def seccion(c, t, y):
    if y < 85: c.showPage(); y = 750
    c.setFillColorRGB(.07, .38, .63)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(55, y, t)
    c.setFillColorRGB(0, 0, 0)
    return y - 18

def campo_pdf(c, nombre, valor, y, indice):
    if y < 65: c.showPage(); y = 750
    nombre = re.sub(r"\W+", "_", nombre.lower()).strip("_") or f"campo{indice}"
    c.setFont("Helvetica-Bold", 9)
    c.drawString(55, y, nombre.replace("_", " ").title())
    c.acroform.textfield(
        name=f"campo_{indice}_{nombre}",
        value=limpiar(valor),
        x=175, y=y - 4, width=340, height=17,
        borderWidth=1, borderStyle="underlined",
        forceBorder=True, fontName="Helvetica", fontSize=9
    )
    return y - 25

def construir_pdf(r, editable=True):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=letter)
    c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
    y = 750

    c.setFont("Helvetica-Bold", 18)
    c.drawString(55, y, "MEXICANO APOYA MEXICANO")
    y -= 24
    c.setFont("Helvetica-Bold", 14)
    c.drawString(55, y, "HOJA DE RUTA / CHECKLIST")
    y -= 22

    # Detección de "MENOR DE EDAD" en textos o estructura de datos
    datos_completos_str = str(r).upper()
    es_menor = "MENOR DE EDAD" in datos_completos_str

    if es_menor:
        c.setStrokeColorRGB(0.85, 0.15, 0.15)
        c.setLineWidth(2)
        c.rect(40, 45, 532, 725)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)
        y = texto_pdf(c, "ALERTA PROTECCIÓN: TRÁMITE DE MENOR DE EDAD DEBE VALIDAR OP-7", y, 10, True) - 4
    else:
        y = texto_pdf(c, "DOCUMENTO PRELIMINAR. REVISA, CORRIGE Y CONFIRMA TU INFORMACION.", y, 9, True) - 8

    p = r.get("perfil", {}) or {}
    y = seccion(c, "1. TUS DATOS", y)

    datos = [
        ("Nombre y apellidos", p.get("nombre_completo", "")),
        ("Fecha de nacimiento", p.get("fecha_nacimiento", "")),
        ("Edad", p.get("edad", "")),
        ("Dirección", p.get("direccion", "")),
        ("Estado", p.get("estado", "")),
        ("Código postal", p.get("codigo_postal", "")),
        ("Teléfono", p.get("telefono", "")),
        ("Trabajo / ocupación", p.get("trabajo") or p.get("ocupacion", ""))
    ]

    for i, (n, v) in enumerate(datos, 1):
        if editable: y = campo_pdf(c, n, v, y, i)
        elif v: y = texto_pdf(c, f"{n}: {v}", y)

    y -= 5
    y = seccion(c, "2. TU TRÁMITE", y)
    y = texto_pdf(c, r.get("nombre_tramite", ""), y, 11, True)

    bloques = [
        ("3. QUIÉN DEBE PRESENTARSE", r.get("personas")),
        ("4. REQUISITOS", r.get("requisitos")),
        ("5. DOCUMENTOS ORIGINALES", r.get("originales")),
        ("6. COPIAS", r.get("copias")),
        ("7. LO QUE YA TIENES", r.get("tienes")),
        ("8. LO QUE TE FALTA", r.get("faltantes")),
        ("9. LO QUE DEBES CONFIRMAR", r.get("confirmar") or r.get("revision")),
        ("10. ALERTAS REVISIÓN GENERAL Y OP-7", r.get("por_revisar")),
        ("11. INFORMACIÓN ESPECIAL", r.get("especial")),
        ("12. QUÉ DEBES HACER", r.get("acciones")),
        ("13. PAGO", r.get("pago")),
        ("14. CITA", r.get("cita")),
        ("15. VIGENCIA", r.get("vigencia")),
        ("16. ENTREGA", r.get("entrega"))
    ]

    for titulo, val in bloques:
        vals = lista_pdf(val)
        if not vals: continue
        y -= 5
        y = seccion(c, titulo, y)
        for v in vals: y = texto_pdf(c, "• " + v, y)

    y -= 5
    y = seccion(c, "17. INFORMACIÓN OFICIAL Y DE DEMARCACIÓN", y)
    y = texto_pdf(c, r.get("fuente", ""), y, 8)

    contacto = r.get("contacto", {}) or {}
    if isinstance(contacto, dict):
        for k, v in contacto.items():
            if v: y = texto_pdf(c, f"{k}: {v}", y, 8)

    y -= 5
    y = texto_pdf(
        c,
        "IMPORTANTE: MEXICANO APOYA MEXICANO NO ES EL GOBIERNO DE MEXICO. "
        "ESTA HOJA ES UNA HERRAMIENTA DE PREPARACION. "
        "CONFIRMA SIEMPRE LOS REQUISITOS VIGENTES CON EL CONSULADO CORRESPONDIENTE.",
        y, 7
    )

    if y < 55: c.showPage(); y = 750
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(.4, .4, .4)
    c.drawString(55, 38, "DOCUMENTO DE PREPARACION — MEXICANO APOYA MEXICANO")
    c.save()
    out.seek(0)
    return out

def extraer_pdf(data):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        partes = []
        for pagina in reader.pages:
            try: t = pagina.extract_text() or ""
            except: t = ""
            if t.strip(): partes.append(t.strip())
        return "\n\n".join(partes).strip()
    except:
        raise HTTPException(400, "No fue posible leer el PDF. Verifica que el archivo tenga texto.")

@app.get("/")
def home(): return FileResponse("static/index.html")

@app.get("/api/estado")
def estado(): return {"app": APP, "version": VERSION, "ok": True}

@app.get("/health")
def health(): return {"status": "ok", "app": APP, "version": VERSION}

@app.get("/api/catalogo")
def api_catalogo(): return catalogo()

@app.get("/api/fuentes")
def api_fuentes(): return obtener_fuentes()

@app.get("/api/contacto")
def api_contacto(): return obtener_contacto()

@app.get("/api/tarifas")
def api_tarifas(): return obtener_tarifas()

@app.get("/api/manual")
def api_manual(): return obtener_manual()

@app.post("/api/iniciar")
def api_iniciar(x: Inicio):
    try: return iniciar(x.texto, x.perfil)
    except Exception as e: raise HTTPException(400, str(e))

@app.post("/api/start")
def api_start(x: Inicio): return api_iniciar(x)

@app.post("/api/interpretar")
def api_interpretar(x: Interpretacion):
    try: return interpretar(x.caso, x.texto, x.respuestas, x.perfil)
    except Exception as e: raise HTTPException(400, str(e))

@app.post("/api/seleccionar-caso")
def api_seleccionar(x: Seleccion):
    try: return seleccionar_caso(x.caso, x.perfil, x.respuestas)
    except Exception as e: raise HTTPException(400, str(e))

@app.post("/api/seleccionar_caso")
def api_seleccionar_2(x: Seleccion): return api_seleccionar(x)

@app.post("/api/continuar")
def api_continuar(x: Continuacion):
    try:
        res = dict(x.respuestas or {})
        perfil = dict(x.perfil or {})
        respuesta = x.respuesta
        if respuesta in ("", None): respuesta = x.texto
        if x.texto: res["_texto_actual"] = x.texto
        return continuar(x.caso, res, perfil, x.pregunta_id, respuesta)
    except Exception as e: raise HTTPException(400, str(e))

@app.post("/api/resultado")
def api_resultado(x: ResultadoRequest):
    try: return resultado(x.caso, x.respuestas, x.perfil)
    except Exception as e: raise HTTPException(400, str(e))

@app.get("/api/tramite/{caso}")
def api_tramite(caso: str):
    c = caso_info(caso)
    if not c: raise HTTPException(404, "Trámite no disponible.")
    return tramite_oficial(caso)

@app.get("/api/caso/{caso}")
def api_caso(caso: str):
    c = caso_info(caso)
    if not c: raise HTTPException(404, "Trámite no disponible.")
    return c

@app.post("/api/procesar")
def api_procesar(data: Dict[str, Any]):
    try:
        return engine.procesar(data.get("caso", ""), data.get("respuestas", {}), data.get("perfil", {}))
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/documento")
async def api_documento(file: UploadFile = File(...)):
    nombre = file.filename or "documento.pdf"
    if not nombre.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo puedes subir archivos PDF.")
    
    data = await file.read()
    if not data:
        raise HTTPException(400, "El PDF está vacío.")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "El PDF no puede superar 15 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "El archivo no parece ser un PDF válido.")
    
    texto = extraer_pdf(data)
    return {
        "ok": True,
        "nombre": nombre,
        "tamano": len(data),
        "texto": texto,
        "tiene_texto": bool(texto),
        "mensaje": "PDF leído correctamente. Revisa la información antes de utilizarla." if texto else "El PDF no contiene texto extraíble."
    }

def obtener_resultado(x):
    r = engine.resultado(x.caso, x.respuestas, x.perfil)
    if not isinstance(r, dict):
        raise HTTPException(400, "El resultado del trámite no tiene un formato válido.")
    return r

@app.post("/api/pdf-preview")
def api_pdf_preview(x: ResultadoRequest):
    try:
        r = obtener_resultado(x)
        pdf = construir_pdf(r, True)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="Hoja_de_Ruta_PRELIMINAR.pdf"',
                "Cache-Control": "no-store"
            }
        )
    except Exception as e:
        raise HTTPException(400, f"No se pudo preparar la vista previa: {e}")

@app.post("/api/pdf")
def api_pdf(x: ResultadoRequest):
    try:
        r = obtener_resultado(x)
        pdf = construir_pdf(r, True)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="Hoja_de_Ruta_EDITABLE.pdf"',
                "Cache-Control": "no-store"
            }
        )
    except Exception as e:
        raise HTTPException(400, f"No se pudo generar el PDF: {e}")

@app.post("/api/generar-pdf")
def api_generar_pdf(x: ResultadoRequest):
    return api_pdf(x)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False
    )
