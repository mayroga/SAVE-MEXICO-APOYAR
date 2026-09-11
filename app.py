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
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from consular_engine import iniciar,seleccionar_caso,continuar,interpretar,obtener_caso,FUENTES,catalogo

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="3.3.0")
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
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","version":"3.3.0"}

@app.get("/api/casos")
def casos(servicio:Optional[str]=None):
 return {"tipo":"catalogo","estado":"seleccionar","servicio":servicio or "todos","opciones":catalogo(servicio)}

@app.get("/api/inicio/{servicio}")
def inicio(servicio:str):
 if servicio not in ("cita","documento"):
  raise HTTPException(400,"Servicio no válido.")
 return iniciar(servicio,{})

@app.post("/api/iniciar")
def api_iniciar(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  raise HTTPException(400,"Falta seleccionar el tipo de servicio.")
 if data.caso:
  if not obtener_caso(data.caso):
   raise HTTPException(404,"Trámite no encontrado.")
  return seleccionar_caso(data.caso,data.respuestas or {})
 return iniciar(data.servicio,data.respuestas or {})

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

def limpio(v):
 return str(v or "").strip()

def lista(items):
 return [limpio(x) for x in (items or []) if limpio(x)]

def ptexto(v):
 return "PENDIENTE DE COMPLETAR" if not limpio(v) else limpio(v)

def generar_pdf(r):
 buf=io.BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=LETTER,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42,title="Hoja de Ruta - Mexicano Apoya Mexicano",author="MEXICANO APOYA MEXICANO")
 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("Titulo",parent=styles["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=5,textColor=colors.HexColor("#173452"))
 subtitulo=ParagraphStyle("Sub",parent=styles["BodyText"],fontSize=10,leading=14,alignment=TA_CENTER,spaceAfter=10,textColor=colors.HexColor("#4d5965"))
 h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=12,leading=15,spaceBefore=13,spaceAfter=7,textColor=colors.HexColor("#173452"))
 h3=ParagraphStyle("H3",parent=styles["Heading3"],fontSize=10.5,leading=13,spaceBefore=9,spaceAfter=5,textColor=colors.HexColor("#173452"))
 body=ParagraphStyle("Body",parent=styles["BodyText"],fontSize=9.5,leading=13,spaceAfter=5)
 small=ParagraphStyle("Small",parent=styles["BodyText"],fontSize=7.7,leading=10,textColor=colors.HexColor("#555f68"))
 estado=ParagraphStyle("Estado",parent=styles["BodyText"],fontSize=13,leading=17,alignment=TA_CENTER,spaceBefore=5,spaceAfter=12)
 story=[]

 def H(t):
  story.append(Paragraph(esc(t),h))

 def H3(t):
  story.append(Paragraph(esc(t),h3))

 def P(t):
  if limpio(t):story.append(Paragraph(esc(t),body))

 def L(items):
  for x in lista(items):P("• "+x)

 def tabla(rows,widths=(155,335)):
  if not rows:return
  t=Table(rows,colWidths=list(widths),repeatRows=1)
  t.setStyle(TableStyle([
   ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173452")),
   ("TEXTCOLOR",(0,0),(-1,0),colors.white),
   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
   ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
   ("FONTSIZE",(0,0),(-1,-1),9),
   ("LEADING",(0,0),(-1,-1),12),
   ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#b9c2ca")),
   ("VALIGN",(0,0),(-1,-1),"TOP"),
   ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f7f9fb")]),
   ("LEFTPADDING",(0,0),(-1,-1),7),
   ("RIGHTPADDING",(0,0),(-1,-1),7),
   ("TOPPADDING",(0,0),(-1,-1),6),
   ("BOTTOMPADDING",(0,0),(-1,-1),6)
  ]))
  story.append(t)
  story.append(Spacer(1,7))

 def bloque_persona(titulo_persona,datos):
  filas=[["DATO","INFORMACIÓN"]]
  for a,b in datos:
   filas.append([a,ptexto(b)])
  return [Paragraph(esc(titulo_persona),h3),Table(filas,colWidths=[155,335],repeatRows=1)]

 nivel=r.get("nivel","amarillo")
 estado_texto=r.get("estado_texto","TE FALTA ALGO")
 color="#087f3e" if nivel=="verde" else "#9b2424" if nivel=="rojo" else "#8a6500"
 estado.textColor=colors.HexColor(color)

 perfil=r.get("perfil") or {}
 respuestas=r.get("respuestas") or {}
 caso=r.get("caso","")
 docs=r.get("documentos") or []
 checklist=r.get("checklist") or {}

 tiene=[x.get("nombre") for x in docs if isinstance(x,dict) and x.get("estado")=="tiene"]
 falta=[x.get("nombre") for x in docs if isinstance(x,dict) and x.get("estado")=="falta"]
 revisar=[x.get("nombre") for x in docs if isinstance(x,dict) and x.get("estado")=="revisar"]

 story.append(Paragraph("MEXICANO APOYA MEXICANO",titulo))
 story.append(Paragraph("HOJA DE RUTA PERSONAL DEL TRÁMITE",titulo))
 story.append(Paragraph("Documento de preparación personal para revisar antes de acudir al Consulado.",subtitulo))
 story.append(Paragraph("<b>"+esc(estado_texto)+"</b>",estado))
 
 H("1. DATOS PERSONALES")
 campos=[
  ("Nombre",perfil.get("nombre")),
  ("Nacionalidad",perfil.get("nacionalidad")),
  ("Teléfono",perfil.get("telefono")),
  ("Dirección",perfil.get("direccion")),
  ("Estado",perfil.get("estado")),
  ("ZIP",perfil.get("zip") or perfil.get("codigo_postal")),
  ("Correo",perfil.get("email") or perfil.get("correo"))
 ]
 filas=[["DATO","INFORMACIÓN"]]+[[a,ptexto(b)] for a,b in campos]
 tabla(filas)

 H("2. TU TRÁMITE")
 P(r.get("tramite") or r.get("titulo") or caso or "PENDIENTE DE COMPLETAR")

 personas=r.get("personas_obligatorias") or []
 if personas:
  H("3. PERSONAS QUE DEBEN PRESENTARSE")
  L(personas)

 H("4. REQUISITOS OBLIGATORIOS")
 requisitos=lista(r.get("requisitos_obligatorios"))
 L(requisitos or ["PENDIENTE DE COMPLETAR"])

 if caso in ("pasaporte_menor","matricula_menor"):
  H("5. INFORMACIÓN DEL MENOR")
  menor_nombre=respuestas.get("menor_nombre") or perfil.get("nombre")
  menor_nac=respuestas.get("menor_nacionalidad")
  menor_id=respuestas.get("menor_identidad")
  tabla([
   ["DATO","INFORMACIÓN"],
   ["Nombre del menor",ptexto(menor_nombre)],
   ["Nacionalidad / documento",ptexto(menor_nac)],
   ["Identificación",ptexto(menor_id)]
  ])

  H("6. PADRE, MADRE O TUTOR")
  padre=respuestas.get("padre1")
  padre_id=respuestas.get("padre1_id")
  padre2=respuestas.get("padre2")
  autorizacion=respuestas.get("autorizacion") or respuestas.get("op7")
  tabla([
   ["DATO","INFORMACIÓN"],
   ["Nombre",ptexto(padre)],
   ["Identificación",ptexto(padre_id)],
   ["Otro padre/madre/tutor",ptexto(padre2)],
   ["Autorización",ptexto(autorizacion)]
  ])
  offset=2
 else:
  offset=0

 H(f"{7 if offset else 5}. LO QUE YA TIENES")
 L(tiene or ["No se registró todavía un documento como disponible."])

 H(f"{8 if offset else 6}. LO QUE TE FALTA")
 L(falta or ["No se identificó todavía un documento confirmado como faltante."])

 H(f"{9 if offset else 7}. LO QUE DEBES CONFIRMAR")
 L(revisar)
 L(r.get("especiales"))
 if not revisar and not r.get("especiales"):
  P("No hay un punto adicional marcado para confirmar con la información registrada.")

 H(f"{10 if offset else 8}. ¿QUÉ DEBES HACER?")
 P(r.get("prepara") or "Reúne los documentos indicados y confirma los puntos pendientes antes de acudir.")

 H(f"{11 if offset else 9}. CITA")
 L(r.get("cita") or ["Confirma la necesidad de cita y conserva la confirmación."])

 H(f"{12 if offset else 10}. DOCUMENTOS ORIGINALES")
 L(r.get("originales") or ["Presenta los documentos ORIGINALES que correspondan a tu caso."])

 H(f"{13 if offset else 11}. COPIAS")
 copias=lista(r.get("copias"))
 L(copias or ["No se identificaron copias obligatorias con la información disponible."])

 H(f"{14 if offset else 12}. PAGO")
 P(r.get("pago") or "Confirma la tarifa y forma de pago vigente antes de acudir.")

 H(f"{15 if offset else 13}. ANTES DE FIRMAR O IMPRIMIR")
 P(r.get("revision") or "Revisa cuidadosamente nombres, fechas y demás datos antes de firmar o imprimir.")

 if r.get("vigencia"):
  H(f"{16 if offset else 14}. VIGENCIA")
  P(r.get("vigencia"))

 if r.get("entrega"):
  H(f"{17 if offset else 15}. ENTREGA")
  P(r.get("entrega"))

 H(f"{18 if offset else 16}. INFORMACIÓN IMPORTANTE")
 importantes=lista(r.get("importante"))
 L(importantes)
 if r.get("confirma"):
  P(r.get("confirma"))

 H("INFORMACIÓN OFICIAL")
 fuente=r.get("fuente") or r.get("fuente_oficial") or FUENTES.get("tarifas","")
 P("Consulta siempre la fuente oficial antes de acudir:")
 P(fuente)

 story.append(Spacer(1,10))
 story.append(Paragraph(
  "NOTA: Esta Hoja de Ruta organiza la información proporcionada durante la consulta y la información oficial incorporada en la aplicación. No sustituye la revisión de la autoridad consular. MEXICANO APOYA MEXICANO es una aplicación independiente y no es el Gobierno de México ni representa a ningún Consulado.",
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
 return StreamingResponse(archivo,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=Hoja_de_Ruta_Mexicano_Apoya_Mexicano.pdf"})

if __name__=="__main__":
 import uvicorn
 uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
