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

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="6.0")
security=HTTPBasic()

DEV_USER=os.getenv("DEV_USER",os.getenv("ADMIN_USERNAME","admin"))
DEV_PASS=os.getenv("DEV_PASS",os.getenv("ADMIN_PASSWORD","securepassword"))
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-ayudar.onrender.com").rstrip("/")

PRICE_IDS={
 "daily":os.getenv("STRIPE_PRICE_ID_DAILY",os.getenv("STRIPE_PRICE_ID1","")),
 "monthly":os.getenv("STRIPE_PRICE_ID_MONTHLY",os.getenv("STRIPE_PRICE_ID2","")),
 "annual":os.getenv("STRIPE_PRICE_ID_ANNUAL","")
}

stripe.api_key=STRIPE_SECRET_KEY
gemini=None
if GEMINI_API_KEY:
    try:
        gemini=genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print("Gemini:",e)

SALIDAS_DIR=Path("salidas")
SALIDAS_DIR.mkdir(exist_ok=True)

TRAMITES={
 "pasaporte":{
  "nombre":"Pasaporte Mexicano",
  "base":"pasaporte",
  "requisitos":[
   "Identificación oficial vigente",
   "Acta de nacimiento",
   "Comprobante de domicilio reciente en Estados Unidos"
  ]},
 "matricula":{
  "nombre":"Matrícula Consular",
  "base":"matricula_consular",
  "requisitos":[
   "Identificación oficial",
   "Comprobante de domicilio reciente en Estados Unidos",
   "Datos necesarios para el trámite"
  ]},
 "ine":{
  "nombre":"Credencial para Votar (INE)",
  "base":"credencial_ine",
  "requisitos":[
   "Identificación oficial",
   "Comprobante de domicilio",
   "Datos personales correctos"
  ]},
 "registro":{
  "nombre":"Registro de Nacimiento",
  "base":"registro_nacimiento",
  "requisitos":[
   "Acta o certificado de nacimiento correspondiente",
   "Identificaciones oficiales",
   "Documentos que acrediten los datos necesarios"
  ]},
 "actas":{
  "nombre":"Solicitud de Actas",
  "base":"solicitud_actas",
  "requisitos":[
   "Datos correctos de la persona registrada",
   "Información disponible del registro",
   "Identificación cuando corresponda"
  ]},
 "poderes":{
  "nombre":"Poderes Notariales",
  "base":"poderes_notariales",
  "requisitos":[
   "Identificación oficial vigente",
   "Datos completos de la persona que recibirá el poder",
   "Descripción clara del propósito"
  ]}
}

class DatosTramite(BaseModel):
    categoria_tramite:str
    primer_nombre:str=""
    segundo_nombre:str=""
    primer_apellido:str=""
    segundo_apellido:str=""
    fecha_nacimiento:str=""
    lugar_nacimiento:str=""
    direccion_usa:str=""
    telefono:str=""
    nacionalidad:str="Mexicana"
    consulado:str=""
    cita:str=""
    documentos_tenidos:list[str]=[]
    documentos_faltantes:list[str]=[]
    datos_extraidos:list[dict]=[]
    confirmado:bool=False

class PreguntaRequest(BaseModel):
    pregunta:str
    categoria_tramite:str="general"

class ResultadoRequest(BaseModel):
    categoria_tramite:str
    estado:str

class StripeCheckoutRequest(BaseModel):
    plan:str=""

def credenciales(c:HTTPBasicCredentials=Depends(security)):
    if c.username!=DEV_USER or c.password!=DEV_PASS:
        raise HTTPException(401,"Credenciales de acceso no válidas.",
                            headers={"WWW-Authenticate":"Basic"})
    return c.username

def limpio(x):
    return re.sub(r"\s+"," ",str(x or "")).strip()

def seguro(x):
    return limpio(x).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def nombre_completo(d):
    return " ".join(x for x in [
        d.primer_nombre,d.segundo_nombre,
        d.primer_apellido,d.segundo_apellido
    ] if limpio(x)).strip()

def tipo_valido(tipo):
    return tipo if tipo in TRAMITES else "pasaporte"

def price_id_plan(plan):
    return PRICE_IDS.get(plan,"")

def activar_servicio(email,session_id):
    print(f"PAGO CONFIRMADO | {email} | {session_id}")

@app.post("/api/create-checkout-session")
async def create_checkout_session(data:StripeCheckoutRequest):
    price_id=price_id_plan(data.plan)
    if not price_id:
        raise HTTPException(400,"El Price ID de este plan no está configurado en Render.")
    try:
        price=stripe.Price.retrieve(price_id)
        mode="subscription" if price.get("recurring") else "payment"
        s=stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price":price_id,"quantity":1}],
            mode=mode,
            success_url=f"{APP_URL}/?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?canceled=true",
            metadata={"plan":data.plan}
        )
        return {"checkout_url":s.url,"session_id":s.id,"mode":mode}
    except Exception as e:
        raise HTTPException(400,f"No se pudo iniciar el pago: {e}")

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature")
    if not WEBHOOK_SECRET:
        raise HTTPException(500,"STRIPE_WEBHOOK_SECRET no está configurado.")
    try:
        event=stripe.Webhook.construct_event(payload,sig,WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400,"Payload de webhook inválido.")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400,"Firma de webhook no válida.")
    if event["type"] in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded"
    ):
        s=event["data"]["object"]
        email=s.get("customer_email") or \
              (s.get("customer_details") or {}).get("email") or "usuario"
        activar_servicio(email,s.get("id"))
    return {"status":"success"}

@app.post("/api/ficha-tramite")
async def ficha_tramite(datos:DatosTramite,user=Depends(credenciales)):
    tipo=tipo_valido(datos.categoria_tramite)
    datos.documentos_tenidos=[
        limpio(x) for x in datos.documentos_tenidos if limpio(x)
    ]
    datos.documentos_faltantes=[
        limpio(x) for x in datos.documentos_faltantes if limpio(x)
    ]
    return {
        "tramite":TRAMITES[tipo]["nombre"],
        "persona":{
            "nombre":nombre_completo(datos),
            "fecha_nacimiento":limpio(datos.fecha_nacimiento),
            "lugar_nacimiento":limpio(datos.lugar_nacimiento),
            "nacionalidad":limpio(datos.nacionalidad) or "Mexicana"
        },
        "contacto":{
            "direccion":limpio(datos.direccion_usa),
            "telefono":limpio(datos.telefono)
        },
        "consulado":limpio(datos.consulado),
        "cita":limpio(datos.cita),
        "documentos_tenidos":datos.documentos_tenidos,
        "documentos_faltantes":datos.documentos_faltantes,
        "datos_extraidos":datos.datos_extraidos,
        "confirmado":datos.confirmado
    }

@app.post("/api/extraer-pdf")
async def extraer_pdf(file:UploadFile=File(...),user=Depends(credenciales)):
    if file.content_type!="application/pdf":
        raise HTTPException(400,"Solo se acepta un archivo PDF.")
    data=await file.read()
    if len(data)>10*1024*1024:
        raise HTTPException(400,"El PDF supera el límite de 10 MB.")
    path=None
    try:
        with tempfile.NamedTemporaryFile(delete=False,suffix=".pdf") as f:
            f.write(data)
            path=f.name
        reader=PdfReader(path)
        paginas=len(reader.pages)
        texto="\n".join((p.extract_text() or "") for p in reader.pages)
        texto=limpio(texto)
        return {
            "status":"success",
            "paginas":paginas,
            "texto":texto[:50000],
            "datos":{
                "texto_extraido":texto[:50000],
                "fuente":"PDF proporcionado por el usuario"
            }
        }
    except Exception as e:
        raise HTTPException(400,f"No se pudo leer el PDF: {e}")
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass

@app.post("/api/pregunta")
async def pregunta(data:PreguntaRequest,user=Depends(credenciales)):
    q=limpio(data.pregunta)
    if not q:
        raise HTTPException(400,"Escribe tu duda.")
    if len(q)>1000:
        raise HTTPException(400,"La pregunta es demasiado larga.")

    tipo=data.categoria_tramite if data.categoria_tramite in TRAMITES else "general"
    contexto=TRAMITES[tipo]["nombre"] if tipo!="general" else "trámites y documentos"

    respuesta=(
        "No puedo confirmar ese dato sin la fuente oficial. "
        "Puedo ayudarte a organizar la información de este trámite."
    )

    if gemini:
        try:
            r=gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"""
Eres el asistente documental de SAVE MÉXICO AYUDAR.
Tema: {contexto}
Pregunta: {q}

Responde solamente sobre preparación y organización documental.
Usa español muy sencillo.
Máximo 5 frases cortas.
No inventes requisitos.
No des asesoría legal.
No prometas resultados.
No digas que representas al Gobierno de México o a un Consulado.
Si algo depende de la autoridad, dilo claramente.
"""
            )
            if r and r.text:
                respuesta=r.text.strip()
        except Exception:
            pass

    return {"respuesta":respuesta}

@app.post("/api/generar-guia-consular")
async def generar_guia_consular(datos:DatosTramite,user=Depends(credenciales)):
    tipo=tipo_valido(datos.categoria_tramite)

    if not nombre_completo(datos):
        raise HTTPException(400,"Falta el nombre de la persona.")
    if not datos.fecha_nacimiento:
        raise HTTPException(400,"Falta la fecha de nacimiento.")
    if not datos.lugar_nacimiento:
        raise HTTPException(400,"Falta el lugar de nacimiento.")

    fecha=limpio(datos.fecha_nacimiento)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}",fecha):
        y,m,d=fecha.split("-")
        fecha=f"{d}/{m}/{y}"

    nombre=nombre_completo(datos)
    documentos_tenidos=[
        limpio(x) for x in datos.documentos_tenidos if limpio(x)
    ]
    documentos_faltantes=[
        limpio(x) for x in datos.documentos_faltantes if limpio(x)
    ]

    estilos=getSampleStyleSheet()

    titulo=ParagraphStyle(
        "titulo",parent=estilos["Heading1"],
        fontName="Helvetica-Bold",fontSize=18,
        leading=21,textColor=colors.HexColor("#17456b"),
        alignment=1,spaceAfter=7
    )

    subtitulo=ParagraphStyle(
        "subtitulo",parent=estilos["Normal"],
        fontName="Helvetica-Bold",fontSize=11,
        leading=14,textColor=colors.HexColor("#333"),
        alignment=1,spaceAfter=16
    )

    seccion=ParagraphStyle(
        "seccion",parent=estilos["Heading2"],
        fontName="Helvetica-Bold",fontSize=11,
        leading=14,textColor=colors.HexColor("#17456b"),
        spaceBefore=12,spaceAfter=6
    )

    campo=ParagraphStyle(
        "campo",parent=estilos["Normal"],
        fontName="Helvetica",fontSize=10,
        leading=14,textColor=colors.HexColor("#222"),
        spaceAfter=2
    )

    pequeno=ParagraphStyle(
        "pequeno",parent=estilos["Normal"],
        fontName="Helvetica",fontSize=7.5,
        leading=9,textColor=colors.HexColor("#666"),
        alignment=1
    )

    aviso=ParagraphStyle(
        "aviso",parent=campo,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#17456b")
    )

    buf=io.BytesIO()
    doc=SimpleDocTemplate(
        buf,pagesize=letter,
        rightMargin=48,leftMargin=48,
        topMargin=45,bottomMargin=45
    )

    story=[]

    story.append(Paragraph("SAVE MÉXICO AYUDAR",titulo))
    story.append(Paragraph(
        f"MI TRÁMITE: {seguro(TRAMITES[tipo]['nombre'])}",
        subtitulo
    ))

    story.append(Paragraph("PERSONA",seccion))

    persona=[
        ["Nombre",nombre],
        ["Fecha de nacimiento",fecha],
        ["Lugar de nacimiento",limpio(datos.lugar_nacimiento)],
        ["Nacionalidad",limpio(datos.nacionalidad) or "Mexicana"]
    ]

    if limpio(datos.direccion_usa):
        persona.append(["Domicilio",limpio(datos.direccion_usa)])

    if limpio(datos.telefono):
        persona.append(["Teléfono",limpio(datos.telefono)])

    table=Table(
        [[Paragraph(f"<b>{seguro(a)}</b>",campo),
          Paragraph(seguro(b),campo)] for a,b in persona],
        colWidths=[145,385]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f2f5f7")),
        ("BOX",(0,0),(-1,-1),.7,colors.HexColor("#d5dadd")),
        ("INNERGRID",(0,0),(-1,-1),.35,colors.HexColor("#e5e8ea")),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),7),
        ("BOTTOMPADDING",(0,0),(-1,-1),7)
    ]))

    story.append(table)

    if documentos_tenidos:
        story.append(Paragraph("DOCUMENTOS QUE TENGO",seccion))
        for d in documentos_tenidos:
            story.append(
                Paragraph(f"✓ {seguro(d)}",campo)
            )
    else:
        story.append(Paragraph("DOCUMENTOS QUE TENGO",seccion))
        story.append(Paragraph(
            "No se han indicado documentos disponibles.",
            campo
        ))

    if documentos_faltantes:
        story.append(Paragraph("DOCUMENTOS QUE ME FALTAN",seccion))
        for d in documentos_faltantes:
            story.append(
                Paragraph(f"☐ {seguro(d)}",campo)
            )

    story.append(Paragraph("ANTES DE IR",seccion))

    for item in [
        "Revisar que mis datos estén correctos.",
        "Revisar los documentos que voy a presentar.",
        "Confirmar los requisitos oficiales.",
        "Confirmar mi cita, si corresponde."
    ]:
        story.append(Paragraph(f"☐ {item}",campo))

    story.append(Paragraph("SIGUIENTE PASO",seccion))
    story.append(Paragraph(
        "Revisa tus datos y confirma los requisitos finales con la autoridad oficial antes de acudir.",
        aviso
    ))

    if limpio(datos.consulado) or limpio(datos.cita):
        story.append(Paragraph("CITA / CONSULADO",seccion))

        if limpio(datos.consulado):
            story.append(
                Paragraph(
                    f"<b>Consulado:</b> {seguro(datos.consulado)}",
                    campo
                )
            )

        if limpio(datos.cita):
            story.append(
                Paragraph(
                    f"<b>Cita:</b> {seguro(datos.cita)}",
                    campo
                )
            )

    story.append(Spacer(1,14))
    story.append(Paragraph(
        "IMPORTANTE",
        seccion
    ))
    story.append(Paragraph(
        "SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida. "
        "No es una agencia del Gobierno de México ni representa a ningún Consulado de México. "
        "Los requisitos, decisiones, aceptación de documentos y resultado corresponden a la autoridad competente.",
        pequeno
    ))

    doc.build(story)
    buf.seek(0)

    archivo=(
        f"{TRAMITES[tipo]['base']}_"
        f"save_mexico_{uuid.uuid4().hex[:8]}.pdf"
    )

    ruta=SALIDAS_DIR/archivo
    ruta.write_bytes(buf.getvalue())

    return {
        "status":"success",
        "archivo":f"/descargar/{archivo}",
        "nombre_archivo":archivo
    }

@app.post("/api/resultado-tramite")
async def resultado_tramite(
    data:ResultadoRequest,
    user=Depends(credenciales)
):
    estados={
        "aprobado":"APROBADO / COMPLETADO",
        "otro_documento":"ME PIDIERON OTRO DOCUMENTO",
        "no_pude":"NO PUDE COMPLETARLO",
        "continuar":"NECESITO CONTINUAR"
    }

    if data.estado not in estados:
        raise HTTPException(400,"Estado no válido.")

    return {
        "status":"success",
        "estado":estados[data.estado],
        "siguiente_paso":
            "Continúa con la preparación y confirma la información oficial correspondiente."
    }

@app.get("/descargar/{nombre_archivo}")
async def descargar(
    nombre_archivo:str,
    user=Depends(credenciales)
):
    if (
        "/" in nombre_archivo or
        "\\" in nombre_archivo or
        ".." in nombre_archivo
    ):
        raise HTTPException(400,"Nombre de archivo no válido.")

    ruta=SALIDAS_DIR/nombre_archivo

    if not ruta.exists() or ruta.suffix.lower()!=".pdf":
        raise HTTPException(404,"Archivo no encontrado.")

    return FileResponse(
        str(ruta),
        media_type="application/pdf",
        filename="Mi_Tramite_Save_Mexico.pdf"
    )

@app.get("/")
async def home():
    for archivo in [
        Path("index.html"),
        Path("static/index.html")
    ]:
        if archivo.exists():
            return HTMLResponse(
                archivo.read_text(encoding="utf-8")
            )
    return HTMLResponse(
        "<h1>Error: Falta index.html</h1>",
        status_code=500
    )

@app.on_event("startup")
async def limpiar_salidas():
    try:
        for f in SALIDAS_DIR.glob("*.pdf"):
            if f.is_file():
                f.unlink()
    except Exception as e:
        print("Limpieza:",e)
