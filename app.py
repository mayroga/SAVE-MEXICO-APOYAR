# app.py
import os
import io
import re
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import stripe

from google import genai

app = FastAPI(title="SAVE MÉXICO AYUDAR - Asistencia Privada de Gestión Documental", version="4.0")

security = HTTPBasic()

DEV_USER = os.getenv("DEV_USER", "admin")
DEV_PASS = os.getenv("DEV_PASS", "securepassword")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
ENDPOINT_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

client_genai = None
if GEMINI_API_KEY:
    try:
        client_genai = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Aviso al inicializar cliente de GenAI: {e}")

SALIDAS_DIR = "salidas"
os.makedirs(SALIDAS_DIR, exist_ok=True)

class DatosTramiteConsular(BaseModel):
    categoria_tramite: str
    primer_nombre: str
    segundo_nombre: str = ""
    primer_apellido: str
    segundo_apellido: str = ""
    fecha_nacimiento: str
    lugar_nacimiento: str
    direccion_usa: str
    telefono: str
    documentos_tenidos: str = ""
    documentos_faltantes: str = ""
    estado_posterior: str = "pendiente"
    extra_1: str = ""
    extra_2: str = ""

class StripeCheckoutRequest(BaseModel):
    price_id: str

def verificar_credenciales(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = credentials.username == DEV_USER
    correct_password = credentials.password == DEV_PASS
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Credenciales de acceso no válidas.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

def limpiar_y_corregir(texto: str) -> str:
    if not texto:
        return ""
    return re.sub(r'\s+', ' ', texto).strip().upper()

def activar_servicio_usuario(email_o_cliente, session_id):
    print(f"Servicio activado exitosamente en servidor para: {email_o_cliente} (Sesión ID: {session_id})")

@app.post("/api/create-checkout-session")
async def create_checkout_session(data: StripeCheckoutRequest):
    try:
        domain_url = "https://save-mexico-ayudar.onrender.com"
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': data.price_id,
                'quantity': 1,
            }],
            mode='payment',
            success_url=domain_url + '/?success=true&session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + '/?canceled=true',
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = None

    try:
        if ENDPOINT_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, ENDPOINT_SECRET
            )
        else:
            event = stripe.Event.construct_from(await request.json(), stripe.api_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload de webhook inválido.")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma de webhook no válida.")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email") or "usuario_web@savemexico.com"
        session_id = session.get("id")
        activar_servicio_usuario(customer_email, session_id)

    return {"status": "success"}

@app.post("/api/generar-guia-consular")
async def generar_guia_consular(datos: DatosTramiteConsular, username: str = Depends(verificar_credenciales)):
    p1 = limpiar_y_corregir(datos.primer_nombre)
    p2 = limpiar_y_corregir(datos.segundo_nombre)
    a1 = limpiar_y_corregir(datos.primer_apellido)
    a2 = limpiar_y_corregir(datos.segundo_apellido)
    lugar = limpiar_y_corregir(datos.lugar_nacimiento)
    direccion = limpiar_y_corregir(datos.direccion_usa)
    telefono = limpiar_y_corregir(datos.telefono)
    tenidos = limpiar_y_corregir(datos.documentos_tenidos)
    faltantes = limpiar_y_corregir(datos.documentos_faltantes)
    ex1 = limpiar_y_corregir(datos.extra_1)
    ex2 = limpiar_y_corregir(datos.extra_2)
    
    if not p1 or not a1 or not datos.fecha_nacimiento or not lugar or not direccion or not telefono:
        raise HTTPException(status_code=400, detail="Faltan datos obligatorios. Verifique los campos antes de continuar.")
    
    if "-" not in datos.fecha_nacimiento:
        raise HTTPException(status_code=400, detail="Formato de fecha no válido.")
    
    ano, mes, dia = datos.fecha_nacimiento.split("-")
    fecha_formateada = f"{dia}/{mes}/{ano}"

    analisis_ia = ""
    if client_genai:
        try:
            prompt_modelo = f"Genera una orientación breve de una línea para un ciudadano preparándose para el trámite de {datos.categoria_tramite} en Estados Unidos."
            response = client_genai.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_modelo,
            )
            if response and response.text:
                analisis_ia = response.text.strip()
        except Exception:
            analisis_ia = "Verifique sus documentos originales directamente en la fuente oficial correspondiente."

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle(
        'TituloDoc', parent=styles['Heading1'], fontName='Helvetica-Bold',
        fontSize=14, leading=16, textColor=colors.HexColor("#1b365d"),
        alignment=1, spaceAfter=12
    )
    
    estilo_seccion = ParagraphStyle(
        'SeccionDoc', parent=styles['Heading2'], fontName='Helvetica-Bold',
        fontSize=11, leading=14, textColor=colors.HexColor("#1a1a1a"),
        spaceBefore=10, spaceAfter=6
    )
    
    estilo_texto = ParagraphStyle(
        'TextoDoc', parent=styles['Normal'], fontName='Helvetica',
        fontSize=10, leading=14, textColor=colors.HexColor("#333333"), spaceAfter=4
    )
    
    estilo_aviso = ParagraphStyle(
        'AvisoDoc', parent=styles['Normal'], fontName='Helvetica-Bold',
        fontSize=9, leading=12, textColor=colors.HexColor("#856404"),
        spaceBefore=6, spaceAfter=6
    )

    estilo_legal = ParagraphStyle(
        'LegalDoc', parent=styles['Normal'], fontName='Helvetica-Oblique',
        fontSize=8, leading=10, textColor=colors.HexColor("#666666"),
        alignment=1, spaceBefore=15
    )

    elementos = []
    elementos.append(Paragraph("SAVE MÉXICO AYUDAR", estilo_titulo))
    
    tramites_config = {
        "pasaporte": {
            "nombre_base": "pasaporte",
            "titulo": "GUÍA DE PREPARACIÓN: TRÁMITE CONSULAR",
            "requisitos": [
                "Identificación oficial vigente.",
                "Copia acta de nacimiento.",
                "Comprobante de domicilio reciente en EE. UU."
            ],
            "nota": f"ORIENTACIÓN: {analisis_ia if analisis_ia else 'Reúna sus documentos con calma paso por paso.'}"
        },
        "matricula": {
            "nombre_base": "matricula_consular",
            "titulo": "GUÍA DE PREPARACIÓN: MATRÍCULA Y REGISTRO",
            "requisitos": [
                "Identificación oficial.",
                "Comprobante de domicilio reciente en EE. UU.",
                "Datos de contacto de emergencia."
            ],
            "nota": "ORIENTACIÓN: Compruebe que el comprobante refleje su residencia actual."
        },
        "ine": {
            "nombre_base": "credencial_ine",
            "titulo": "GUÍA DE PREPARACIÓN: CREDENCIAL Y REGISTRO ELECTORAL",
            "requisitos": [
                "Identificación oficial.",
                "Comprobante de domicilio."
            ],
            "nota": "ORIENTACIÓN: Revise el estatus de su registro en la plataforma oficial."
        },
        "registro": {
            "nombre_base": "registro_nacimiento",
            "titulo": "GUÍA DE PREPARACIÓN: REGISTRO Y CERTIFICACIÓN",
            "requisitos": [
                "Certificado de nacimiento original (Long Form).",
                "Identificaciones oficiales vigentes."
            ],
            "nota": "ORIENTACIÓN: Asegúrese de que las firmas sean legibles."
        },
        "actas": {
            "nombre_base": "copia_actas",
            "titulo": "GUÍA DE PREPARACIÓN: SOLICITUD DE ACTAS",
            "requisitos": [
                "Datos precisos de la persona registrada.",
                "Identificación oficial vigente."
            ],
            "nota": "ORIENTACIÓN: Confirme que los datos coincidan con los originales."
        },
        "poderes": {
            "nombre_base": "poderes_notariales",
            "titulo": "GUÍA DE PREPARACIÓN: ACTOS NOTARIALES",
            "requisitos": [
                "Identificación oficial vigente.",
                "Datos completos de la persona representante.",
                "Descripción clara del propósito."
            ],
            "nota": "ORIENTACIÓN: Redacte con claridad el alcance del trámite."
        }
    }

    config = tramites_config.get(datos.categoria_tramite, tramites_config["pasaporte"])

    elementos.append(Paragraph(config["titulo"], estilo_seccion))
    elementos.append(Spacer(1, 4))

    datos_tabla = [
        [Paragraph("<b>Titular / Solicitante:</b>", estilo_texto), Paragraph(f"{p1} {p2} {a1} {a2}", estilo_texto)],
        [Paragraph("<b>Nacimiento:</b>", estilo_texto), Paragraph(f"{fecha_formateada} ({lugar})", estilo_texto)],
        [Paragraph("<b>Domicilio USA:</b>", estilo_texto), Paragraph(f"{direccion}", estilo_texto)],
        [Paragraph("<b>Teléfono:</b>", estilo_texto), Paragraph(f"{telefono}", estilo_texto)],
        [Paragraph("<b>Lo que tienes:</b>", estilo_texto), Paragraph(f"{tenidos if tenidos else 'No especificado'}", estilo_texto)],
        [Paragraph("<b>Lo que falta:</b>", estilo_texto), Paragraph(f"{faltantes if faltantes else 'Ninguno'}", estilo_texto)],
        [Paragraph("<b>Estatus Posterior:</b>", estilo_texto), Paragraph(f"{datos.estado_posterior.upper()}", estilo_texto)]
    ]

    if ex1 or ex2:
        datos_tabla.append([Paragraph("<b>Referencia Extra:</b>", estilo_texto), Paragraph(f"{ex1} | {ex2}", estilo_texto)])

    t = Table(datos_tabla, colWidths=[120, 410])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8f9fa")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#d6d8db")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e9ecef")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    elementos.append(t)
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("CHECKLIST DE DOCUMENTOS A PREPARAR", estilo_seccion))
    
    checklist_data = []
    for req in config["requisitos"]:
        checklist_data.append([Paragraph("[    ]", estilo_texto), Paragraph(req, estilo_texto)])

    t_check = Table(checklist_data, colWidths=[30, 500])
    t_check.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    
    elementos.append(t_check)
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph(config["nota"], estilo_aviso))
    elementos.append(Spacer(1, 10))

    texto_legal = (
        "SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida.<br/>"
        "No es una agencia del Gobierno de México ni representa a ningún consulado mexicano.<br/>"
        "Este documento generado es un apoyo de organización personal. Los requisitos y decisiones corresponden a la autoridad."
    )
    elementos.append(Paragraph(texto_legal, estilo_legal))

    doc.build(elementos)
    buffer.seek(0)
    
    nombre_salida = f"{config['nombre_base']}_save_mexico_{os.urandom(4).hex()}.pdf"
    ruta_salida = os.path.join(SALIDAS_DIR, nombre_salida)
    
    with open(ruta_salida, "wb") as f:
        f.write(buffer.getvalue())

    return {"status": "success", "archivo": f"/descargar/{nombre_salida}"}

@app.get("/descargar/{nombre_archivo}")
async def descargar(nombre_archivo: str):
    ruta = os.path.join(SALIDAS_DIR, nombre_archivo)
    if os.path.exists(ruta):
        return FileResponse(ruta, media_type="application/pdf", filename="Guia_Preparacion_Save_Mexico.pdf")
    raise HTTPException(status_code=404, detail="Archivo no encontrado.")

@app.get("/")
async def home():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Error: Falta index.html</h1>", status_code=500)
