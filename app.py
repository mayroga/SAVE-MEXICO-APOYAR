# TRAMO 1: INICIO
# app.py (Suite Nacional + Pasarela Stripe + Control de Cuotas + Bypass Dev)
import os, io, re
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Depends, Cookie
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import date
import stripe

import consular_engine as engine

# Inyección de credenciales desde las variables de Render
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
PRICE_ID_DIARIO = os.getenv("STRIPE_PRICE_ID1")   # $15.99 Pago único
PRICE_ID_MENSUAL = os.getenv("STRIPE_PRICE_ID2")  # $25.99 Suscripción

ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

app = FastAPI(title=engine.APP, version=engine.VERSION)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Repositorio temporal en memoria para el control arancelario de accesos
# Formato: {"token_id": {"tipo": "diario/mensual/dev", "fecha": "YYYY-MM-DD", "usos_hoy": 0}}
SESIONES_PAGADAS = {}

class ExpedientePerfil(BaseModel):
    nombre_completo: Optional[str] = ""
    fecha_nacimiento: Optional[str] = ""
    edad: Optional[str] = ""
    origen_mexico: Optional[str] = ""
    direccion_usa: Optional[str] = ""
    telefono: Optional[str] = ""
    estado: Optional[str] = "Otro"
    nacionalidad: Optional[str] = "mexicana"

class Inicio(BaseModel):
    perfil: Optional[ExpedientePerfil] = None
    texto: str = ""

class Continuacion(BaseModel):
    caso: str
    pregunta_id: str = ""
    respuesta: Any = ""
    respuestas: Dict[str, Any] = Field(default_factory=dict)
    perfil: Optional[ExpedientePerfil] = None

class Seleccion(BaseModel):
    caso: str
    perfil: Optional[ExpedientePerfil] = None
    respuestas: Dict[str, Any] = Field(default_factory=dict)

class LoginDev(BaseModel):
    username: str
    password: str
# TRAMO 1: FIN
# TRAMO 2: INICIO
def verificar_acceso_paywall(token: Optional[str] = Cookie(None)):
    if not token or token not in SESIONES_PAGADAS:
        raise HTTPException(402, "Muro de pago activo. Por favor procesa tu contribución en Stripe para continuar.")
    
    sesion = SESIONES_PAGADAS[token]
    hoy = str(date.today())
    
    # Reiniciar contadores si cambió el día de uso
    if sesion.get("fecha") != hoy:
        sesion["fecha"] = hoy
        sesion["usos_hoy"] = 0
        
    if sesion["tipo"] == "dev":
        return token # El desarrollador tiene cuotas infinitas de prueba
        
    if sesion["tipo"] == "diario" and sesion["usos_hoy"] >= 1:
        raise HTTPException(429, "Has agotado tu consulta diaria de Hoja de Ruta. Regresa mañana o adquiere el pase mensual.")
        
    if sesion["tipo"] == "mensual" and sesion["usos_hoy"] >= 4:
        raise HTTPException(429, "Límite de seguridad alcanzado: Máximo 4 consultas de Hoja de Ruta por día en el plan mensual.")
        
    return token

@app.post("/api/checkout")
def crear_checkout_stripe(plan: str):
    price_id = PRICE_ID_DIARIO if plan == "diario" else PRICE_ID_MENSUAL
    mode = "payment" if plan == "diario" else "subscription"
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{"price": price_id, "quantity": 1}],
            mode=mode,
            success_url="https://onrender.com{CHECKOUT_SESSION_ID}",
            cancel_url="https://onrender.com",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(400, f"Error al inicializar pasarela: {e}")

@app.post("/api/login-developer")
def login_developer_bypass(x: LoginDev):
    # Validamos que tus claves de Render coincidan exactamente
    if x.username == ADMIN_USER and x.password == ADMIN_PASS:
        # Generamos una llave de entrada limpia y segura sin usar urandom corrupto
        token_dev = f"dev_token_autorizado_{x.username}"
        
        # Registramos tu sesión en el Cerebro del servidor con cuotas infinitas gratis
        SESIONES_PAGADAS[token_dev] = {
            "tipo": "dev", 
            "fecha": str(date.today()), 
            "usos_hoy": 0
        }
        
        # Creamos la respuesta de autorización nativa para el navegador
        from fastapi.responses import JSONResponse
        response = JSONResponse(content={"ok": True, "token": token_dev})
        
        # Inyectamos la cookie de forma limpia y transparente
        response.set_cookie(
            key="token", 
            value=token_dev, 
            max_age=86400, # Válida por 24 horas continuas
            path="/",
            samesite="lax"
        )
        return response
        
    raise HTTPException(401, "Credenciales de desarrollador inválidas.")

# TRAMO 2: FIN
# TRAMO 3: INICIO
@app.post("/api/stripe-webhook")
async def stripe_webhook_capture(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400, f"Webhook Error Signature: {e}")
        
    if event["type"] in ["checkout.session.completed", "invoice.payment_succeeded"]:
        session = event["data"]["object"]
        session_id = session.get("id") or session.get("checkout_session")
        
        plan_tipo = "diario"
        if session.get("subscription") or "sub_" in str(session_id):
            plan_tipo = "mensual"
            
        SESIONES_PAGADAS[session_id] = {"tipo": plan_tipo, "fecha": str(date.today()), "usos_hoy": 0}
        
    return {"status": "success"}

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/catalogo")
def api_catalogo(token: str = Depends(verificar_acceso_paywall)):
    return engine.catalogo()

@app.post("/api/seleccionar-caso")
def api_seleccionar(x: Seleccion, token: str = Depends(verificar_acceso_paywall)):
    try:
        p_dict = x.perfil.dict() if x.perfil else {}
        return engine.seleccionar_caso(x.caso, p_dict, x.respuestas)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/continuar")
def api_continuar(x: Continuacion, token: str = Depends(verificar_acceso_paywall)):
    try:
        res = dict(x.respuestas or {})
        p_dict = x.perfil.dict() if x.perfil else {}
        return engine.continuar(x.caso, res, p_dict, x.pregunta_id, x.respuesta)
    except Exception as e:
        raise HTTPException(400, str(e))
# TRAMO 3: FIN
# TRAMO 4: INICIO
def construir_pdf(r):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=letter)
    c.setTitle("MEXICANO APOYA MEXICANO - Hoja de Ruta")
    
    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.05, 0.25, 0.20) # Verde SRE Institucional Nacional
    c.drawString(55, 740, "MEXICANO APOYA MEXICANO")
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(55, 718, "HOJA DE RUTA CONSULAR Y EXPEDIENTE AUTOMATIZADO")
    c.line(55, 705, 555, 705)
    
    # 1. Datos del Ciudadano
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, 680, "1. INFORMACIÓN DECLARADA POR EL SOLICITANTE")
    c.setFont("Helvetica", 10)
    c.drawString(65, 660, f"Nombre Completo: {r.get('nombre_ciudadano', '')}")
    c.drawString(65, 642, f"Fecha de Nacimiento: {r.get('fecha_nacimiento', '')}")
    c.drawString(65, 624, f"Lugar de Origen (México): {r.get('origen_mexico', '')}")
    c.drawString(65, 606, f"Dirección en EE. UU.: {r.get('direccion_usa', '')}")
    c.drawString(65, 588, f"Teléfono de Contacto: {r.get('telefono_ciudadano', '')}")
    
    # 2. Detalles del Trámite
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, 560, f"2. TRÁMITE EVALUADO: {r.get('nombre_tramite', '').upper()}")
    c.setFont("Helvetica", 10)
    c.drawString(65, 540, f"Estatus de Validación: {r.get('estado', '')}")
    c.drawString(65, 522, f"Estatus de Cita Consular: {r.get('cita_estatus', '')}")
    c.drawString(65, 504, f"Arancel Consular de Ventanilla: {r.get('pago_estimado', '')}")
    
    # 3. Asignación de Oficina
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, 470, "3. JURISDICCIÓN CONSULAR ASIGNADA")
    c.setFont("Helvetica", 10)
    c.drawString(65, 450, f"Sede Representativa: {r.get('consulado_nombre', '')}")
    c.drawString(65, 432, f"Dirección Física: {r.get('consulado_direccion', '')}")
    c.drawString(65, 414, f"Teléfono de Emergencia Protección: {r.get('consulado_telefono', '')}")
    
    # 4. Requisitos y Faltantes
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, 380, "4. REQUISITOS OFICIALES REQUERIDOS")
    y = 360
    for req in r.get("requisitos_oficiales", []):
        c.setFont("Helvetica", 9)
        c.drawString(70, y, f"• {req}")
        y -= 16
        
    faltantes = r.get("faltantes", [])
    if faltantes:
        y -= 10
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.7, 0.1, 0.1)
        c.drawString(55, y, "5. ALERTAS CRÍTICAS Y DOCUMENTACIÓN FALTANTE:")
        y -= 18
        for f in faltantes:
            c.setFont("Helvetica", 9)
            c.drawString(70, y, f"[ ] {f}")
            y -= 16
            
    # Pie de Deslinde Legal Regulado
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(55, 45, "Deslinde Legal: Mexicano Apoya Mexicano es un desarrollo independiente propiedad de MAY ROGA LLC.")
    c.drawString(55, 35, "No posee vinculación jurídica con la SRE ni el INE. Verifique siempre los requisitos vigentes en ventanilla.")
    c.save()
    out.seek(0)
    return out

@app.post("/api/pdf-preview")
def api_pdf_preview(r: Dict[str, Any], token: str = Depends(verificar_acceso_paywall)):
    try:
        pdf = construir_pdf(r)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'inline; filename="Hoja_de_Ruta_Preliminar.pdf"',
                "Cache-Control": "no-store"
            }
        )
    except Exception as e:
        raise HTTPException(400, f"Error al generar la vista previa: {e}")

@app.post("/api/pdf")
def api_pdf(r: Dict[str, Any], token: str = Depends(verificar_acceso_paywall)):
    try:
        # Descontar uso de la cuota contratada tras una exportación exitosa de expediente
        if token in SESIONES_PAGADAS and SESIONES_PAGADAS[token]["tipo"] != "dev":
            SESIONES_PAGADAS[token]["usos_hoy"] += 1
            
        pdf = construir_pdf(r)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="Hoja_de_Ruta_Consular.pdf"',
                "Cache-Control": "no-store"
            }
        )
    except Exception as e:
        raise HTTPException(400, f"Error al generar el PDF: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
# TRAMO 4: FIN
