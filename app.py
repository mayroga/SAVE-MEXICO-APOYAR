import io,html
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse,JSONResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from consular_engine import (
    iniciar,interpretar,continuar,seleccionar_caso,
    resultado,pantalla_resultado,obtener_catalogo,
    obtener_fuentes,obtener_contacto,obtener_tarifas,
    obtener_manual
)

APP="MEXICANO APOYA MEXICANO"
VERSION="4.0.0"

app=FastAPI(title=APP,version=VERSION)
app.mount("/static",StaticFiles(directory="static"),name="static")

class Inicio(BaseModel):
    texto:str=""
    servicio:str=""

class Interpretacion(BaseModel):
    texto:str=""
    servicio:str=""
    caso:str=""
    respuestas:dict={}
    perfil:dict={}

class Continuacion(BaseModel):
    servicio:str=""
    caso:str=""
    pregunta_id:str=""
    texto:str=""
    respuestas:dict={}
    perfil:dict={}

class Seleccion(BaseModel):
    servicio:str=""
    caso:str=""
    respuestas:dict={}
    perfil:dict={}

class ResultadoRequest(BaseModel):
    servicio:str=""
    caso:str=""
    respuestas:dict={}
    perfil:dict={}

def limpiar(v):
    if v is None:return ""
    return html.escape(str(v))

def lista_pdf(story,titulo,items,styles):
    if not items:return
    story.append(Paragraph(titulo,styles["H2"]))
    for x in items:
        story.append(Paragraph("• "+limpiar(x),styles["Body"]))
        story.append(Spacer(1,3))
    story.append(Spacer(1,7))

def datos_pdf(story,titulo,datos,styles):
    vals=[]
    for k,v in datos.items():
        if isinstance(v,(dict,list)):continue
        v=str(v or "").strip()
        if not v:v="PENDIENTE DE COMPLETAR"
        vals.append([limpiar(k),limpiar(v)])
    if not vals:return
    story.append(Paragraph(titulo,styles["H2"]))
    t=Table(vals,colWidths=[145,350],hAlign="LEFT")
    t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#cbd5e1")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef2f7")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",(1,0),(1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("LEFTPADDING",(0,0),(-1,-1),7),
        ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story.extend([t,Spacer(1,12)])

def construir_pdf(data):
    buf=io.BytesIO()
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TituloMAM",parent=styles["Title"],fontSize=17,
        leading=21,alignment=TA_CENTER,spaceAfter=14
    ))
    styles.add(ParagraphStyle(
        name="H2",parent=styles["Heading2"],fontSize=11,
        leading=14,spaceBefore=8,spaceAfter=6,textColor=colors.HexColor("#17324d")
    ))
    styles.add(ParagraphStyle(
        name="Body",parent=styles["BodyText"],fontSize=9.5,
        leading=13,spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="Small",parent=styles["BodyText"],fontSize=7.5,
        leading=10,textColor=colors.HexColor("#475569")
    ))

    doc=SimpleDocTemplate(
        buf,pagesize=LETTER,
        rightMargin=42,leftMargin=42,
        topMargin=40,bottomMargin=40
    )
    story=[]

    nombre=data.get("nombre_tramite","Trámite consular")
    estado=data.get("titulo","")
    story.append(Paragraph("MEXICANO APOYA MEXICANO",styles["TituloMAM"]))
    story.append(Paragraph(limpiar(nombre),styles["H2"]))
    story.append(Paragraph(
        "Hoja de Ruta / Checklist personal para preparar tu trámite antes de acudir.",
        styles["Body"]
    ))
    story.append(Spacer(1,8))

    if estado:
        story.append(Paragraph(limpiar(estado),styles["H2"]))
        story.append(Paragraph(limpiar(data.get("mensaje","")),styles["Body"]))
        story.append(Spacer(1,8))

    perfil=data.get("datos_personales") or data.get("perfil") or {}
    perfil_legible={
        "Nombre completo":perfil.get("nombre_completo"),
        "Nacionalidad":perfil.get("nacionalidad"),
        "Teléfono":perfil.get("telefono"),
        "Dirección":perfil.get("direccion"),
        "Estado":perfil.get("estado"),
        "ZIP Code":perfil.get("zip"),
        "Correo electrónico":perfil.get("email")
    }
    datos_pdf(story,"1. DATOS PERSONALES",perfil_legible,styles)

    datos_pdf(story,"2. TU TRÁMITE",{
        "Trámite":data.get("nombre_tramite"),
        "Descripción":data.get("descripcion")
    },styles)

    lista_pdf(story,"3. PERSONAS QUE DEBEN PRESENTARSE",
              data.get("personas",[]),styles)

    lista_pdf(story,"4. REQUISITOS OBLIGATORIOS",
              data.get("requisitos",[]),styles)

    if data.get("originales"):
        lista_pdf(story,"5. DOCUMENTOS ORIGINALES",
                  data["originales"],styles)

    if data.get("copias"):
        lista_pdf(story,"6. COPIAS",
                  data["copias"],styles)

    if data.get("faltan"):
        lista_pdf(story,"7. LO QUE TE FALTA",
                  data["faltan"],styles)

    if data.get("confirmar"):
        lista_pdf(story,"8. LO QUE DEBES CONFIRMAR",
                  data["confirmar"],styles)

    if data.get("pago"):
        lista_pdf(story,"9. PAGO", [data["pago"]],styles)

    if data.get("cita"):
        lista_pdf(story,"10. CITA",[data["cita"]],styles)

    if data.get("vigencia"):
        lista_pdf(story,"11. VIGENCIA",[data["vigencia"]],styles)

    if data.get("entrega"):
        lista_pdf(story,"12. ENTREGA",[data["entrega"]],styles)

    if data.get("especiales"):
        lista_pdf(story,"13. INFORMACIÓN ESPECIAL",
                  data["especiales"],styles)

    if data.get("acciones"):
        lista_pdf(story,"14. ¿QUÉ DEBES HACER?",
                  data["acciones"],styles)

    story.append(Paragraph("15. INFORMACIÓN OFICIAL",styles["H2"]))
    story.append(Paragraph(
        limpiar(data.get("fuente_oficial") or data.get("fuente") or ""),
        styles["Body"]
    ))
    story.append(Spacer(1,7))

    contacto=data.get("contacto") or {}
    lista_pdf(story,"16. CONTACTO",[
        "Teléfono de citas/documentos: "+str(contacto.get("telefono","")),
        "Conmutador: "+str(contacto.get("conmutador","")),
        "Dirección de referencia: "+str(contacto.get("direccion",""))
    ],styles)

    story.append(Spacer(1,10))
    story.append(Paragraph(
        "IMPORTANTE: esta aplicación ayuda a preparar la visita. "
        "No es el Gobierno de México ni sustituye las instrucciones "
        "del consulado. Los requisitos, tarifas, citas y disponibilidad "
        "pueden cambiar. Confirma siempre la información oficial del "
        "consulado que atiende tu lugar de residencia.",
        styles["Small"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf

@app.get("/",response_class=HTMLResponse)
def inicio():
    try:
        with open("static/index.html","r",encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>MEXICANO APOYA MEXICANO</h1><p>Archivo de aplicación no encontrado.</p>"

@app.get("/api/estado")
def estado():
    return {
        "ok":True,
        "app":APP,
        "version":VERSION,
        "ia":False,
        "tramites":6,
        "mensaje":"Sistema disponible"
    }

@app.get("/health")
def health():
    return {"ok":True,"app":APP,"version":VERSION}

@app.get("/api/catalogo")
def catalogo():
    return {
        "ok":True,
        "tramites":obtener_catalogo()
    }

@app.get("/api/fuentes")
def fuentes():
    return {
        "ok":True,
        "fuentes":obtener_fuentes()
    }

@app.get("/api/contacto")
def contacto():
    return {
        "ok":True,
        "contacto":obtener_contacto()
    }

@app.get("/api/tarifas")
def tarifas():
    return {
        "ok":True,
        "tarifas":obtener_tarifas()
    }

@app.get("/api/manual")
def manual():
    return {
        "ok":True,
        "manual":obtener_manual()
    }

@app.post("/api/iniciar")
@app.post("/api/start")
def api_iniciar(x:Inicio):
    return iniciar(x.texto,x.servicio)

@app.post("/api/interpretar")
def api_interpretar(x:Interpretacion):
    return interpretar(
        x.servicio,x.texto,x.caso,
        x.respuestas,x.perfil
    )

@app.post("/api/continuar")
def api_continuar(x:Continuacion):
    return continuar(
        x.servicio,
        x.caso,
        x.pregunta_id,
        x.texto,
        x.respuestas,
        x.perfil
    )

@app.post("/api/seleccionar-caso")
@app.post("/api/seleccionar_caso")
def api_seleccionar(x:Seleccion):
    return seleccionar_caso(
        x.servicio,
        x.caso,
        x.perfil,
        x.respuestas
    )

@app.post("/api/resultado")
def api_resultado(x:ResultadoRequest):
    if not x.caso:
        raise HTTPException(400,"Falta el trámite.")
    return resultado(
        x.servicio,
        x.caso,
        x.respuestas,
        x.perfil
    )

@app.post("/api/pdf")
@app.post("/api/generar-pdf")
def api_pdf(x:ResultadoRequest):
    if not x.caso:
        raise HTTPException(400,"Falta el trámite.")
    data=resultado(
        x.servicio,
        x.caso,
        x.respuestas,
        x.perfil
    )
    if data.get("tipo")!="resultado":
        raise HTTPException(400,"No se pudo preparar el resultado.")
    pdf=construir_pdf(data)
    nombre=x.caso.replace("_","-")+".pdf"
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":f'attachment; filename="{nombre}"'
        }
    )

@app.get("/api/tramite/{caso}")
def api_tramite(caso:str):
    catalogo=obtener_catalogo()
    for x in catalogo:
        if x.get("id")==caso:
            return {"ok":True,"tramite":x}
    raise HTTPException(404,"Trámite no disponible.")

if __name__=="__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
