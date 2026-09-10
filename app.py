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

# Importación de la librería oficial y actual para Gemini
from google import genai

app = FastAPI(title="SAVE MÉXICO AYUDAR - Asistencia Privada de Gestión Documental", version="3.3")

security = HTTPBasic()

# Credenciales y Configuración de Entorno desde Render
DEV_USER = os.getenv("DEV_USER", "admin")
DEV_PASS = os.getenv("DEV_PASS", "securepassword")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Inicialización correcta del cliente oficial google-genai
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
            success_url=domain_url + '/?success=true',
            cancel_url=domain_url + '/?canceled=true',
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/generar-guia-consular")
async def generar_guia_consular(datos: DatosTramiteConsular, username: str = Depends(verificar_credenciales)):
    p1 = limpiar_y_corregir(datos.primer_nombre)
    p2 = limpiar_y_corregir(datos.segundo_nombre)
    a1 = limpiar_y_corregir(datos.primer_apellido)
    a2 = limpiar_y_corregir(datos.segundo_apellido)
    lugar = limpiar_y_corregir(datos.lugar_nacimiento)
    direccion = limpiar_y_corregir(datos.direccion_usa)
    telefono = limpiar_y_corregir(datos.telefono)
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
            prompt_modelo = f"Genera una recomendación breve de una línea para un ciudadano preparándose para el trámite de {datos.categoria_tramite} en Estados Unidos."
            response = client_genai.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt_modelo,
            )
            if response and response.text:
                analisis_ia = response.text.strip()
        except Exception as e:
            analisis_ia = "Verifique sus documentos originales directamente en el portal oficial correspondiente."

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
                "Documento de identidad oficial original.",
                "Identificación oficial vigente con fotografía.",
                "Comprobante de domicilio reciente en EE. UU. con código postal visible."
            ],
            "nota": f"RECOMENDACIÓN: {analisis_ia if analisis_ia else 'Verifique que su documentación coincida exactamente.'}"
        },
        "matricula": {
            "nombre_base": "matricula_consular",
            "titulo": "GUÍA DE PREPARACIÓN: MATRÍCULA Y REGISTRO",
            "requisitos": [
                "Documento de identidad original.",
                "Comprobante de domicilio reciente en EE. UU.",
                "Datos de contacto de emergencia debidamente registrados."
            ],
            "nota": "RECOMENDACIÓN: Compruebe que el comprobante de domicilio refleje su residencia actual."
        },
        "ine": {
            "nombre_base": "credencial_ine",
            "titulo": "GUÍA DE PREPARACIÓN: CREDENCIAL Y REGISTRO ELECTORAL",
            "requisitos": [
                "Documento de identidad original.",
                "Comprobante de domicilio reciente en EE. UU."
            ],
            "nota": "RECOMENDACIÓN: Ingrese al portal oficial para verificar el estatus de su solicitud."
        },
        "registro": {
            "nombre_base": "registro_nacimiento",
            "titulo": "GUÍA DE PREPARACIÓN: REGISTRO Y CERTIFICACIÓN",
            "requisitos": [
                "Certificado de nacimiento original (Formato Largo / Long Form).",
                "Identificaciones oficiales vigentes."
            ],
            "nota": "RECOMENDACIÓN: El certificado debe contar con firmas legibles."
        },
        "actas": {
            "nombre_base": "copia_actas",
            "titulo": "GUÍA DE PREPARACIÓN: SOLICITUD DE ACTAS",
            "requisitos": [
                "Datos precisos de la persona registrada (Nombre completo y fecha exacta).",
                "Identificación oficial vigente del solicitante."
            ],
            "nota": "RECOMENDACIÓN: Confirme que los datos proporcionados coincidan con el registro original."
        },
        "poderes": {
            "nombre_base": "poderes_notariales",
            "titulo": "GUÍA DE PREPARACIÓN: ACTOS NOTARIALES",
            "requisitos": [
                "Identificación oficial vigente del otorgante.",
                "Datos completos de la persona que recibirá la representación.",
                "Descripción clara de las facultades."
            ],
            "nota": "RECOMENDACIÓN: Redacte con claridad el propósito del trámite."
        }
    }

    config = tramites_config.get(datos.categoria_tramite, tramites_config["pasaporte"])

    elementos.append(Paragraph(config["titulo"], estilo_seccion))
    elementos.append(Spacer(1, 4))

    datos_tabla = [
        [Paragraph("<b>Titular / Solicitante:</b>", estilo_texto), Paragraph(f"{p1} {p2} {a1} {a2}", estilo_texto)],
        [Paragraph("<b>Nacimiento:</b>", estilo_texto), Paragraph(f"{fecha_formateada} ({lugar})", estilo_texto)],
        [Paragraph("<b>Domicilio USA:</b>", estilo_texto), Paragraph(f"{direccion}", estilo_texto)],
        [Paragraph("<b>Teléfono:</b>", estilo_texto), Paragraph(f"{telefono}", estilo_texto)]
    ]

    if ex1 or ex2:
        datos_tabla.append([Paragraph("<b>Referencia Extra:</b>", estilo_texto), Paragraph(f"{ex1} | {ex2}", estilo_texto)])

    t = Table(datos_tabla, colWidths=[110, 420])
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
        "SAVE MÉXICO AYUDAR | Asistencia Privada de Gestión Documental.<br/>"
        "Operado por MAY ROGA LLC, Florida. El alcance legal se limita exclusivamente al comprador en USA.<br/>"
        "Este documento es una guía privada de organización de expedientes y no constituye representación oficial."
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
