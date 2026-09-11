import os,re,json,secrets,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta

import stripe,httpx
from fastapi import FastAPI,HTTPException,Request,UploadFile,File,Depends
from fastapi.responses import FileResponse,HTMLResponse
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ============================================================
# CONFIG
# ============================================================

APP_URL=os.getenv(
    "APP_URL",
    "https://save-mexico-ayudar.onrender.com"
).rstrip("/")

DEV_USER=os.getenv(
    "DEV_USER",
    os.getenv("ADMIN_USERNAME","admin")
)

DEV_PASS=os.getenv(
    "DEV_PASS",
    os.getenv("ADMIN_PASSWORD","securepassword")
)

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")

PRICE_IDS={
    "daily":os.getenv(
        "STRIPE_PRICE_ID_DAILY",
        os.getenv("STRIPE_PRICE_ID1","")
    ),
    "monthly":os.getenv(
        "STRIPE_PRICE_ID_MONTHLY",
        os.getenv("STRIPE_PRICE_ID2","")
    ),
    "annual":os.getenv(
        "STRIPE_PRICE_ID_ANNUAL",""
    )
}

stripe.api_key=STRIPE_SECRET_KEY

BASE_DIR=Path(__file__).resolve().parent
STATIC_DIR=BASE_DIR/"static"
DATA_DIR=BASE_DIR/"data"
SALIDAS_DIR=BASE_DIR/"salidas"

DATA_DIR.mkdir(exist_ok=True)
SALIDAS_DIR.mkdir(exist_ok=True)

ACCESS_FILE=DATA_DIR/"access.json"

app=FastAPI(
    title="SAVE MÉXICO AYUDAR",
    version="8.0"
)

security=HTTPBasic()

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static"
    )


# ============================================================
# MODELOS
# ============================================================

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
    documentos_tenidos:list[str]=Field(default_factory=list)
    documentos_faltantes:list[str]=Field(default_factory=list)
    datos_extraidos:list[dict]=Field(default_factory=list)
    estado_posterior:str="pendiente"
    extra_1:str=""
    extra_2:str=""
    confirmado:bool=False


class PreguntaRequest(BaseModel):
    pregunta:str
    contexto:str=""


class ResultadoRequest(BaseModel):
    categoria_tramite:str=""
    resultado:str=""
    comentario:str=""


class StripeCheckoutRequest(BaseModel):
    plan:str


class AccesoRequest(BaseModel):
    email:str=""
    session_id:str=""


# ============================================================
# UTILIDADES
# ============================================================

def ahora():
    return datetime.now(timezone.utc)


def cargar_json(path,default):
    if not path.exists():
        return default
    try:
        with open(path,"r",encoding="utf-8") as f:
            data=json.load(f)
        return data
    except Exception:
        return default


def guardar_json(path,data):
    tmp=path.with_suffix(".tmp")
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
    tmp.replace(path)


def cargar_access():
    data=cargar_json(ACCESS_FILE,{})
    return data if isinstance(data,dict) else {}


def guardar_access(data):
    guardar_json(ACCESS_FILE,data)


def email_clean(email):
    return (email or "").strip().lower()


def text(v):
    if v is None:
        return ""
    return re.sub(r"\s+"," ",str(v).replace("\x00"," ")).strip()


def hash_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def crear_token():
    return secrets.token_urlsafe(48)


def validar_archivo(nombre):
    nombre=os.path.basename(nombre)
    if (
        not nombre.lower().endswith(".pdf")
        or ".." in nombre
        or "/" in nombre
        or "\\" in nombre
    ):
        raise HTTPException(
            400,
            "Nombre de archivo no válido."
        )
    return nombre


def acceso_activo(item):
    if not item or not item.get("active"):
        return False

    exp=item.get("expires_at")

    if exp:
        try:
            if ahora().timestamp()>=float(exp):
                return False
        except Exception:
            return False

    return True


def guardar_acceso(
    email,
    plan="",
    session_id="",
    subscription_id="",
    expires_at=None
):
    email=email_clean(email)

    if not email:
        return False

    data=cargar_access()

    token=crear_token()

    data[email]={
        "active":True,
        "email":email,
        "plan":plan or "",
        "session_id":session_id or "",
        "subscription_id":subscription_id or "",
        "expires_at":expires_at,
        "token_hash":hash_token(token),
        "updated_at":ahora().isoformat()
    }

    guardar_access(data)

    return token


def activar_servicio_usuario(
    email,
    session_id="",
    plan="",
    subscription_id="",
    expires_at=None
):
    return guardar_acceso(
        email,
        plan,
        session_id,
        subscription_id,
        expires_at
    )


def desactivar_servicio_usuario(email):
    email=email_clean(email)
    data=cargar_access()

    if email in data:
        data[email]["active"]=False
        data[email]["updated_at"]=ahora().isoformat()
        guardar_access(data)

    return True


def acceso_por_email(email):
    email=email_clean(email)
    item=cargar_access().get(email)
    return acceso_activo(item)


def acceso_por_token(token):
    if not token:
        return None

    h=hash_token(token)
    data=cargar_access()

    for email,item in data.items():
        if item.get("token_hash")==h and acceso_activo(item):
            return {
                "type":"customer",
                "email":email,
                "data":item
            }

    return None


# ============================================================
# AUTORIZACIÓN
# ADMIN = BASIC AUTH
# CLIENTE = COOKIE HttpOnly
# ============================================================

def autenticar(
    request:Request,
    credentials:HTTPBasicCredentials|None=None
):
    # ADMINISTRADOR
    if credentials:
        if (
            secrets.compare_digest(
                credentials.username,
                DEV_USER
            )
            and
            secrets.compare_digest(
                credentials.password,
                DEV_PASS
            )
        ):
            return {
                "type":"admin",
                "username":credentials.username
            }

    # CLIENTE STRIPE
    token=request.cookies.get(
        "save_access_token"
    )

    cliente=acceso_por_token(token)

    if cliente:
        return cliente

    raise HTTPException(
        status_code=401,
        detail="Acceso no autorizado.",
        headers={
            "WWW-Authenticate":"Basic"
        }
    )


async def require_access(
    request:Request,
    credentials:HTTPBasicCredentials=Depends(security)
):
    return autenticar(
        request,
        credentials
    )


def require_admin(
    credentials:HTTPBasicCredentials=Depends(security)
):
    if not (
        secrets.compare_digest(
            credentials.username,
            DEV_USER
        )
        and
        secrets.compare_digest(
            credentials.password,
            DEV_PASS
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales administrativas incorrectas.",
            headers={
                "WWW-Authenticate":"Basic"
            }
        )

    return credentials.username


# ============================================================
# HOME
# ============================================================

@app.get("/",response_class=HTMLResponse)
async def home():
    index=STATIC_DIR/"index.html"

    if not index.exists():
        return HTMLResponse(
            "<h1>SAVE MÉXICO AYUDAR</h1>"
            "<p>index.html no encontrado.</p>",
            status_code=404
        )

    return HTMLResponse(
        index.read_text(encoding="utf-8")
    )


# ============================================================
# LOGIN ADMIN
# ============================================================

@app.post("/api/admin-login")
async def admin_login(
    credentials:HTTPBasicCredentials=Depends(security)
):
    require_admin(credentials)

    return {
        "status":"success",
        "admin":True
    }


# ============================================================
# STRIPE CHECKOUT
# ============================================================

@app.post("/api/create-checkout-session")
async def create_checkout_session(
    data:StripeCheckoutRequest
):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            500,
            "STRIPE_SECRET_KEY no está configurada."
        )

    plan=text(data.plan).lower()

    if plan not in PRICE_IDS:
        raise HTTPException(
            400,
            "Plan no válido."
        )

    price_id=PRICE_IDS.get(plan)

    if not price_id:
        raise HTTPException(
            500,
            f"Price ID de {plan} no configurado en Render."
        )

    try:
        price=stripe.Price.retrieve(price_id)

        recurring=price.get("recurring")
        mode="subscription" if recurring else "payment"

        params={
            "line_items":[
                {
                    "price":price_id,
                    "quantity":1
                }
            ],
            "mode":mode,
            "success_url":(
                f"{APP_URL}/"
                "?success=true"
                "&session_id={CHECKOUT_SESSION_ID}"
            ),
            "cancel_url":(
                f"{APP_URL}/?canceled=true"
            ),
            "metadata":{
                "app":"SAVE_MEXICO_AYUDAR",
                "plan":plan
            }
        }

        if mode=="subscription":
            params["subscription_data"]={
                "metadata":{
                    "app":"SAVE_MEXICO_AYUDAR",
                    "plan":plan
                }
            }

        session=stripe.checkout.Session.create(
            **params
        )

        return {
            "status":"success",
            "checkout_url":session.url,
            "session_id":session.id,
            "mode":mode,
            "plan":plan
        }

    except stripe.error.StripeError as e:
        raise HTTPException(
            400,
            f"Stripe: {str(e)}"
        )


# ============================================================
# VERIFICAR PAGO
# CREA COOKIE DE CLIENTE
# ============================================================

@app.get("/api/verify-payment")
async def verify_payment(
    session_id:str,
    request:Request
):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            500,
            "Stripe no está configurado."
        )

    if not session_id:
        raise HTTPException(
            400,
            "Falta session_id."
        )

    try:
        session=stripe.checkout.Session.retrieve(
            session_id
        )

        if session.get("payment_status") not in (
            "paid",
            "no_payment_required"
        ):
            return {
                "active":False,
                "status":session.get(
                    "payment_status"
                )
            }

        email=""

        customer=session.get(
            "customer_details"
        ) or {}

        email=customer.get("email","") or session.get(
            "customer_email",""
        )

        email=email_clean(email)

        metadata=session.get(
            "metadata"
        ) or {}

        plan=metadata.get("plan","")

        subscription_id=session.get(
            "subscription"
        ) or ""

        expires_at=None

        if subscription_id:

            try:
                sub=stripe.Subscription.retrieve(
                    subscription_id
                )

                if sub.get("status") not in (
                    "active",
                    "trialing"
                ):
                    return {
                        "active":False,
                        "email":email,
                        "status":sub.get("status")
                    }

                expires_at=sub.get(
                    "current_period_end"
                )

            except Exception:
                pass

        else:
            # Servicio individual:
            # acceso durante 24 horas.
            expires_at=(
                ahora()+timedelta(days=1)
            ).timestamp()

        token=activar_servicio_usuario(
            email=email,
            session_id=session.id,
            plan=plan,
            subscription_id=subscription_id,
            expires_at=expires_at
        )

        if not token:
            raise HTTPException(
                400,
                "Stripe no proporcionó un correo válido."
            )

        response=HTMLResponse(
            content=json.dumps({
                "active":True,
                "email":email,
                "plan":plan,
                "session_id":session.id
            })
        )

        response.set_cookie(
            key="save_access_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=(
                31536000
                if subscription_id
                else 86400
            ),
            path="/"
        )

        return response

    except stripe.error.StripeError as e:
        raise HTTPException(
            400,
            f"Stripe: {str(e)}"
        )


# ============================================================
# WEBHOOK STRIPE
# ============================================================

@app.post("/api/webhook/stripe")
async def stripe_webhook(
    request:Request
):
    payload=await request.body()
    signature=request.headers.get(
        "stripe-signature"
    )

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            500,
            "STRIPE_WEBHOOK_SECRET no configurado."
        )

    if not signature:
        raise HTTPException(
            400,
            "Falta Stripe-Signature."
        )

    try:
        event=stripe.Webhook.construct_event(
            payload,
            signature,
            STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(
            400,
            "Payload Stripe inválido."
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            400,
            "Firma Stripe inválida."
        )

    tipo=event.get("type")

    # --------------------------------------------------------
    # CHECKOUT COMPLETADO
    # --------------------------------------------------------

    if tipo in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded"
    ):

        session=event["data"]["object"]

        customer=session.get(
            "customer_details"
        ) or {}

        email=email_clean(
            customer.get("email","")
            or session.get(
                "customer_email",""
            )
        )

        metadata=session.get(
            "metadata"
        ) or {}

        plan=metadata.get(
            "plan",""
        )

        subscription_id=session.get(
            "subscription"
        ) or ""

        expires_at=None

        if subscription_id:

            try:
                sub=stripe.Subscription.retrieve(
                    subscription_id
                )

                expires_at=sub.get(
                    "current_period_end"
                )

            except Exception:
                pass

        else:
            expires_at=(
                ahora()+timedelta(days=1)
            ).timestamp()

        if email:
            activar_servicio_usuario(
                email=email,
                session_id=session.get("id",""),
                plan=plan,
                subscription_id=subscription_id,
                expires_at=expires_at
            )

    # --------------------------------------------------------
    # SUSCRIPCIÓN ACTUALIZADA
    # --------------------------------------------------------

    elif tipo=="customer.subscription.updated":

        sub=event["data"]["object"]

        customer_id=sub.get("customer")

        try:
            customer=stripe.Customer.retrieve(
                customer_id
            )

            email=email_clean(
                customer.get("email","")
            )

            if sub.get("status") in (
                "active",
                "trialing"
            ):
                activar_servicio_usuario(
                    email=email,
                    subscription_id=sub.get("id",""),
                    expires_at=sub.get(
                        "current_period_end"
                    )
                )
            else:
                desactivar_servicio_usuario(
                    email
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # SUSCRIPCIÓN ELIMINADA
    # --------------------------------------------------------

    elif tipo=="customer.subscription.deleted":

        sub=event["data"]["object"]

        try:
            customer=stripe.Customer.retrieve(
                sub.get("customer")
            )

            email=email_clean(
                customer.get("email","")
            )

            desactivar_servicio_usuario(
                email
            )

        except Exception:
            pass

    return {
        "status":"success"
    }


# ============================================================
# COMPROBAR ACCESO
# ============================================================

@app.post("/api/check-access")
async def check_access(
    request:Request,
    data:AccesoRequest
):
    token=request.cookies.get(
        "save_access_token"
    )

    cliente=acceso_por_token(token)

    if cliente:
        return {
            "active":True,
            "email":cliente["email"],
            "plan":cliente["data"].get(
                "plan",""
            )
        }

    email=email_clean(data.email)

    return {
        "active":acceso_por_email(email),
        "email":email
    }


# ============================================================
# FICHA
# ============================================================

@app.post("/api/ficha-tramite")
async def ficha_tramite(
    data:DatosTramite,
    access=Depends(require_access)
):
    if not text(data.categoria_tramite):
        raise HTTPException(
            400,
            "Debe seleccionar un trámite."
        )

    return {
        "status":"success",
        "message":"Datos recibidos correctamente."
    }


# ============================================================
# EXTRAER PDF
# ============================================================

@app.post("/api/extraer-pdf")
async def extraer_pdf(
    archivo:UploadFile=File(...),
    access=Depends(require_access)
):
    if not archivo.filename:
        raise HTTPException(
            400,
            "Archivo no válido."
        )

    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(
            400,
            "Solo se permiten archivos PDF."
        )

    contenido=await archivo.read()

    if not contenido:
        raise HTTPException(
            400,
            "El PDF está vacío."
        )

    temp=DATA_DIR/(
        "tmp_"+secrets.token_hex(8)+".pdf"
    )

    try:
        temp.write_bytes(contenido)

        reader=PdfReader(str(temp))
        paginas=[]

        for page in reader.pages:
            try:
                paginas.append(
                    page.extract_text() or ""
                )
            except Exception:
                paginas.append("")

        return {
            "status":"success",
            "texto":"\n".join(paginas).strip(),
            "paginas":len(reader.pages)
        }

    except Exception as e:
        raise HTTPException(
            400,
            f"No se pudo leer el PDF: {str(e)}"
        )

    finally:
        try:
            temp.unlink(missing_ok=True)
        except Exception:
            pass


# ============================================================
# GEMINI
# ============================================================

@app.post("/api/pregunta")
async def pregunta(
    data:PreguntaRequest,
    access=Depends(require_access)
):
    pregunta=text(data.pregunta)

    if not pregunta:
        raise HTTPException(
            400,
            "Escribe una pregunta."
        )

    if not GEMINI_API_KEY:
        return {
            "status":"success",
            "respuesta":(
                "El asistente Gemini no está "
                "configurado actualmente."
            )
        }

    prompt=f"""
Eres el asistente de SAVE MÉXICO AYUDAR.

Ayudas a organizar información y documentos
relacionados con trámites mexicanos.

Habla de manera clara, sencilla y directa.
No amontones información.
Usa listas cuando sea útil.

No inventes requisitos.
No afirmes ser una autoridad mexicana.
No prometas que un trámite será aprobado.
Cuando un requisito pueda cambiar, indica que
debe confirmarse con el consulado correspondiente.

CONTEXTO:
{text(data.contexto)}

PREGUNTA:
{pregunta}
""".strip()

    url=(
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.0-flash:generateContent"
        f"?key={GEMINI_API_KEY}"
    )

    payload={
        "contents":[
            {
                "parts":[
                    {
                        "text":prompt
                    }
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(
            timeout=45
        ) as client:
            r=await client.post(
                url,
                json=payload
            )

        if r.status_code!=200:
            raise HTTPException(
                502,
                "Gemini no respondió correctamente."
            )

        j=r.json()

        respuesta=(
            j.get("candidates",[{}])[0]
            .get("content",{})
            .get("parts",[{}])[0]
            .get("text","")
        )

        return {
            "status":"success",
            "respuesta":(
                respuesta
                or "No pude obtener una respuesta."
            )
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            502,
            f"Error con Gemini: {str(e)}"
        )


# ============================================================
# GENERAR GUÍA
# ============================================================

@app.post("/api/generar-guia-consular")
async def generar_guia(
    data:DatosTramite,
    access=Depends(require_access)
):
    categoria=text(data.categoria_tramite)
    nombre=text(data.primer_nombre)
    apellido=text(data.primer_apellido)
    fecha=text(data.fecha_nacimiento)
    lugar=text(data.lugar_nacimiento)

    if not categoria:
        raise HTTPException(
            400,
            "Debe seleccionar un trámite."
        )

    if not nombre:
        raise HTTPException(
            400,
            "Falta el nombre."
        )

    if not apellido:
        raise HTTPException(
            400,
            "Falta el primer apellido."
        )

    if not fecha:
        raise HTTPException(
            400,
            "Falta la fecha de nacimiento."
        )

    if not lugar:
        raise HTTPException(
            400,
            "Falta el lugar de nacimiento."
        )

    completo=" ".join(
        x for x in [
            nombre,
            text(data.segundo_nombre),
            apellido,
            text(data.segundo_apellido)
        ] if x
    )

    archivo=(
        "SAVE_MEXICO_"
        +datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        +"_"+secrets.token_hex(4)
        +".pdf"
    )

    ruta=SALIDAS_DIR/archivo

    try:
        pdf=canvas.Canvas(
            str(ruta),
            pagesize=letter
        )

        ancho,alto=letter
        y=alto-50

        def line(txt,size=10,space=17):
            nonlocal y

            txt=text(txt)

            pdf.setFont(
                "Helvetica",
                size
            )

            partes=[
                txt[i:i+105]
                for i in range(
                    0,
                    len(txt),
                    105
                )
            ] or [""]

            for parte in partes:

                if y<55:
                    pdf.showPage()
                    y=alto-50

                pdf.drawString(
                    45,
                    y,
                    parte
                )

                y-=space

        pdf.setFont(
            "Helvetica-Bold",
            16
        )

        pdf.drawString(
            45,
            y,
            "SAVE MÉXICO AYUDAR"
        )

        y-=30

        line(
            f"Guía de preparación: {categoria}",
            13,
            22
        )

        y-=5

        line(
            f"Nombre: {completo}"
        )

        line(
            f"Fecha de nacimiento: {fecha}"
        )

        line(
            f"Lugar de nacimiento: {lugar}"
        )

        line(
            f"Nacionalidad: {text(data.nacionalidad) or 'Mexicana'}"
        )

        line(
            f"Dirección en EE.UU.: {text(data.direccion_usa)}"
        )

        line(
            f"Teléfono: {text(data.telefono)}"
        )

        if data.consulado:
            line(
                f"Consulado: {text(data.consulado)}"
            )

        if data.cita:
            line(
                f"Cita: {text(data.cita)}"
            )

        y-=8

        line(
            "DOCUMENTOS QUE YA TIENE",
            11,
            18
        )

        if data.documentos_tenidos:
            for d in data.documentos_tenidos:
                line("• "+text(d))
        else:
            line("No se indicaron documentos.")

        y-=7

        line(
            "DOCUMENTOS QUE FALTAN",
            11,
            18
        )

        if data.documentos_faltantes:
            for d in data.documentos_faltantes:
                line("• "+text(d))
        else:
            line("No se indicaron documentos faltantes.")

        if data.extra_1:
            y-=8
            line(
                "INFORMACIÓN ADICIONAL",
                11,
                18
            )
            line(data.extra_1)

        if data.extra_2:
            line(data.extra_2)

        y-=10

        line(
            "Esta guía sirve para organizar información "
            "y documentos. No sustituye las instrucciones "
            "oficiales del Gobierno de México o del "
            "consulado correspondiente."
        )

        pdf.save()

    except Exception as e:

        try:
            ruta.unlink(missing_ok=True)
        except Exception:
            pass

        raise HTTPException(
            500,
            f"No se pudo generar el PDF: {str(e)}"
        )

    return {
        "status":"success",
        "archivo":f"/descargar/{archivo}",
        "nombre_archivo":archivo
    }


# ============================================================
# DESCARGAR PDF
# ============================================================

@app.get("/descargar/{nombre_archivo}")
async def descargar(
    nombre_archivo:str,
    access=Depends(require_access)
):
    nombre_archivo=validar_archivo(
        nombre_archivo
    )

    ruta=SALIDAS_DIR/nombre_archivo

    if not ruta.exists():
        raise HTTPException(
            404,
            "Archivo no encontrado."
        )

    return FileResponse(
        str(ruta),
        media_type="application/pdf",
        filename="Mi_Tramite_Save_Mexico.pdf"
    )


# ============================================================
# RESULTADO
# ============================================================

@app.post("/api/resultado-tramite")
async def resultado_tramite(
    data:ResultadoRequest,
    access=Depends(require_access)
):
    archivo=DATA_DIR/"resultados.json"

    registros=cargar_json(
        archivo,
        []
    )

    if not isinstance(registros,list):
        registros=[]

    registros.append({
        "email":access.get("email","")
        if isinstance(access,dict)
        else "",
        "categoria":text(
            data.categoria_tramite
        ),
        "resultado":text(
            data.resultado
        ),
        "comentario":text(
            data.comentario
        ),
        "fecha":ahora().isoformat()
    })

    try:
        guardar_json(
            archivo,
            registros
        )
    except Exception:
        pass

    return {
        "status":"success",
        "message":"Resultado guardado."
    }


# ============================================================
# CERRAR SESIÓN CLIENTE
# ============================================================

@app.post("/api/logout")
async def logout():
    response=HTMLResponse(
        json.dumps({
            "status":"success"
        })
    )

    response.delete_cookie(
        "save_access_token",
        path="/"
    )

    return response


# ============================================================
# ESTADO
# ============================================================

@app.get("/api/estado")
async def estado():

    return {
        "app":"SAVE MÉXICO AYUDAR",
        "version":"8.0",
        "stripe":bool(
            STRIPE_SECRET_KEY
        ),
        "webhook":bool(
            STRIPE_WEBHOOK_SECRET
        ),
        "gemini":bool(
            GEMINI_API_KEY
        ),
        "planes":{
            "daily":bool(
                PRICE_IDS["daily"]
            ),
            "monthly":bool(
                PRICE_IDS["monthly"]
            ),
            "annual":bool(
                PRICE_IDS["annual"]
            )
        }
    }


# ============================================================
# START
# ============================================================

if __name__=="__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(
            os.getenv("PORT","8000")
        ),
        reload=False
    )
