import os,io
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from typing import Any,Dict,Optional
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from consular_engine import iniciar,seleccionar_caso,continuar,interpretar,obtener_caso,FUENTES,catalogo

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="3.2.0")
app.mount("/static",StaticFiles(directory="static"),name="static")

class Respuesta(BaseModel):
 servicio:Optional[str]=""
 caso:Optional[str]=""
 pregunta_id:Optional[str]=""
 texto:Optional[str]=""
 respuestas:Dict[str,Any]=Field(default_factory=dict)
 resultado:Optional[Dict[str,Any]]=None

@app.get("/")
def home():
 return FileResponse("static/index.html")

@app.get("/api/estado")
def estado():
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","version":"3.2.0"}

@app.get("/api/casos")
def casos(servicio:Optional[str]=None):
 return {"estado":"seleccionar","tipo":"catalogo","servicio":servicio or "todos","opciones":catalogo(servicio)}

@app.get("/api/inicio/{servicio}")
def inicio(servicio:str):
 if servicio not in ("cita","documento"):
  raise HTTPException(400,"Servicio no válido.")
 return iniciar(servicio)

@app.post("/api/iniciar")
def api_iniciar(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  raise HTTPException(400,"Falta seleccionar el tipo de servicio.")
 if data.caso:
  if not obtener_caso(data.caso):
   raise HTTPException(404,"Trámite no encontrado.")
  return seleccionar_caso(data.caso,data.respuestas or {})
 return iniciar(data.servicio,None,data.respuestas or {})

@app.post("/api/entender")
def entender(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  raise HTTPException(400,"Falta seleccionar el servicio.")
 return interpretar(data.servicio,data.texto or "",data.respuestas or {},data.pregunta_id or "")

@app.post("/api/responder")
def responder(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  raise HTTPException(400,"Falta seleccionar el servicio.")
 texto=(data.texto or "").strip()
 respuestas=dict(data.respuestas or {})
 if data.caso:
  if not obtener_caso(data.caso):
   raise HTTPException(404,"Trámite no encontrado.")
  if data.pregunta_id and texto:
   respuestas[data.pregunta_id]=texto
  return continuar(data.caso,respuestas,data.pregunta_id or "",texto)
 return interpretar(data.servicio,texto,respuestas,data.pregunta_id or "")

def esc(v):
 return str(v or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br/>")

def lista(items):
 return [str(x) for x in (items or []) if str(x).strip()]

def generar_pdf(r):
 buf=io.BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=LETTER,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("Titulo",parent=styles["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=4)
 h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=12,leading=15,spaceBefore=14,spaceAfter=7)
 body=ParagraphStyle("Body",parent=styles["BodyText"],fontSize=9.5,leading=13,spaceAfter=5)
 small=ParagraphStyle("Small",parent=styles["BodyText"],fontSize=8,leading=11)
 story=[]

 def H(t):
  story.append(Paragraph(esc(t),h))
  story.append(Spacer(1,3))

 def P(t):
  if t is not None and str(t).strip():
   story.append(Paragraph(esc(t),body))

 def L(items):
  for x in lista(items):
   P("• "+x)

 def T(rows):
  if not rows:return
  tabla=Table(rows,colWidths=[145,345],repeatRows=1)
  tabla.setStyle(TableStyle([
   ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173452")),
   ("TEXTCOLOR",(0,0),(-1,0),colors.white),
   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
   ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
   ("FONTSIZE",(0,0),(-1,-1),9),
   ("LEADING",(0,0),(-1,-1),12),
   ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#b7c1cb")),
   ("VALIGN",(0,0),(-1,-1),"TOP"),
   ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f7f9fb")]),
   ("LEFTPADDING",(0,0),(-1,-1),7),
   ("RIGHTPADDING",(0,0),(-1,-1),7),
   ("TOPPADDING",(0,0),(-1,-1),6),
   ("BOTTOMPADDING",(0,0),(-1,-1),6)
  ]))
  story.append(tabla)
  story.append(Spacer(1,8))

 nivel=r.get("nivel","amarillo")
 estado=r.get("estado_texto","TE FALTA ALGO")
 perfil=r.get("perfil") or {}
 docs=r.get("documentos") or []
 tiene=[x.get("nombre") for x in docs if x.get("estado")=="tiene"]
 falta=[x.get("nombre") for x in docs if x.get("estado")=="falta"]
 revisar=[x.get("nombre") for x in docs if x.get("estado")=="revisar"]

 story.append(Paragraph("MEXICANO APOYA MEXICANO",titulo))
 story.append(Paragraph("HOJA DE RUTA PERSONAL DEL TRÁMITE",titulo))
 story.append(Spacer(1,10))

 color="#9b2424" if nivel=="rojo" else "#8a6500" if nivel=="amarillo" else "#087f3e"
 estado_style=ParagraphStyle("Estado",parent=styles["BodyText"],fontSize=12,leading=16,alignment=TA_CENTER,textColor=colors.HexColor(color),spaceAfter=8)
 story.append(Paragraph("<b>"+esc(estado)+"</b>",estado_style))

 H("1. DATOS PERSONALES")
 filas=[["DATO","INFORMACIÓN"]]
 campos=[
  ("Nombre",perfil.get("nombre")),
  ("Nacionalidad",perfil.get("nacionalidad")),
  ("Teléfono",perfil.get("telefono")),
  ("Dirección",perfil.get("direccion")),
  ("Estado",perfil.get("estado")),
  ("ZIP",perfil.get("zip") or perfil.get("codigo_postal")),
  ("Correo",perfil.get("email") or perfil.get("correo"))
 ]
 for nombre,valor in campos:
  filas.append([nombre,valor or "PENDIENTE DE COMPLETAR"])
 T(filas)

 H("2. TRÁMITE")
 P(r.get("tramite") or r.get("titulo") or "PENDIENTE DE COMPLETAR")

 personas=r.get("personas_obligatorias") or []
 if personas:
  H("3. PERSONAS QUE DEBEN PRESENTARSE")
  L(personas)

 H("4. REQUISITOS OBLIGATORIOS")
 L(r.get("requisitos_obligatorios") or ["PENDIENTE DE COMPLETAR"])

 H("5. LO QUE YA TIENES")
 L(tiene or ["No se registró todavía un documento como disponible."])

 H("6. LO QUE TE FALTA")
 L(falta or ["PENDIENTE DE COMPLETAR"])

 H("7. LO QUE DEBES CONFIRMAR")
 L(revisar)
 L(r.get("especiales"))

 H("8. ¿QUÉ DEBES HACER?")
 P(r.get("prepara") or "PENDIENTE DE COMPLETAR")

 H("9. CITA")
 L(r.get("cita") or ["Confirma la necesidad de cita y conserva la confirmación correspondiente."])

 H("10. DOCUMENTOS ORIGINALES")
 L(r.get("originales") or ["Presenta los documentos ORIGINALES que correspondan a tu caso."])

 copias=r.get("copias") or []
 if copias:
  H("11. COPIAS")
  L(copias)

 H("12. PAGO")
 P(r.get("pago") or "Confirma la tarifa y forma de pago vigente.")

 H("13. ANTES DE FIRMAR O IMPRIMIR")
 P(r.get("revision") or "Revisa cuidadosamente todos los datos antes de firmar o imprimir.")

 if r.get("vigencia"):
  H("14. VIGENCIA")
  P(r.get("vigencia"))

 if r.get("entrega"):
  H("15. ENTREGA")
  P(r.get("entrega"))

 H("16. INFORMACIÓN IMPORTANTE")
 L(r.get("importante"))
 if r.get("confirma"):
  P(r.get("confirma"))

 H("INFORMACIÓN OFICIAL")
 P(r.get("fuente") or r.get("fuente_oficial") or FUENTES.get("tarifas",""))

 story.append(Spacer(1,10))
 story.append(Paragraph(
  "Esta Hoja de Ruta se basa en la información proporcionada durante la consulta y no sustituye la revisión de la autoridad consular. MEXICANO APOYA MEXICANO es una aplicación independiente y no es el Gobierno de México ni representa a ningún Consulado.",
  small
 ))

 doc.build(story)
 buf.seek(0)
 return buf

@app.post("/api/pdf")
def pdf(data:Respuesta):
 r=data.resultado
 if not r and data.caso:
  if not obtener_caso(data.caso):
   raise HTTPException(404,"Trámite no encontrado.")
  r=continuar(data.caso,data.respuestas or {})
 if not r:
  raise HTTPException(400,"Primero termina la consulta.")
 if r.get("tipo")!="resultado":
  raise HTTPException(400,"La consulta todavía no está terminada.")
 try:
  archivo=generar_pdf(r)
 except Exception as e:
  raise HTTPException(500,f"No se pudo generar el PDF: {e}")
 return StreamingResponse(
  archivo,
  media_type="application/pdf",
  headers={"Content-Disposition":"attachment; filename=Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf"}
 )

if __name__=="__main__":
 import uvicorn
 uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
