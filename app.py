```python
import os,io,re,uuid,tempfile
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request,Depends,UploadFile,File
from fastapi.responses import HTMLResponse,FileResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from pydantic import BaseModel
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
import stripe
from google import genai

app=FastAPI(title="SAVE MÉXICO AYUDAR - Asistencia Privada de Gestión Documental",version="5.0")
security=HTTPBasic()

DEV_USER=os.getenv("DEV_USER",os.getenv("ADMIN_USERNAME","admin"))
DEV_PASS=os.getenv("DEV_PASS",os.getenv("ADMIN_PASSWORD","securepassword"))
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-ayudar.onrender.com").rstrip("/")

# Render: puedes usar estos nombres
PRICE_IDS={
 "daily":os.getenv("STRIPE_PRICE_ID_DAILY",os.getenv("STRIPE_PRICE_ID1","")),
 "monthly":os.getenv("STRIPE_PRICE_ID_MONTHLY",os.getenv("STRIPE_PRICE_ID2","")),
 "annual":os.getenv("STRIPE_PRICE_ID_ANNUAL","")
}

stripe.api_key=STRIPE_SECRET_KEY
client_genai=None
if GEMINI_API_KEY:
    try: client_genai=genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e: print("Gemini:",e)

SALIDAS_DIR=Path("salidas")
SALIDAS_DIR.mkdir(exist_ok=True)

TRAMITES={
 "pasaporte":{
  "nombre":"Pasaporte Mexicano","base":"pasaporte",
  "requisitos":["Identificación oficial vigente.","Acta de nacimiento.","Comprobante de domicilio reciente en EE. UU."]
 },
 "matricula":{
  "nombre":"Matrícula Consular","base":"matricula_consular",
  "requisitos":["Identificación oficial.","Comprobante de domicilio reciente en EE. UU.","Datos necesarios para el trámite."]
 },
 "ine":{
  "nombre":"Credencial para Votar (INE)","base":"credencial_ine",
  "requisitos":["Identificación oficial.","Comprobante de domicilio.","Datos personales correctos."]
 },
 "registro":{
  "nombre":"Registro de Nacimiento","base":"registro_nacimiento",
  "requisitos":["Acta o certificado de nacimiento correspondiente.","Identificaciones oficiales.","Documentos que acrediten los datos necesarios."]
 },
 "actas":{
  "nombre":"Solicitud de Actas","base":"copia_actas",
  "requisitos":["Datos correctos de la persona registrada.","Información disponible del registro.","Identificación cuando corresponda."]
 },
 "poderes":{
  "nombre":"Poderes Notariales","base":"poderes_notariales",
  "requisitos":["Identificación oficial vigente.","Datos completos de la persona que recibirá el poder.","Descripción clara del propósito."]
 }
}

class DatosTramiteConsular(BaseModel):
 categoria_tramite:str
 primer_nombre:str
 segundo_nombre:str=""
 primer_apellido:str
 segundo_apellido:str=""
 fecha_nacimiento:str
 lugar_nacimiento:str
 direccion_usa:str
 telefono:str
 documentos_tenidos:str=""
 documentos_faltantes:str=""
 estado_posterior:str="pendiente"
 extra_1:str=""
 extra_2:str=""
 nacionalidad:str="Mexicana"
 consulado:str=""
 cita:str=""

class StripeCheckoutRequest(BaseModel):
 plan:str=""
 price_id:str=""

class PreguntaRequest(BaseModel):
 pregunta:str
 categoria_tramite:str="general"

class ResultadoRequest(BaseModel):
 categoria_tramite:str
 estado:str

def credenciales(c:HTTPBasicCredentials=Depends(security)):
 if c.username!=DEV_USER or c.password!=DEV_PASS:
  raise HTTPException(401,"Credenciales de acceso no válidas.",headers={"WWW-Authenticate":"Basic"})
 return c.username

def limpiar(x):
 return re.sub(r"\s+"," ",str(x or "")).strip().upper()

def texto_seguro(x):
 return str(x or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def activar_servicio(email,session_id):
 print(f"Pago confirmado: {email} | {session_id}")

def tipo_price(price_id):
 for k,v in PRICE_IDS.items():
  if v and price_id==v:return k
 return ""

@app.post("/api/create-checkout-session")
async def create_checkout_session(data:StripeCheckoutRequest):
 plan=data.plan
 price_id=data.price_id or PRICE_IDS.get(plan,"")
 if not price_id:
  raise HTTPException(400,"No está configurado el Price ID de este plan en Render.")
 if data.price_id and data.price_id not in PRICE_IDS.values():
  raise HTTPException(400,"Price ID no autorizado.")
 try:
  # Los precios recurrentes usan subscription; los pagos únicos usan payment.
  price=stripe.Price.retrieve(price_id)
  recurring=bool(price.get("recurring"))
  mode="subscription" if recurring else "payment"
  s=stripe.checkout.Session.create(
   payment_method_types=["card"],
   line_items=[{"price":price_id,"quantity":1}],
   mode=mode,
   success_url=f"{APP_URL}/?success=true&session_id={{CHECKOUT_SESSION_ID}}",
   cancel_url=f"{APP_URL}/?canceled=true",
   metadata={"plan":plan or tipo_price(price_id)}
  )
  return {"checkout_url":s.url,"session_id":s.id,"mode":mode}
 except Exception as e:
  raise HTTPException(400,f"No se pudo iniciar el pago: {e}")

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
 payload=await request.body()
 sig=request.headers.get("stripe-signature")
 try:
  if not WEBHOOK_SECRET: raise HTTPException(500,"STRIPE_WEBHOOK_SECRET no está configurado.")
  event=stripe.Webhook.construct_event(payload,sig,WEBHOOK_SECRET)
 except ValueError: raise HTTPException(400,"Payload de webhook inválido.")
 except stripe.error.SignatureVerificationError: raise HTTPException(400,"Firma de webhook no válida.")
 if event["type"] in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
  s=event["data"]["object"]
  email=s.get("customer_email") or (s.get("customer_details") or {}).get("email") or "usuario"
  activar_servicio(email,s.get("id"))
 return {"status":"success"}

@app.post("/api/generar-guia-consular")
async def generar_guia_consular(datos:DatosTramiteConsular,user=Depends(credenciales)):
 tipo=datos.categoria_tramite if datos.categoria_tramite in TRAMITES else "pasaporte"
 p1,p2,a1,a2=map(limpiar,[datos.primer_nombre,datos.segundo_nombre,datos.primer_apellido,datos.segundo_apellido])
 lugar,direccion,tel=map(limpiar,[datos.lugar_nacimiento,datos.direccion_usa,datos.telefono])
 tenidos,faltantes=map(limpiar,[datos.documentos_tenidos,datos.documentos_faltantes])
 ex1,ex2=map(limpiar,[datos.extra_1,datos.extra_2])
 if not p1 or not a1 or not datos.fecha_nacimiento or not lugar or not direccion or not tel:
  raise HTTPException(400,"Faltan datos obligatorios. Revisa la información antes de continuar.")
 if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",datos.fecha_nacimiento):
  raise HTTPException(400,"La fecha de nacimiento no tiene un formato válido.")
 y,m,d=datos.fecha_nacimiento.split("-")
 fecha=f"{d}/{m}/{y}"

 orientacion="Reúne tus documentos con calma y verifica la información oficial antes de acudir."
 if client_genai:
  try:
   r=client_genai.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"""Actúa solamente como asistente de preparación documental.
Trámite: {TRAMITES[tipo]["nombre"]}.
Da una orientación muy breve y clara en español.
No inventes requisitos, no prometas aprobación y no digas que representas al Gobierno o al Consulado.
Indica que los requisitos finales deben confirmarse con la autoridad oficial."""
   )
   if r and r.text: orientacion=r.text.strip()
  except Exception: pass

 styles=getSampleStyleSheet()
 titulo=ParagraphStyle("t",parent=styles["Heading1"],fontName="Helvetica-Bold",fontSize=15,leading=18,textColor=colors.HexColor("#17456b"),alignment=1,spaceAfter=12)
 seccion=ParagraphStyle("s",parent=styles["Heading2"],fontName="Helvetica-Bold",fontSize=11,leading=14,textColor=colors.HexColor("#222"),spaceBefore=9,spaceAfter=5)
 normal=ParagraphStyle("n",parent=styles["Normal"],fontName="Helvetica",fontSize=9.5,leading=13,textColor=colors.HexColor("#333"),spaceAfter=3)
 aviso=ParagraphStyle("a",parent=normal,fontName="Helvetica-Bold",textColor=colors.HexColor("#856404"),spaceBefore=6)
 legal=ParagraphStyle("l",parent=normal,fontName="Helvetica-Oblique",fontSize=7.5,leading=9,textColor=colors.HexColor("#666"),alignment=1,spaceBefore=14)

 buf=io.BytesIO()
 doc=SimpleDocTemplate(buf,pagesize=letter,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40)
 E=[Paragraph("SAVE MÉXICO AYUDAR",titulo),Paragraph(f"GUÍA DE PREPARACIÓN: {TRAMITES[tipo]['nombre'].upper()}",seccion)]
 nombre=" ".join(x for x in [p1,p2,a1,a2] if x)
 rows=[
  ["Titular",nombre],["Nacimiento",f"{fecha} ({lugar})"],["Domicilio USA",direccion],
  ["Teléfono",tel],["Nacionalidad",limpiar(datos.nacionalidad) or "MEXICANA"],
  ["Consulado",limpiar(datos.consulado) or "NO INDICADO"],["Cita",limpiar(datos.cita) or "NO INDICADA"],
  ["Lo que tienes",tenidos or "NO ESPECIFICADO"],["Lo que falta",faltantes or "NO ESPECIFICADO"]
 ]
 if ex1: rows.append(["Dato adicional",ex1])
 if ex2: rows.append(["Dato adicional",ex2])
 table=Table([[Paragraph(f"<b>{texto_seguro(a)}</b>",normal),Paragraph(texto_seguro(b),normal)] for a,b in rows],colWidths=[125,405])
 table.setStyle(TableStyle([
  ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f7f9fb")),
  ("BOX",(0,0),(-1,-1),1,colors.HexColor("#d6d8db")),
  ("INNERGRID",(0,0),(-1,-1),.4,colors.HexColor("#e9ecef")),
  ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
  ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7)
 ]))
 E += [table,Spacer(1,9),Paragraph("CHECKLIST",seccion)]
 check=[[Paragraph("[    ]",normal),Paragraph(texto_seguro(x),normal)] for x in TRAMITES[tipo]["requisitos"]]
 tc=Table(check,colWidths=[30,500])
 tc.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
 E += [tc,Spacer(1,7),Paragraph("ORIENTACIÓN",seccion),Paragraph(texto_seguro(orientacion),aviso),Spacer(1,8)]
 E += [Paragraph("IMPORTANTE",seccion),Paragraph(
  "Esta guía fue generada con información proporcionada por el usuario. SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida. "
  "No es una agencia del Gobierno de México ni representa a ningún consulado mexicano. "
  "Los requisitos, decisiones, aceptación de documentos y resultados corresponden a la autoridad competente. "
  "Revisa tus datos antes de usar este documento.",legal)]
 doc.build(E)
 buf.seek(0)
 nombre_arch=f"{TRAMITES[tipo]['base']}_save_mexico_{uuid.uuid4().hex[:8]}.pdf"
 ruta=SALIDAS_DIR/nombre_arch
 ruta.write_bytes(buf.getvalue())
 return {"status":"success","archivo":f"/descargar/{nombre_arch}"}

@app.post("/api/pregunta")
async def pregunta(data:PreguntaRequest,user=Depends(credenciales)):
 tipo=data.categoria_tramite if data.categoria_tramite in TRAMITES else "general"
 q=data.pregunta.strip()
 if not q: raise HTTPException(400,"Escribe tu duda.")
 if len(q)>1000: raise HTTPException(400,"La pregunta es demasiado larga.")
 contexto=TRAMITES[tipo]["nombre"] if tipo!="general" else "trámites y documentos de SAVE MÉXICO AYUDAR"
 respuesta="No puedo confirmar ese dato sin la fuente oficial. Puedo ayudarte a organizar y preparar la información de este trámite."
 if client_genai:
  try:
   r=client_genai.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"""Eres el asistente documental de SAVE MÉXICO AYUDAR.
Solo puedes responder dudas sobre preparación de trámites y documentos mexicanos.
Tema actual: {contexto}.
Pregunta: {q}
Responde en español sencillo, corto y claro.
No inventes requisitos.
No des asesoría legal.
No afirmes representar al Gobierno de México ni al Consulado.
Cuando el requisito dependa de la autoridad, indica que debe confirmarse en la fuente oficial."""
   )
   if r and r.text: respuesta=r.text.strip()
  except Exception: pass
 return {"respuesta":respuesta}

@app.post("/api/extraer-pdf")
async def extraer_pdf(file:UploadFile=File(...),user=Depends(credenciales)):
 if file.content_type!="application/pdf": raise HTTPException(400,"Solo se acepta un PDF.")
 data=await file.read()
 if len(data)>10*1024*1024: raise HTTPException(400,"El PDF supera el límite de 10 MB.")
 path=None
 try:
  with tempfile.NamedTemporaryFile(delete=False,suffix=".pdf") as f:
   f.write(data);path=f.name
  reader=PdfReader(path)
  text="\n".join((p.extract_text() or "") for p in reader.pages)
  return {"status":"success","texto":text[:50000],"paginas":len(reader.pages)}
 except Exception as e: raise HTTPException(400,f"No se pudo extraer texto del PDF: {e}")
 finally:
  if path:
   try: os.remove(path)
   except Exception: pass

@app.post("/api/resultado-tramite")
async def resultado_tramite(data:ResultadoRequest,user=Depends(credenciales)):
 estados={"aprobado":"APROBADO / COMPLETADO","otro_documento":"ME PIDIERON OTRO DOCUMENTO","no_pude":"NO PUDE COMPLETARLO","continuar":"NECESITO CONTINUAR"}
 if data.estado not in estados: raise HTTPException(400,"Estado no válido.")
 print(f"RESULTADO | usuario={user} | tramite={data.categoria_tramite} | estado={estados[data.estado]}")
 return {"status":"success","estado":estados[data.estado],"siguiente_paso":"Continuar con la preparación y confirmar la información oficial correspondiente."}

@app.post("/api/ficha-tramite")
async def ficha_tramite(datos:DatosTramiteConsular,user=Depends(credenciales)):
 tipo=datos.categoria_tramite if datos.categoria_tramite in TRAMITES else "pasaporte"
 return {
  "tramite":TRAMITES[tipo]["nombre"],
  "persona":{"nombre":" ".join(x for x in [datos.primer_nombre,datos.segundo_nombre,datos.primer_apellido,datos.segundo_apellido] if x),"nacimiento":datos.fecha_nacimiento,"lugar":datos.lugar_nacimiento,"nacionalidad":datos.nacionalidad},
  "documentos":{"disponibles":datos.documentos_tenidos,"faltantes":datos.documentos_faltantes},
  "consulado":datos.consulado,
  "cita":datos.cita,
  "estado":datos.estado_posterior
 }

@app.get("/descargar/{nombre_archivo}")
async def descargar(nombre_archivo:str,user=Depends(credenciales)):
 if "/" in nombre_archivo or "\\" in nombre_archivo or ".." in nombre_archivo: raise HTTPException(400,"Nombre de archivo no válido.")
 ruta=SALIDAS_DIR/nombre_archivo
 if not ruta.exists() or ruta.suffix.lower()!=".pdf": raise HTTPException(404,"Archivo no encontrado.")
 return FileResponse(str(ruta),media_type="application/pdf",filename="Guia_Preparacion_Save_Mexico.pdf")

@app.get("/")
async def home():
 path=Path("index.html")
 if path.exists(): return HTMLResponse(path.read_text(encoding="utf-8"))
 return HTMLResponse("<h1>Error: Falta index.html</h1>",status_code=500)

@app.on_event("startup")
async def limpiar_salidas():
 # Elimina PDFs temporales antiguos al iniciar el servidor.
 try:
  for f in SALIDAS_DIR.glob("*.pdf"):
   if f.is_file(): f.unlink()
 except Exception as e: print("Limpieza:",e)
```
