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

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="4.0.0")
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
 return {"ok":True,"app":"MEXICANO APOYA MEXICANO","version":"4.0.0"}

@app.get("/api/casos")
def casos(servicio:Optional[str]=None):
 return {"tipo":"catalogo","estado":"seleccionar","servicio":servicio or "todos","opciones":catalogo(servicio)}

@app.get("/api/inicio/{servicio}")
def inicio(servicio:str):
 if servicio not in ("cita","documento"):raise HTTPException(400,"Servicio no válido.")
 return iniciar(servicio,{})

@app.post("/api/iniciar")
def api_iniciar(data:Respuesta):
 if data.servicio not in ("cita","documento"):
  raise HTTPException(400,"Falta seleccionar el tipo de servicio.")
 if data.caso:
  if not obtener_caso(data.caso):raise HTTPException(404,"Trámite no encontrado.")
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
 r=dict(data.respuestas or {})
 if data.caso:
  if not obtener_caso(data.caso):raise HTTPException(404,"Trámite no encontrado.")
  return continuar(data.caso,r,data.pregunta_id or "",texto)
 return interpretar(data.servicio,texto,r,data.pregunta_id or "")

def esc(v):
 return str(v or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br/>")

def limpio(v):
 return str(v or "").strip()

def lista(a):
 return [limpio(x) for x in (a or []) if limpio(x)]

def ptexto(v):
 return limpio(v) or "PENDIENTE DE COMPLETAR"

def generar_pdf(r):
 buf=io.BytesIO()
 doc=SimpleDocTemplate(
  buf,pagesize=LETTER,rightMargin=42,leftMargin=42,
  topMargin=42,bottomMargin=42,
  title="Hoja de Ruta - Mexicano Apoya Mexicano",
  author="MEXICANO APOYA MEXICANO"
 )
 s=getSampleStyleSheet()
 titulo=ParagraphStyle("T",parent=s["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=5,textColor=colors.HexColor("#173452"))
 sub=ParagraphStyle("S",parent=s["BodyText"],fontSize=9.5,leading=13,alignment=TA_CENTER,spaceAfter=12,textColor=colors.HexColor("#59636d"))
 h=ParagraphStyle("H",parent=s["Heading2"],fontSize=12,leading=15,spaceBefore=14,spaceAfter=7,textColor=colors.HexColor("#173452"))
 body=ParagraphStyle("B",parent=s["BodyText"],fontSize=9.5,leading=13,spaceAfter=5)
 small=ParagraphStyle("SM",parent=s["BodyText"],fontSize=7.5,leading=10,textColor=colors.HexColor("#555f68"))
 estado=ParagraphStyle("E",parent=s["BodyText"],fontSize=13,leading=17,alignment=TA_CENTER,spaceBefore=5,spaceAfter=12)
 story=[]

 def H(t):story.append(Paragraph(esc(t),h))
 def P(t):
  if limpio(t):story.append(Paragraph(esc(t),body))
 def L(a):
  for x in lista(a):P("• "+x)
 def T(rows,widths=(160,330)):
  if not rows:return
  rows=[[Paragraph(esc(str(c)),body) for c in row] for row in rows]
  t=Table(rows,colWidths=widths,repeatRows=1)
  t.setStyle(TableStyle([
   ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#173452")),
   ("TEXTCOLOR",(0,0),(-1,0),colors.white),
   ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
   ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
   ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#b9c2ca")),
   ("VALIGN",(0,0),(-1,-1),"TOP"),
   ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f7f9fb")]),
   ("LEFTPADDING",(0,0),(-1,-1),7),
   ("RIGHTPADDING",(0,0),(-1,-1),7),
   ("TOPPADDING",(0,0),(-1,-1),5),
   ("BOTTOMPADDING",(0,0),(-1,-1),5)
  ]))
  story.extend([t,Spacer(1,7)])

 nivel=r.get("nivel","amarillo")
 color="#087f3e" if nivel=="verde" else "#9b2424" if nivel=="rojo" else "#8a6500"
 estado.textColor=colors.HexColor(color)
 perfil=r.get("perfil") or {}
 rr=r.get("respuestas") or {}
 caso=r.get("caso","")
 docs=r.get("documentos") or []
 tiene=[x.get("nombre") for x in docs if isinstance(x,dict) and x.get("estado")=="tiene"]
 falta=[x.get("nombre") for x in docs if isinstance(x,dict) and x.get("estado")=="falta"]
 revisar=[x.get("nombre") for x in docs if isinstance(x,dict) and x.get("estado")=="revisar"]
 menor=caso in ("pasaporte_menor","matricula_menor")

 story.append(Paragraph("MEXICANO APOYA MEXICANO",titulo))
 story.append(Paragraph("HOJA DE RUTA PERSONAL DEL TRÁMITE",titulo))
 story.append(Paragraph("Organiza tu información para que puedas revisar tu caso antes de acudir.",sub))
 story.append(Paragraph("<b>"+esc(r.get("estado_texto","TE FALTA ALGO"))+"</b>",estado))

 H("1. DATOS PERSONALES")
 T([
  ["DATO","INFORMACIÓN"],
  ["Nombre",ptexto(perfil.get("nombre"))],
  ["Nacionalidad",ptexto(perfil.get("nacionalidad"))],
  ["Teléfono",ptexto(perfil.get("telefono"))],
  ["Dirección",ptexto(perfil.get("direccion"))],
  ["Estado",ptexto(perfil.get("estado"))],
  ["ZIP",ptexto(perfil.get("zip") or perfil.get("codigo_postal"))],
  ["Correo",ptexto(perfil.get("email") or perfil.get("correo"))]
 ])

 H("2. TRÁMITE")
 P(r.get("tramite") or r.get("titulo") or caso)

 H("3. PERSONAS QUE DEBEN PRESENTARSE")
 L(r.get("personas_obligatorias") or ["PENDIENTE DE COMPLETAR"])

 H("4. REQUISITOS OBLIGATORIOS")
 L(r.get("requisitos_obligatorios") or ["PENDIENTE DE COMPLETAR"])

 n=5
 if menor:
  H("5. INFORMACIÓN DEL MENOR")
  T([
   ["DATO","INFORMACIÓN"],
   ["Nombre del menor",ptexto(rr.get("menor_nombre") or perfil.get("nombre"))],
   ["Nacionalidad / documento",ptexto(rr.get("menor_nacionalidad"))],
   ["Identificación",ptexto(rr.get("menor_identidad"))]
  ])
  H("6. PADRE, MADRE O TUTOR")
  T([
   ["DATO","INFORMACIÓN"],
   ["Nombre",ptexto(rr.get("padre1"))],
   ["Identificación",ptexto(rr.get("padre1_id"))],
   ["Otro padre/madre/tutor",ptexto(rr.get("padre2"))],
   ["Autorización",ptexto(rr.get("autorizacion") or rr.get("op7"))]
  ])
  n=7

 H(f"{n}. LO QUE YA TIENES");L(tiene or ["Todavía no se confirmó ningún documento disponible."])
 n+=1
 H(f"{n}. LO QUE TE FALTA");L(falta or ["No se confirmó todavía un documento como faltante."])
 n+=1
 H(f"{n}. LO QUE DEBES CONFIRMAR");L(revisar or ["No hay otro punto marcado para confirmar."])
 n+=1
 H(f"{n}. ¿QUÉ DEBES HACER?")
 P(r.get("prepara") or "Reúne los documentos indicados y confirma los puntos pendientes antes de acudir.")
 n+=1
 H(f"{n}. CITA");L(r.get("cita") or ["Confirma directamente si necesitas cita."])
 n+=1
 H(f"{n}. DOCUMENTOS ORIGINALES");L(r.get("originales") or ["PENDIENTE DE COMPLETAR"])
 n+=1
 H(f"{n}. COPIAS")
 copias=lista(r.get("copias"))
 L(copias or ["No se identificaron copias obligatorias con la información disponible."])
 n+=1
 H(f"{n}. PAGO");P(r.get("pago") or "Confirma la tarifa y forma de pago vigente.")
 n+=1
 H(f"{n}. ANTES DE FIRMAR O IMPRIMIR");P(r.get("revision"))
 n+=1
 if r.get("vigencia"):
  H(f"{n}. VIGENCIA");P(r["vigencia"]);n+=1
 if r.get("entrega"):
  H(f"{n}. ENTREGA");P(r["entrega"]);n+=1
 H(f"{n}. INFORMACIÓN IMPORTANTE")
 importantes=list(dict.fromkeys(lista(r.get("importante"))+lista(r.get("especiales"))))
 L(importantes or ["La autoridad consular puede solicitar información adicional."])
 P(r.get("confirma"))
 H(f"{n+1}. INFORMACIÓN OFICIAL")
 P("Consulta la información oficial antes de acudir:")
 P(r.get("fuente") or FUENTES.get("tarifas"))
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
  if not obtener_caso(data.caso):raise HTTPException(404,"Trámite no encontrado.")
  r=continuar(data.caso,data.respuestas or {})
 if not r or r.get("tipo")!="resultado":
  raise HTTPException(400,"Primero termina la consulta.")
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
