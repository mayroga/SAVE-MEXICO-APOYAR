import os,json,secrets,uuid
from pathlib import Path
from typing import Any,Optional
from datetime import datetime,timezone

import stripe
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,HTMLResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static"
DATA=BASE/"data"
OUT=BASE/"descargas"
STATIC.mkdir(parents=True,exist_ok=True)
DATA.mkdir(parents=True,exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)

JSON_FILE=DATA/"tramites.json"
APP_URL=os.getenv("APP_URL","https://save-mexico-ayudar.onrender.com").rstrip("/")
ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
PRICE1=os.getenv("STRIPE_PRICE_ID1","")
PRICE2=os.getenv("STRIPE_PRICE_ID2","")
stripe.api_key=STRIPE_SECRET_KEY

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="5.0.0")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")

TOKENS={}
PAYMENTS={}

class Payload(BaseModel):
    tramite:Optional[str]=None
    modalidad:Optional[str]=None
    datos_personales:dict[str,Any]={}
    respuestas:dict[str,Any]={}
    documentos:list[Any]=[]
    documentos_estados:dict[str,str]={}
    documentos_disponibles:list[str]=[]
    documentos_faltantes:list[str]=[]
    documentos_dudosos:list[str]=[]
    consulado:dict[str,Any]={}
    resultado:dict[str,Any]={}
    idioma:str="es"

class Login(BaseModel):
    username:str
    password:str

class Checkout(BaseModel):
    price_id:Optional[str]=None
    pase_tipo:Optional[int]=None

def load_json():
    if not JSON_FILE.exists():
        raise HTTPException(500,"No se encontró data/tramites.json")
    try:
        return json.loads(JSON_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(500,f"Error leyendo tramites.json: {e}")

def token_cookie(response,token):
    response.set_cookie(
        "save_access_token",token,max_age=60*60*24*365,
        httponly=True,samesite="lax",secure=True
    )

def has_access(request:Request):
    token=request.cookies.get("save_access_token")
    return bool(token and token in TOKENS)

def require_access(request:Request):
    if not has_access(request):
        raise HTTPException(403,"Acceso no autorizado")

def find_tramite(data,tid):
    for t in data.get("tramites",[]):
        if t.get("id")==tid or t.get("codigo")==tid:
            return t
    return None

def find_modalidad(t,mid):
    if not t:return None
    for m in t.get("modalidades",[]):
        if m.get("id")==mid or m.get("codigo")==mid:
            return m
    return None

def text(v,lang="es"):
    if isinstance(v,str):return v
    if isinstance(v,dict):
        return str(v.get(lang,v.get("es",v.get("en",next(iter(v.values()),"")))))
    return str(v or "")

def norm(v):
    return str(v or "").strip().upper()

def as_list(v):
    return v if isinstance(v,list) else ([] if v is None else [v])

def condition_match(c,respuestas):
    if not c:return True
    if isinstance(c,list):return all(condition_match(x,respuestas) for x in c)
    rid=c.get("respuesta") or c.get("pregunta") or c.get("id")
    if not rid:return True
    actual=respuestas.get(rid)
    values=[norm(x) for x in as_list(actual)]
    if "incluye" in c:return norm(c["incluye"]) in values
    if "contiene" in c:return norm(c["contiene"]) in norm(actual)
    if "no_incluye" in c:return norm(c["no_incluye"]) not in values
    if "alguno_de" in c:return any(norm(x) in values for x in c["alguno_de"])
    if "todos_de" in c:return all(norm(x) in values for x in c["todos_de"])
    if "es" in c:return norm(c["es"]) in values
    if "no_es" in c:return norm(c["no_es"]) not in values
    if "distinto_de" in c:return norm(actual)!=norm(c["distinto_de"])
    if "igual_a" in c:return norm(actual)==norm(c["igual_a"])
    if "y" in c:return all(condition_match(x,respuestas) for x in c["y"])
    return True

def visible_questions(mod,respuestas):
    return [
        q for q in mod.get("preguntas",[])
        if condition_match(q.get("mostrar_si") or q.get("mostrarCuando") or q.get("condicion"),respuestas)
    ]

def all_documents(mod):
    docs=mod.get("documentos",[])
    return docs if isinstance(docs,list) else []

def classify(payload):
    data=load_json()
    t=find_tramite(data,payload.tramite)
    m=find_modalidad(t,payload.modalidad)
    if not t or not m:
        return {"estado":"REQUIERE_CONFIRMACION","mensaje":"No se pudo identificar exactamente el trámite y modalidad."}

    r=payload.respuestas
    missing=[]
    uncertain=[]
    contradictions=[]
    for q in visible_questions(m,r):
        if not q.get("obligatoria"):continue
        value=r.get(q.get("id"))
        if value in (None,"",[]):
            missing.append(text(q.get("texto") or q.get("pregunta"),payload.idioma))
        if norm(value)=="NO_SE":
            missing.append(text(q.get("texto") or q.get("pregunta"),payload.idioma))
    for d in all_documents(m):
        did=d.get("id") or d.get("codigo")
        st=payload.documentos_estados.get(did)
        if d.get("obligatorio") is True:
            if st=="NO_LO_TENGO":missing.append(text(d.get("nombre") or d.get("titulo"),payload.idioma))
            elif st=="NO_ESTOY_SEGURO":uncertain.append(text(d.get("nombre") or d.get("titulo"),payload.idioma))

    for key,val in r.items():
        if isinstance(val,list) and "NO_SE" in [norm(x) for x in val] and len(val)>1:
            contradictions.append(f"{key}: NO_SE no puede combinarse con otras opciones.")

    if contradictions:
        status="HAY_INCONSISTENCIAS"
    elif missing:
        status="FALTAN_DOCUMENTOS"
    elif uncertain:
        status="REQUIERE_CONFIRMACION"
    else:
        status="LISTO_PARA_CONFIRMAR"

    return {
        "estado":status,
        "faltantes":missing,
        "dudosos":uncertain,
        "inconsistencias":contradictions,
        "mensaje":{
            "LISTO_PARA_CONFIRMAR":"La información está organizada. Confirme los requisitos finales con la autoridad.",
            "FALTAN_DOCUMENTOS":"Hay documentos o respuestas obligatorias que todavía faltan.",
            "HAY_INCONSISTENCIAS":"Hay respuestas que deben corregirse antes de continuar.",
            "REQUIERE_CONFIRMACION":"Hay información que requiere confirmación con la autoridad."
        }[status]
    }

def clean(v):
    if isinstance(v,list):return ", ".join(clean(x) for x in v)
    if isinstance(v,dict):return "; ".join(f"{k}: {clean(x)}" for k,x in v.items())
    return str(v if v is not None else "")

def esc(v):
    return (str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            .replace('"',"&quot;").replace("'","&#39;"))

def make_pdf(p:Payload):
    data=load_json()
    t=find_tramite(data,p.tramite)
    m=find_modalidad(t,p.modalidad)
    if not t or not m:
        raise HTTPException(400,"Trámite o modalidad no válidos.")

    result=p.resultado or classify(p)
    name=clean(p.datos_personales.get("nombres",""))
    ap1=clean(p.datos_personales.get("apellido_paterno",""))
    ap2=clean(p.datos_personales.get("apellido_materno",""))
    titular=" ".join(x for x in [name,ap1,ap2] if x).strip() or "NO INDICADO"

    filename=f"guia_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
    path=OUT/filename

    styles=getSampleStyleSheet()
    title=ParagraphStyle("T",parent=styles["Title"],fontSize=18,leading=22,alignment=TA_CENTER,spaceAfter=12)
    h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=13,leading=16,spaceBefore=10,spaceAfter=7)
    body=ParagraphStyle("B",parent=styles["BodyText"],fontSize=9.5,leading=13,spaceAfter=5)
    small=ParagraphStyle("S",parent=body,fontSize=8,leading=11,textColor=colors.HexColor("#555555"))

    doc=SimpleDocTemplate(str(path),pagesize=LETTER,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42)
    story=[]
    story.append(Paragraph("SAVE MÉXICO AYUDAR",title))
    story.append(Paragraph("GUÍA INDIVIDUALIZADA DE PREPARACIÓN",h))
    story.append(Paragraph(f"<b>Trámite:</b> {esc(text(t.get('nombre') or t.get('titulo') or p.tramite,p.idioma))}",body))
    story.append(Paragraph(f"<b>Modalidad:</b> {esc(text(m.get('nombre') or m.get('titulo') or p.modalidad,p.idioma))}",body))
    story.append(Paragraph(f"<b>Titular / solicitante:</b> {esc(titular)}",body))
    story.append(Spacer(1,6))

    story.append(Paragraph("1. DATOS DEL SOLICITANTE",h))
    personal=p.datos_personales or {}
    rows=[]
    labels={
        "nombres":"Nombre(s)","apellido_paterno":"Apellido paterno",
        "apellido_materno":"Apellido materno","fecha_nacimiento":"Fecha de nacimiento",
        "lugar_nacimiento":"Lugar de nacimiento","entidad_nacimiento":"Entidad de nacimiento",
        "sexo":"Sexo","nacionalidad":"Nacionalidad",
        "estado_residencia_usa":"Estado de residencia en EE. UU.",
        "ciudad_residencia_usa":"Ciudad de residencia",
        "domicilio_usa":"Domicilio","codigo_postal":"Código postal",
        "telefono":"Teléfono","email":"Correo electrónico"
    }
    for k,v in personal.items():
        if v not in ("",None,[]):
            rows.append([Paragraph(f"<b>{esc(labels.get(k,k))}</b>",body),Paragraph(esc(clean(v)),body)])
    if rows:
        tb=Table(rows,colWidths=[190,310])
        tb.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,colors.HexColor("#cccccc")),
                                ("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f3f3f3"))]))
        story.append(tb)
    else:story.append(Paragraph("No se proporcionaron datos personales.",body))

    story.append(Paragraph("2. LO QUE USTED NECESITA HACER",h))
    selected=[]
    for q in visible_questions(m,p.respuestas):
        qid=q.get("id","")
        val=p.respuestas.get(qid)
        if val not in ("",None,[]):
            selected.append([Paragraph(f"<b>{esc(text(q.get('texto') or q.get('pregunta'),p.idioma))}</b>",body),
                             Paragraph(esc(clean(val)),body)])
    if selected:
        tb=Table(selected,colWidths=[290,210])
        tb.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,colors.HexColor("#cccccc")),
                                ("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(tb)
    else:story.append(Paragraph("No se registraron respuestas específicas.",body))

    story.append(Paragraph("3. DOCUMENTOS ESPECÍFICOS DE SU CASO",h))
    docs=all_documents(m)
    if docs:
        for d in docs:
            did=d.get("id") or d.get("codigo")
            status=p.documentos_estados.get(did,"NO INDICADO")
            title_d=text(d.get("nombre") or d.get("titulo") or did,p.idioma)
            note=text(d.get("nota") or "",p.idioma)
            if status=="LO_TENGO":mark="LO TENGO"
            elif status=="NO_LO_TENGO":mark="NO LO TENGO"
            elif status=="NO_ESTOY_SEGURO":mark="NO ESTOY SEGURO"
            elif status=="NO_APLICA":mark="NO APLICA"
            else:mark="NO INDICADO"
            extra=f"<br/><font color='#555555'>{esc(note)}</font>" if note else ""
            story.append(Paragraph(f"<b>{esc(title_d)}</b> — {esc(mark)}{extra}",body))
    else:
        story.append(Paragraph("No se encontró una lista específica para esta modalidad. Confirme directamente con la autoridad.",body))

    if p.consulado:
        story.append(Paragraph("4. CONSULADO / JURISDICCIÓN",h))
        story.append(Paragraph(
            f"<b>Estado:</b> {esc(p.consulado.get('estado',''))}<br/>"
            f"<b>Ciudad / zona:</b> {esc(p.consulado.get('ciudad',''))}",body))

    story.append(Paragraph("5. RESULTADO DE LA REVISIÓN",h))
    status=result.get("estado","REQUIERE_CONFIRMACION")
    story.append(Paragraph(f"<b>ESTATUS: {esc(status)}</b>",body))
    story.append(Paragraph(esc(result.get("mensaje","")),body))

    if result.get("faltantes"):
        story.append(Paragraph("DOCUMENTOS O DATOS FALTANTES",h))
        for x in result["faltantes"]:story.append(Paragraph("• "+esc(x),body))
    if result.get("dudosos"):
        story.append(Paragraph("DOCUMENTOS O DATOS QUE USTED NO PUDO CONFIRMAR",h))
        for x in result["dudosos"]:story.append(Paragraph("• "+esc(x),body))
    if result.get("inconsistencias"):
        story.append(Paragraph("INCONSISTENCIAS",h))
        for x in result["inconsistencias"]:story.append(Paragraph("• "+esc(x),body))

    story.append(Paragraph("6. INFORMACIÓN IMPORTANTE",h))
    story.append(Paragraph(
        "Esta guía fue elaborada con la información proporcionada por el solicitante y "
        "con la estructura documental configurada en SAVE MÉXICO AYUDAR. "
        "<b>No es un documento oficial.</b> La autoridad competente determina finalmente "
        "qué documentos acepta, si cumplen los requisitos y si procede el trámite.",body))
    story.append(Paragraph(
        "Cuando un requisito depende de la jurisdicción, del caso individual o de una "
        "determinación de la autoridad, debe confirmarse directamente con el consulado, "
        "SRE o INE correspondiente.",body))
    story.append(Spacer(1,10))
    story.append(Paragraph(
        "SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida. "
        "No es el Gobierno de México, la SRE ni el INE.",small))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",small))
    doc.build(story)
    return filename

@app.get("/",response_class=HTMLResponse)
async def home():
    f=STATIC/"index.html"
    if not f.exists():raise HTTPException(404,"No se encontró static/index.html")
    return HTMLResponse(f.read_text(encoding="utf-8"))

@app.get("/health")
async def health():
    return {"ok":True,"app":"SAVE MÉXICO AYUDAR","version":"5.0.0"}

@app.post("/api/admin-login")
async def admin_login(p:Login):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(503,"Acceso administrativo no configurado.")
    if secrets.compare_digest(p.username,ADMIN_USERNAME) and secrets.compare_digest(p.password,ADMIN_PASSWORD):
        token=secrets.token_urlsafe(48)
        TOKENS[token]={"role":"admin","created":datetime.now(timezone.utc).isoformat()}
        r=JSONResponse({"success":True,"role":"admin","access":True})
        token_cookie(r,token)
        return r
    raise HTTPException(401,"Usuario o contraseña incorrectos.")

@app.get("/api/check-access")
async def check_access(request:Request):
    token=request.cookies.get("save_access_token")
    if token in TOKENS:return {"access":True,"role":TOKENS[token].get("role","paid")}
    return {"access":False}

@app.post("/api/create-checkout-session")
async def create_checkout(p:Checkout):
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado.")
    price=p.price_id
    if not price and p.pase_tipo:
        price=PRICE1 if p.pase_tipo==1 else PRICE2 if p.pase_tipo==2 else None
    if price not in {PRICE1,PRICE2}:
        raise HTTPException(400,"Price ID no válido.")
    try:
        session=stripe.checkout.Session.create(
            mode="subscription" if price==PRICE2 else "payment",
            line_items=[{"price":price,"quantity":1}],
            success_url=f"{APP_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?payment=cancel",
            metadata={"app":"SAVE_MEXICO_AYUDAR","price_id":price}
        )
        return {"id":session.id,"url":session.url}
    except Exception as e:
        raise HTTPException(502,f"Stripe: {e}")

def provision_payment(session):
    sid=session.get("id")
    if not sid:return None
    token=secrets.token_urlsafe(48)
    mode=session.get("mode")
    TOKENS[token]={
        "role":"paid","session_id":sid,"mode":mode,
        "created":datetime.now(timezone.utc).isoformat()
    }
    PAYMENTS[sid]=TOKENS[token]
    return token

@app.get("/api/verify-payment")
async def verify_payment(session_id:str,request:Request):
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado.")
    try:
        session=stripe.checkout.Session.retrieve(session_id)
        if session.payment_status=="paid" or session.status=="complete":
            existing=PAYMENTS.get(session_id)
            token=next((k for k,v in TOKENS.items() if v.get("session_id")==session_id),None)
            if not token:token=provision_payment(session)
            r=JSONResponse({"success":True,"access":True})
            token_cookie(r,token)
            return r
        return {"success":False,"access":False,"status":session.payment_status}
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature","")
    try:
        event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400,"Webhook inválido.")
    obj=event["data"]["object"]
    if event["type"]=="checkout.session.completed":
        provision_payment(obj)
    return {"received":True}

@app.get("/api/tramites")
async def tramites(request:Request):
    require_access(request)
    data=load_json()
    return {"tramites":[
        {"id":t.get("id"),"nombre":t.get("nombre") or t.get("titulo"),"descripcion":t.get("descripcion")}
        for t in data.get("tramites",[])
    ]}

@app.get("/api/modalidades")
async def modalidades(request:Request,tramite:str):
    require_access(request)
    t=find_tramite(load_json(),tramite)
    if not t:raise HTTPException(404,"Trámite no encontrado.")
    return {"modalidades":[
        {"id":m.get("id"),"nombre":m.get("nombre") or m.get("titulo"),"descripcion":m.get("descripcion")}
        for m in t.get("modalidades",[])
    ]}

@app.get("/api/ficha-tramite")
async def ficha(request:Request,tramite:str,modalidad:str):
    require_access(request)
    data=load_json()
    t=find_tramite(data,tramite)
    m=find_modalidad(t,modalidad)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados.")
    return {
        "tramite":{"id":t.get("id"),"nombre":t.get("nombre") or t.get("titulo")},
        "modalidad":{"id":m.get("id"),"nombre":m.get("nombre") or m.get("titulo")},
        "datos_personales":data.get("datos_personales",{}),
        "preguntas":m.get("preguntas",[]),
        "documentos":m.get("documentos",[]),
        "fuentes":m.get("fuentes",[]),
        "nota":m.get("nota")
    }

@app.post("/api/perfil-tramite")
async def perfil(request:Request,p:Payload):
    require_access(request)
    data=load_json()
    t=find_tramite(data,p.tramite)
    m=find_modalidad(t,p.modalidad)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados.")
    docs=[]
    for d in m.get("documentos",[]):
        if condition_match(d.get("mostrar_si") or d.get("mostrarCuando") or d.get("condicion"),p.respuestas):
            docs.append(d)
    return {"documentos":docs,"preguntas":visible_questions(m,p.respuestas)}

@app.post("/api/pregunta")
async def pregunta(request:Request,p:Payload):
    require_access(request)
    data=load_json()
    t=find_tramite(data,p.tramite)
    m=find_modalidad(t,p.modalidad)
    if not m:raise HTTPException(404,"Modalidad no encontrada.")
    qs=visible_questions(m,p.respuestas)
    return {"preguntas":qs}

@app.post("/api/resultado-tramite")
async def resultado(request:Request,p:Payload):
    require_access(request)
    return classify(p)

@app.post("/api/generar-guia-consular")
async def generar(request:Request,p:Payload):
    require_access(request)
    p.resultado=p.resultado or classify(p)
    filename=make_pdf(p)
    return {
        "success":True,
        "filename":filename,
        "url":f"/descargar/{filename}",
        "download_url":f"/descargar/{filename}",
        "estado":p.resultado.get("estado")
    }

@app.get("/descargar/{nombre}")
async def descargar(request:Request,nombre:str):
    require_access(request)
    safe=Path(nombre).name
    f=OUT/safe
    if not f.exists():raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(str(f),media_type="application/pdf",filename=safe)

@app.post("/api/logout")
async def logout(request:Request):
    token=request.cookies.get("save_access_token")
    TOKENS.pop(token,None)
    r=JSONResponse({"success":True})
    r.delete_cookie("save_access_token")
    return r

@app.get("/api/fuentes")
async def fuentes(request:Request):
    require_access(request)
    return load_json().get("fuentes_oficiales",{})

@app.post("/api/extraer-pdf")
async def extraer_pdf(request:Request):
    require_access(request)
    return {"success":False,"message":"La extracción de PDF no forma parte del flujo principal de SAVE MÉXICO AYUDAR."}

@app.post("/api/subir-fotos")
async def subir_fotos(request:Request):
    require_access(request)
    return {"success":False,"message":"La carga de fotografías no es necesaria para el flujo documental actual."}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
