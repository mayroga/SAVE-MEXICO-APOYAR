import os,io,html
from copy import deepcopy
from fastapi import FastAPI,HTTPException
from fastapi.responses import JSONResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from consular_engine import (
    iniciar,interpretar,continuar,seleccionar_caso,
    resultado,pantalla_resultado,obtener_catalogo,
    obtener_fuentes,obtener_contacto,obtener_tarifas,
    obtener_manual
)

APP="MEXICANO APOYA MEXICANO"
VERSION="3.0.0"

app=FastAPI(title=APP,version=VERSION)

app.mount("/static",StaticFiles(directory="static"),name="static")

# ============================================================
# MODELOS
# ============================================================

class Inicio(BaseModel):
    servicio:str=""
    respuestas:dict=Field(default_factory=dict)
    texto:str=""

class Interpretacion(BaseModel):
    servicio:str=""
    caso:str=""
    pregunta_id:str=""
    texto:str=""
    respuestas:dict=Field(default_factory=dict)
    perfil:dict=Field(default_factory=dict)

class Continuacion(BaseModel):
    servicio:str=""
    caso:str=""
    pregunta_id:str=""
    texto:str=""
    respuestas:dict=Field(default_factory=dict)
    perfil:dict=Field(default_factory=dict)

class Seleccion(BaseModel):
    servicio:str=""
    caso:str=""
    respuestas:dict=Field(default_factory=dict)
    perfil:dict=Field(default_factory=dict)

class ResultadoRequest(BaseModel):
    servicio:str=""
    caso:str=""
    respuestas:dict=Field(default_factory=dict)
    perfil:dict=Field(default_factory=dict)

# ============================================================
# UTILIDADES
# ============================================================

def limpio(v):
    return str(v or "").strip()

def lista(v):
    if not v:return []
    if isinstance(v,list):return [limpio(x) for x in v if limpio(x)]
    return [limpio(v)]

def esc(v):
    return html.escape(limpio(v))

def fila(label,value):
    return [Paragraph(f"<b>{esc(label)}</b>",S["small"]),
            Paragraph(esc(value),S["small"])]

def seccion(story,titulo):
    story.append(Spacer(1,10))
    story.append(Paragraph(esc(titulo),S["h2"]))
    story.append(Spacer(1,4))

def lista_pdf(story,valores):
    vals=lista(valores)
    if not vals:
        story.append(Paragraph("PENDIENTE DE COMPLETAR",S["muted"]))
        return
    for x in vals:
        story.append(Paragraph("• "+esc(x),S["body"]))
        story.append(Spacer(1,3))

# ============================================================
# ESTILOS PDF
# ============================================================

styles=getSampleStyleSheet()

S={
    "title":ParagraphStyle(
        "TitleMX",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=12
    ),
    "sub":ParagraphStyle(
        "SubMX",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12
    ),
    "h2":ParagraphStyle(
        "H2MX",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#17324d"),
        spaceBefore=5,
        spaceAfter=7
    ),
    "h3":ParagraphStyle(
        "H3MX",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#222222"),
        spaceBefore=5,
        spaceAfter=4
    ),
    "body":ParagraphStyle(
        "BodyMX",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        spaceAfter=4
    ),
    "small":ParagraphStyle(
        "SmallMX",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11
    ),
    "muted":ParagraphStyle(
        "MutedMX",
        parent=styles["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#666666"),
        spaceAfter=5
    ),
    "estado":ParagraphStyle(
        "EstadoMX",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=9
    )
}

# ============================================================
# PDF
# ============================================================

def construir_pdf(data):
    b=io.BytesIO()

    doc=SimpleDocTemplate(
        b,
        pagesize=LETTER,
        rightMargin=42,
        leftMargin=42,
        topMargin=40,
        bottomMargin=42,
        title="Hoja de Ruta - MEXICANO APOYA MEXICANO",
        author=APP
    )

    story=[]

    caso=limpio(data.get("caso_nombre") or data.get("caso"))
    estado=data.get("estado") or {}
    codigo=limpio(
        data.get("estado_codigo") or
        estado.get("codigo")
    )

    story.append(
        Paragraph(
            "MEXICANO APOYA MEXICANO",
            S["title"]
        )
    )

    story.append(
        Paragraph(
            "HOJA DE RUTA PERSONAL DE TU TRÁMITE",
            S["title"]
        )
    )

    story.append(
        Paragraph(
            "Preparación previa para ayudarte a evitar "
            "un viaje innecesario, gastos o pérdida de tiempo.",
            S["sub"]
        )
    )

    # ESTADO
    if codigo=="rojo":
        color="#9b2424"
        titulo="ATENCIÓN: TODAVÍA NO VAYAS"
    elif codigo=="amarillo":
        color="#8a6500"
        titulo="TE FALTA CONFIRMAR ALGO"
    else:
        color="#126b42"
        titulo="PARECES LISTO"

    story.append(
        Paragraph(
            f'<font color="{color}">{esc(titulo)}</font>',
            S["estado"]
        )
    )

    if data.get("mensaje"):
        story.append(
            Paragraph(
                esc(data["mensaje"]),
                S["body"]
            )
        )

    # DATOS PERSONALES
    seccion(story,"1. DATOS PERSONALES")

    datos=data.get("datos_personales") or []

    if datos:
        tabla=Table(
            [fila(a,b) for a,b in datos],
            colWidths=[145,350]
        )
        tabla.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cccccc")),
            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f1f4f7")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),7),
            ("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6)
        ]))
        story.append(tabla)

    # TRÁMITE
    seccion(story,"2. TU TRÁMITE")

    story.append(
        Paragraph(
            f"<b>Trámite:</b> {esc(caso)}",
            S["body"]
        )
    )

    if data.get("descripcion"):
        story.append(
            Paragraph(
                esc(data["descripcion"]),
                S["body"]
            )
        )

    # PERSONAS
    seccion(story,"3. PERSONAS QUE DEBEN PRESENTARSE")
    lista_pdf(story,data.get("personas"))

    # REQUISITOS
    seccion(story,"4. REQUISITOS OBLIGATORIOS")
    lista_pdf(story,data.get("obligatorios"))

    # MENOR
    menor=data.get("datos_menor") or []

    if menor:
        seccion(story,"5. INFORMACIÓN DEL MENOR")

        tabla=Table(
            [fila(a,b) for a,b in menor],
            colWidths=[145,350]
        )

        tabla.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cccccc")),
            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f1f4f7")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),7),
            ("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6)
        ]))

        story.append(tabla)

    # PADRE / MADRE / TUTOR
    pmt=data.get("datos_padre_madre_tutor") or []

    if pmt:
        seccion(story,"6. PADRE, MADRE O TUTOR")

        tabla=Table(
            [fila(a,b) for a,b in pmt],
            colWidths=[145,350]
        )

        tabla.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cccccc")),
            ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f1f4f7")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),7),
            ("RIGHTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6)
        ]))

        story.append(tabla)

    # TIENE
    seccion(story,"7. LO QUE YA TIENES")

    tiene=data.get("tiene") or []

    if tiene:
        lista_pdf(story,tiene)
    else:
        story.append(
            Paragraph(
                "No se registró todavía un documento como disponible.",
                S["muted"]
            )
        )

    # FALTA
    seccion(story,"8. LO QUE TE FALTA")

    falta=data.get("falta") or []

    if falta:
        lista_pdf(story,falta)
    else:
        story.append(
            Paragraph(
                "No aparece un requisito faltante con las respuestas proporcionadas.",
                S["body"]
            )
        )

    # CONFIRMAR
    seccion(story,"9. LO QUE DEBES CONFIRMAR")

    confirmar=data.get("confirmar") or []

    if confirmar:
        lista_pdf(story,confirmar)
    else:
        story.append(
            Paragraph(
                "No aparece información pendiente de confirmación.",
                S["body"]
            )
        )

    # QUÉ HACER
    seccion(story,"10. ¿QUÉ DEBES HACER?")

    instrucciones=data.get("instrucciones") or []

    if instrucciones:
        lista_pdf(story,instrucciones)
    else:
        acciones=data.get("acciones") or []

        for a in acciones:
            titulo=limpio(a.get("titulo"))
            txt=limpio(a.get("texto"))

            if titulo:
                story.append(
                    Paragraph(
                        f"<b>{esc(titulo)}</b>",
                        S["body"]
                    )
                )

            if txt:
                story.append(
                    Paragraph(
                        esc(txt),
                        S["body"]
                    )
                )

    # CITA
    cita=data.get("cita") or {}

    if cita:
        seccion(story,"11. CITA")

        if cita.get("necesaria"):
            story.append(
                Paragraph(
                    "<b>Este trámite requiere cita según la información del caso.</b>",
                    S["body"]
                )
            )

            if cita.get("telefono"):
                story.append(
                    Paragraph(
                        f"<b>Teléfono:</b> {esc(cita['telefono'])}",
                        S["body"]
                    )
                )

            if cita.get("url"):
                story.append(
                    Paragraph(
                        f"<b>Sitio:</b> {esc(cita['url'])}",
                        S["body"]
                    )
                )
        else:
            story.append(
                Paragraph(
                    "La necesidad de cita depende del procedimiento seleccionado.",
                    S["body"]
                )
            )

    # ORIGINALES
    seccion(story,"12. DOCUMENTOS ORIGINALES")
    lista_pdf(
        story,
        data.get("documentos_originales")
    )

    # COPIAS
    seccion(story,"13. COPIAS")

    copias=data.get("copias") or []

    if copias:
        lista_pdf(story,copias)
    else:
        story.append(
            Paragraph(
                "No se agregan copias generales. Lleva copias únicamente "
                "cuando el procedimiento oficial las solicite.",
                S["body"]
            )
        )

    # PAGO
    seccion(story,"14. PAGO")

    pago=data.get("pago") or {}

    if pago:
        if pago.get("necesario"):
            story.append(
                Paragraph(
                    "<b>Puede existir un pago para este trámite.</b>",
                    S["body"]
                )
            )

            if pago.get("cantidad"):
                story.append(
                    Paragraph(
                        f"<b>Referencia:</b> {esc(pago['cantidad'])}",
                        S["body"]
                    )
                )

        story.append(
            Paragraph(
                esc(
                    pago.get(
                        "mensaje",
                        "Confirma la tarifa vigente."
                    )
                ),
                S["body"]
            )
        )

    # ANTES DE FIRMAR
    seccion(story,"15. ANTES DE FIRMAR O IMPRIMIR")

    story.append(
        Paragraph(
            "Revisa cuidadosamente nombres, apellidos, fechas, "
            "datos personales y cualquier documento que el Consulado "
            "te presente antes de firmarlo o imprimirlo.",
            S["body"]
        )
    )

    # VIGENCIA
    vigencia=data.get("vigencia") or []

    if vigencia:
        seccion(story,"16. VIGENCIA")
        lista_pdf(story,vigencia)

    # ENTREGA
    entrega=data.get("entrega") or []

    if entrega:
        seccion(story,"17. ENTREGA")
        lista_pdf(story,entrega)

    # ESPECIALES
    especiales=data.get("especiales") or []

    if especiales:
        seccion(story,"18. INFORMACIÓN IMPORTANTE")
        lista_pdf(story,especiales)

    # FUENTE
    seccion(story,"19. INFORMACIÓN OFICIAL")

    fuente=limpio(data.get("fuente_oficial"))

    if fuente:
        story.append(
            Paragraph(
                f"<b>Fuente oficial:</b> {esc(fuente)}",
                S["body"]
            )
        )

    story.append(
        Spacer(1,12)
    )

    story.append(
        Paragraph(
            "IMPORTANTE: MEXICANO APOYA MEXICANO es una aplicación "
            "independiente. No es el Gobierno de México, no pertenece "
            "a la Secretaría de Relaciones Exteriores y no representa "
            "al Consulado de México. Los requisitos, tarifas, citas, "
            "horarios y procedimientos pueden cambiar. Antes de acudir, "
            "confirma siempre la información directamente con la fuente oficial.",
            S["muted"]
        )
    )

    doc.build(story)
    b.seek(0)
    return b

# ============================================================
# RUTAS
# ============================================================

@app.get("/")
def inicio_web():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
    return {
        "ok":True,
        "app":APP,
        "version":VERSION,
        "motor":"determinístico",
        "ia":False
    }

@app.get("/api/catalogo")
def api_catalogo():
    return JSONResponse(
        content=obtener_catalogo()
    )

@app.get("/api/fuentes")
def api_fuentes():
    return JSONResponse(
        content=obtener_fuentes()
    )

@app.get("/api/contacto")
def api_contacto():
    return JSONResponse(
        content=obtener_contacto()
    )

@app.get("/api/tarifas")
def api_tarifas():
    return JSONResponse(
        content=obtener_tarifas()
    )

@app.get("/api/manual")
def api_manual():
    return JSONResponse(
        content=obtener_manual()
    )

# ============================================================
# INICIAR
# ============================================================

@app.post("/api/iniciar")
def api_iniciar(data:Inicio):
    try:
        r=iniciar(
            data.servicio,
            data.respuestas,
            data.texto
        )
        return JSONResponse(content=r)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al iniciar: {e}"
        )

# Alias para compatibilidad
@app.post("/api/start")
def api_start(data:Inicio):
    return api_iniciar(data)

# ============================================================
# INTERPRETAR TEXTO
# ============================================================

@app.post("/api/interpretar")
def api_interpretar(data:Interpretacion):
    try:
        r=interpretar(
            data.servicio,
            data.caso,
            data.pregunta_id,
            data.texto,
            data.respuestas,
            data.perfil
        )
        return JSONResponse(content=r)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al interpretar: {e}"
        )

# ============================================================
# CONTINUAR
# ============================================================

@app.post("/api/continuar")
def api_continuar(data:Continuacion):
    try:
        r=continuar(
            data.servicio,
            data.caso,
            data.pregunta_id,
            data.texto,
            data.respuestas,
            data.perfil
        )
        return JSONResponse(content=r)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al continuar: {e}"
        )

# ============================================================
# SELECCIONAR CASO
# ============================================================

@app.post("/api/seleccionar-caso")
def api_seleccionar(data:Seleccion):
    try:
        r=seleccionar_caso(
            data.servicio,
            data.caso,
            data.respuestas,
            data.perfil
        )
        return JSONResponse(content=r)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al seleccionar el caso: {e}"
        )

@app.post("/api/seleccionar_caso")
def api_seleccionar_alias(data:Seleccion):
    return api_seleccionar(data)

# ============================================================
# RESULTADO
# ============================================================

@app.post("/api/resultado")
def api_resultado(data:ResultadoRequest):
    try:
        r=pantalla_resultado(
            data.servicio,
            data.caso,
            data.respuestas,
            data.perfil
        )
        return JSONResponse(content=r)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear resultado: {e}"
        )

# ============================================================
# PDF
# ============================================================

@app.post("/api/pdf")
def api_pdf(data:ResultadoRequest):
    try:
        r=pantalla_resultado(
            data.servicio,
            data.caso,
            data.respuestas,
            data.perfil
        )

        if r.get("tipo")=="error":
            raise HTTPException(
                status_code=400,
                detail=r.get("error","Caso inválido")
            )

        pdf=construir_pdf(r)

        nombre="hoja_de_ruta_mexicano_apoya_mexicano.pdf"

        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                f'attachment; filename="{nombre}"'
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar PDF: {e}"
        )

# Alias
@app.post("/api/generar-pdf")
def api_generar_pdf(data:ResultadoRequest):
    return api_pdf(data)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status":"ok",
        "app":APP,
        "version":VERSION
    }

# ============================================================
# EJECUCIÓN LOCAL
# ============================================================

if __name__=="__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT","8000")),
        reload=False
    )
