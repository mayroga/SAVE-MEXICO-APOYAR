# app.py — SAVE MÉXICO AYUDAR v6.1.0
import os,json,re,hmac,hashlib,base64,time,secrets,uuid
from pathlib import Path
from datetime import datetime
import stripe
from fastapi import FastAPI,HTTPException,Request,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

BASE=Path(__file__).resolve().parent
DATA=BASE/"data"; STATIC=BASE/"static"; OUT=BASE/"generated"
JSON_FILE=DATA/"tramites.json"
ACCESS_FILE=DATA/"access.json"
DATA.mkdir(exist_ok=True); STATIC.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)

ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","").strip()
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","").strip()
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","").strip()
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","").strip()
APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
PRICE1=os.getenv("STRIPE_PRICE_ID1") or os.getenv("STRIPE_PRICE_ID_DAILY")
PRICE2=os.getenv("STRIPE_PRICE_ID2") or os.getenv("STRIPE_PRICE_ID_MONTHLY")
PRICE3=os.getenv("STRIPE_PRICE_ID3") or os.getenv("STRIPE_PRICE_ID_ANNUAL")
ACCESS_SECRET=os.getenv("ACCESS_TOKEN_SECRET") or STRIPE_SECRET_KEY or secrets.token_hex(32)
stripe.api_key=STRIPE_SECRET_KEY or None

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="6.1.0")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")
SESSIONS={}

# ------------------------- ARCHIVOS / DATOS -------------------------

def load_json(path,default):
    try:
        with open(path,"r",encoding="utf-8") as f:return json.load(f)
    except Exception:return default

def save_json(path,obj):
    tmp=Path(str(path)+".tmp")
    with open(tmp,"w",encoding="utf-8") as f:json.dump(obj,f,ensure_ascii=False,separators=(",",":"))
    tmp.replace(path)

def data():return load_json(JSON_FILE,{})
def access_db():return load_json(ACCESS_FILE,{"payments":{},"revoked":[]})

def clean(v):
    if isinstance(v,str):return re.sub(r"\s+"," ",v.strip())
    if isinstance(v,list):return [clean(x) for x in v]
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    return v

def tramites():
    return data().get("tramites",[])

def get_tramite(tid):
    return next((x for x in tramites() if x.get("id")==tid),None)

def get_modalidad(tid,mid):
    t=get_tramite(tid)
    if not t:return None
    return next((x for x in t.get("modalidades",[]) if x.get("id")==mid),None)

def questions(mod):
    return mod.get("preguntas",[]) if mod else []

def docs(mod):
    return mod.get("documentos",[]) if mod else []

def qmap(mod):
    return {q.get("id"):q for q in questions(mod)}

def dmap(mod):
    return {d.get("id"):d for d in docs(mod)}

def scalar_list(v):
    if v is None:return []
    if isinstance(v,list):return v
    return [v]

def answer_value(ans,qid):
    if not isinstance(ans,dict):return None
    return ans.get(qid)

def match_value(actual,rule):
    if not isinstance(rule,dict):return bool(actual)
    vals=scalar_list(actual)
    if "existe" in rule:
        return (actual is not None and actual!="" and actual!=[])==bool(rule["existe"])
    if "es" in rule:return actual==rule["es"]
    if "igual_a" in rule:return actual==rule["igual_a"]
    if "no_es" in rule:return actual!=rule["no_es"]
    if "distinto_de" in rule:return actual!=rule["distinto_de"]
    if "incluye" in rule:return rule["incluye"] in vals
    if "no_incluye" in rule:return rule["no_incluye"] not in vals
    if "en" in rule:return actual in rule["en"]
    if "alguno_de" in rule:return any(x in rule["alguno_de"] for x in vals)
    if "todos_de" in rule:return all(x in vals for x in rule["todos_de"])
    if "cantidad_mayor_que" in rule:
        n=len(vals)
        if n<=int(rule["cantidad_mayor_que"]):return False
        exc=rule.get("excepto",[])
        if exc and any(x in exc for x in vals):return False
        return True
    if "cantidad_igual_a" in rule:return len(vals)==int(rule["cantidad_igual_a"])
    if "cantidad_menor_que" in rule:return len(vals)<int(rule["cantidad_menor_que"])
    return False

def cond_match(cond,answers):
    if not cond:return True
    if isinstance(cond,list):return all(cond_match(x,answers) for x in cond)
    if not isinstance(cond,dict):return True
    if "y" in cond or "and" in cond:
        return all(cond_match(x,answers) for x in cond.get("y",cond.get("and",[])))
    if "o" in cond or "or" in cond:
        return any(cond_match(x,answers) for x in cond.get("o",cond.get("or",[])))
    qid=cond.get("respuesta") or cond.get("pregunta") or cond.get("campo")
    if not qid:return True
    return match_value(answers.get(qid),cond)

def visible(q,answers):
    return cond_match(q.get("mostrar_si") or q.get("cuando"),answers)

def required(q,answers):
    if q.get("required") is True:return visible(q,answers)
    if "obligatoria_si" in q:return visible(q,answers) and cond_match(q["obligatoria_si"],answers)
    return False

def valid_type(q,v):
    if q.get("tipo")=="multiple":return isinstance(v,list)
    return not isinstance(v,list)

def option_values(q):
    return {str(x.get("valor")) for x in q.get("opciones",[]) if isinstance(x,dict) and "valor" in x}

def validate_answer(q,v):
    if v is None or v=="" or v==[]:return None
    if not valid_type(q,v):return "FORMATO_INVALIDO"
    opts=option_values(q)
    if opts:
        vals=v if isinstance(v,list) else [v]
        if any(str(x) not in opts for x in vals):return "OPCION_INVALIDA"
    if q.get("tipo")=="multiple":
        vals=[str(x) for x in v]
        if "NO_SE" in vals and len(vals)>1:return "NO_SE_EXCLUSIVO"
        if "NINGUNO" in vals and len(vals)>1:return "NINGUNO_EXCLUSIVO"
    return None

def required_missing(mod,answers):
    out=[]
    for q in questions(mod):
        if not visible(q,answers):continue
        if required(q,answers):
            v=answers.get(q.get("id"))
            if v is None or v=="" or v==[]:out.append(q.get("id"))
            elif validate_answer(q,v):out.append(q.get("id"))
    return out

# ------------------------- DOCUMENTOS -------------------------

def doc_condition(d,answers):return cond_match(d.get("mostrar_si") or d.get("cuando"),answers)

def applicable_docs(mod,answers):
    return [d for d in docs(mod) if doc_condition(d,answers)]

def normalize_docs(items):
    out={}
    if not isinstance(items,list):return out
    allowed={"LO_TENGO","NO_LO_TENGO","NO_ESTOY_SEGURO","NO_APLICA"}
    for x in items:
        if not isinstance(x,dict):continue
        did=str(x.get("id","")).strip()
        st=str(x.get("estado","")).strip().upper()
        if did and st in allowed:
            out[did]={"estado":st,"motivo":clean(x.get("motivo",""))}
    return out

def validate_document_states(mod,answers,doc_states):
    errors=[];missing=[];unsure=[];not_answered=[]
    for d in applicable_docs(mod,answers):
        did=d.get("id")
        st=doc_states.get(did,{}).get("estado")
        if not st:
            not_answered.append(did)
            continue
        if st=="NO_LO_TENGO":missing.append(did)
        elif st=="NO_ESTOY_SEGURO":unsure.append(did)
    return errors,missing,unsure,not_answered

# ------------------------- VALIDACIÓN / RESULTADO -------------------------

def evaluate(payload):
    tid=payload.get("tramite_id");mid=payload.get("modalidad_id")
    t=get_tramite(tid);m=get_modalidad(tid,mid)
    if not t or not m:raise HTTPException(400,"Trámite o modalidad inválidos.")

    answers=clean(payload.get("respuestas") or {})
    personal=clean(payload.get("datos_personales") or {})
    cons=clean(payload.get("consulado") or {})
    ds=normalize_docs(payload.get("documentos") or [])

    qmiss=required_missing(m,answers)
    qerrors=[]
    for q in questions(m):
        qid=q.get("id")
        if qid in answers and visible(q,answers):
            err=validate_answer(q,answers[qid])
            if err:qerrors.append({"pregunta":qid,"error":err})

    for q in questions(m):
        if not visible(q,answers):continue
        v=answers.get(q.get("id"))
        vals=scalar_list(v)
        if "OTRO" in vals and not answers.get(q.get("id")+"_detalle"):
            qerrors.append({"pregunta":q.get("id"),"error":"FALTA_DETALLE_OTRO"})

    _,missing,unsure,no_status=validate_document_states(m,answers,ds)
    contradictions=[]

    # Reglas del JSON
    for r in m.get("reglas",[]):
        if not cond_match(r.get("si") or r.get("cuando") or r.get("condicion"),answers):continue
        accion=r.get("accion","")
        if accion in {"EXIGIR_ACLARACION","INCONSISTENCIA","HAY_INCONSISTENCIAS"}:
            contradictions.append(r.get("id") or r.get("mensaje") or "INCONSISTENCIA")
        elif accion in {"CONFIRMAR","REQUIERE_CONFIRMACION","CONFIRMAR_CONSULADO"}:
            unsure.append(r.get("id") or "CONFIRMAR")
        elif accion in {"FALTAN_DOCUMENTOS","EXIGIR_DOCUMENTO"}:
            missing.append(r.get("id") or "DOCUMENTO")

    personal_fields=data().get("datos_personales",{}).get("campos",[])
    personal_missing=[x.get("id") for x in personal_fields if x.get("required") and not personal.get(x.get("id"))]
    cons_fields=data().get("consulado",{}).get("campos",[])
    cons_missing=[x.get("id") for x in cons_fields if x.get("required") and not cons.get(x.get("id"))]

    confirmations=[]
    if no_status:confirmations+=["DOCUMENTOS:"+x for x in no_status]
    if unsure:confirmations+=["CONFIRMAR:"+str(x) for x in sorted(set(unsure))]
    if cons_missing:confirmations+=["CONSULADO:"+x for x in cons_missing]

    if qerrors or contradictions:
        result="HAY_INCONSISTENCIAS"
    elif qmiss or missing:
        result="FALTAN_DOCUMENTOS"
    elif confirmations or personal_missing:
        result="REQUIERE_CONFIRMACION"
    else:
        result="LISTO_PARA_CONFIRMAR"

    return {
        "resultado":result,
        "tramite":t.get("nombre",tid),
        "autoridad":t.get("autoridad",""),
        "modalidad":m.get("nombre",mid),
        "preguntas_faltantes":sorted(set(qmiss)),
        "errores":qerrors,
        "documentos_faltantes":sorted(set(missing)),
        "documentos_dudosos":sorted(set(unsure)),
        "documentos_sin_estado":sorted(set(no_status)),
        "datos_personales_faltantes":personal_missing,
        "confirmaciones":sorted(set(confirmations)),
        "inconsistencias":sorted(set(contradictions)),
        "consulado":cons
    }

# ------------------------- ACCESO SEGURO -------------------------

def token_make(subject,ttl=86400):
    p={"sub":subject,"iat":int(time.time()),"exp":int(time.time())+ttl,"jti":secrets.token_hex(12)}
    raw=base64.urlsafe_b64encode(json.dumps(p,separators=(",",":")).encode()).decode().rstrip("=")
    sig=hmac.new(ACCESS_SECRET.encode(),raw.encode(),hashlib.sha256).hexdigest()
    return raw+"."+sig

def token_read(auth):
    if not auth or not auth.startswith("Bearer "):raise HTTPException(401,"Acceso requerido.")
    token=auth[7:].strip()
    try:
        raw,sig=token.rsplit(".",1)
        good=hmac.new(ACCESS_SECRET.encode(),raw.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,good):raise ValueError()
        raw+="="*(-len(raw)%4)
        p=json.loads(base64.urlsafe_b64decode(raw).decode())
        if int(p.get("exp",0))<int(time.time()):raise ValueError()
        return p
    except Exception:raise HTTPException(401,"Acceso inválido o vencido.")

def require_access(req):
    auth=req.headers.get("authorization")
    return token_read(auth)

def payment_registered(session_id):
    db=access_db()
    return session_id in db.get("payments",{}) and session_id not in db.get("revoked",[])

# ------------------------- MODELOS -------------------------

class AdminLogin(BaseModel):
    username:str
    password:str

class Checkout(BaseModel):
    plan:str="1"

class Guide(BaseModel):
    tramite_id:str
    modalidad_id:str
    respuestas:dict={}
    datos_personales:dict={}
    consulado:dict={}
    documentos:list=[]

class Access(BaseModel):
    token:str

# ------------------------- RUTAS BÁSICAS -------------------------

@app.get("/")
async def index():return FileResponse(STATIC/"index.html")

@app.get("/health")
async def health():
    return {"status":"ok","app":"SAVE MÉXICO AYUDAR","version":"6.1.0","stripe":bool(stripe.api_key)}

@app.post("/api/admin-login")
async def admin_login(req:AdminLogin):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(500,"El acceso administrativo no está configurado.")
    if not hmac.compare_digest(req.username.strip(),ADMIN_USERNAME) or not hmac.compare_digest(req.password,ADMIN_PASSWORD):
        raise HTTPException(401,"Usuario o contraseña incorrectos.")
    return {"status":"success","access":"granted","type":"admin","token":token_make("admin",43200)}

@app.post("/api/login")
async def login_alias(req:AdminLogin):
    return await admin_login(req)

@app.post("/api/logout")
async def logout():
    return {"status":"success"}

@app.post("/api/check-access")
async def check_access(req:Access):
    p=token_read("Bearer "+req.token)
    return {"status":"success","access":"granted","type":"admin" if p.get("sub")=="admin" else "stripe","subject":p.get("sub")}

@app.get("/api/check-access")
async def check_access_get(request:Request):
    p=require_access(request)
    return {"status":"success","access":"granted","type":"admin" if p.get("sub")=="admin" else "stripe","subject":p.get("sub")}

# ------------------------- STRIPE -------------------------

def price_for(plan):
    return {"1":PRICE1,"2":PRICE2,"3":PRICE3}.get(str(plan))

def mode_for(plan):
    return "payment" if str(plan)=="1" else "subscription"

@app.post("/api/create-checkout-session")
async def create_checkout(req:Checkout):
    if not stripe.api_key:raise HTTPException(500,"Stripe no está configurado.")
    price_id=price_for(req.plan)
    if not price_id:raise HTTPException(500,"El Price ID seleccionado no está configurado.")
    try:
        s=stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price":price_id,"quantity":1}],
            mode=mode_for(req.plan),
            success_url=f"{APP_URL}/?stripe=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?stripe=cancel",
            metadata={"app":"SAVE_MEXICO_AYUDAR","plan":str(req.plan)},
            client_reference_id="SAVE_MEXICO_AYUDAR"
        )
        return {"status":"ok","url":s.url,"session_id":s.id}
    except Exception as e:
        raise HTTPException(502,f"No fue posible crear el pago: {str(e)}")

@app.get("/api/payment-success")
async def payment_success(session_id:str):
    if not stripe.api_key:raise HTTPException(500,"Stripe no está configurado.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        if s.payment_status!="paid":
            return {"status":"pending","access":"denied","message":"El pago todavía no está confirmado por Stripe."}
        # El acceso NO se concede solamente por el retorno del navegador.
        if not payment_registered(session_id):
            return {"status":"pending","access":"denied","message":"Pago recibido. Esperando confirmación segura de Stripe."}
        return {"status":"success","access":"granted","token":token_make(f"stripe:{session_id}",86400)}
    except Exception as e:
        raise HTTPException(400,f"No fue posible verificar el pago: {str(e)}")

@app.post("/api/verify-payment")
async def verify_payment(req:Access):
    try:
        p=token_read("Bearer "+req.token)
        if not str(p.get("sub","")).startswith("stripe:"):return {"status":"success","access":"granted","type":"admin"}
        sid=p["sub"].split(":",1)[1]
        if not payment_registered(sid):raise HTTPException(403,"El acceso de pago no está confirmado.")
        return {"status":"success","access":"granted","type":"stripe"}
    except HTTPException:raise
    except Exception:raise HTTPException(401,"Acceso inválido.")

@app.post("/api/stripe-webhook")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500,"STRIPE_WEBHOOK_SECRET no está configurado.")
    try:
        event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
    except ValueError:raise HTTPException(400,"Payload Stripe inválido.")
    except stripe.error.SignatureVerificationError:raise HTTPException(400,"Firma Stripe inválida.")

    typ=event["type"]; obj=event["data"]["object"]
    db=access_db()

    if typ=="checkout.session.completed":
        sid=obj.get("id")
        paid=obj.get("payment_status")=="paid"
        if sid and paid:
            prices=set()
            try:
                ss=stripe.checkout.Session.retrieve(sid,expand=["line_items"])
                prices={i.price.id for i in ss.line_items.data if getattr(i,"price",None)}
            except Exception:pass
            allowed={x for x in (PRICE1,PRICE2,PRICE3) if x}
            if prices.intersection(allowed):
                db.setdefault("payments",{})[sid]={
                    "created":datetime.utcnow().isoformat()+"Z",
                    "plan":obj.get("metadata",{}).get("plan",""),
                    "customer":(obj.get("customer_details") or {}).get("email",""),
                    "price_ids":list(prices)
                }
                save_json(ACCESS_FILE,db)

    elif typ in {"charge.refunded","checkout.session.expired"}:
        sid=obj.get("id") if typ=="checkout.session.expired" else obj.get("metadata",{}).get("checkout_session_id")
        if sid:
            db.setdefault("revoked",[])
            if sid not in db["revoked"]:db["revoked"].append(sid)
            save_json(ACCESS_FILE,db)

    elif typ in {"customer.subscription.deleted","customer.subscription.updated"}:
        # El acceso se mantiene sujeto a la confirmación del pago/suscripción
        # que Stripe haya registrado; no se concede acceso desde el navegador.
        pass

    return {"received":True}

# ------------------------- DATOS DEL TRÁMITE -------------------------

@app.get("/api/tramites")
async def api_tramites():
    return {"version":data().get("version"),"nombre_app":data().get("nombre_app"),"tramites":[
        {"id":t.get("id"),"nombre":t.get("nombre"),"autoridad":t.get("autoridad")}
        for t in tramites()
    ]}

@app.get("/api/modalidades")
async def api_modalidades(tramite_id:str):
    t=get_tramite(tramite_id)
    if not t:raise HTTPException(404,"Trámite no encontrado.")
    return {"tramite_id":tramite_id,"modalidades":[
        {"id":m.get("id"),"nombre":m.get("nombre"),"descripcion":m.get("descripcion","")}
        for m in t.get("modalidades",[])
    ]}

@app.get("/api/ficha-tramite")
async def ficha_tramite(tramite_id:str,modalidad_id:str):
    t=get_tramite(tramite_id);m=get_modalidad(tramite_id,modalidad_id)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados.")
    return {
        "tramite":t,
        "modalidad":m,
        "preguntas":questions(m),
        "documentos":docs(m),
        "manual":data().get("manual",{}),
        "mensajes":data().get("mensajes",{})
    }

@app.get("/api/datos-personales")
async def datos_personales():
    return {
        "campos":data().get("datos_personales",{}).get("campos",[]),
        "consulado":data().get("consulado",{}).get("campos",[])
    }

# ------------------------- RESULTADO -------------------------

@app.post("/api/resultado-tramite")
async def resultado_tramite(payload:Guide,request:Request):
    require_access(request)
    return evaluate(payload.model_dump())

# ------------------------- PDF -------------------------

def txt(v):
    if v is None or v=="":return "No indicado"
    if isinstance(v,list):return ", ".join(map(str,v)) or "No indicado"
    return str(v)

def make_pdf(payload,result):
    t=get_tramite(payload.tramite_id);m=get_modalidad(payload.tramite_id,payload.modalidad_id)
    name=f"guia_{payload.tramite_id.lower()}_{uuid.uuid4().hex[:8]}.pdf"
    path=OUT/name
    styles=getSampleStyleSheet()
    normal=styles["BodyText"];normal.fontSize=9;normal.leading=12
    title=styles["Title"];title.fontSize=17
    story=[Paragraph("SAVE MÉXICO AYUDAR",title),Spacer(1,8),
           Paragraph("GUÍA PERSONALIZADA DE PREPARACIÓN",styles["Heading2"]),Spacer(1,8)]
    story += [
        Paragraph(f"<b>Trámite:</b> {txt(t.get('nombre'))}",normal),
        Paragraph(f"<b>Autoridad:</b> {txt(t.get('autoridad'))}",normal),
        Paragraph(f"<b>Modalidad:</b> {txt(m.get('nombre'))}",normal),
        Paragraph(f"<b>Resultado:</b> {txt(result.get('resultado'))}",normal),
        Spacer(1,10)
    ]

    story.append(Paragraph("DATOS DEL SOLICITANTE",styles["Heading2"]))
    rows=[]
    for f in data().get("datos_personales",{}).get("campos",[]):
        fid=f.get("id");v=payload.datos_personales.get(fid)
        if v not in (None,"",[]):rows.append([txt(f.get("nombre",fid)),txt(v)])
    story.append(Table(rows or [["Datos","No indicados"]],colWidths=[170,340],
                       style=TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),
                                         ("VALIGN",(0,0),(-1,-1),"TOP"),
                                         ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
                                         ("FONTSIZE",(0,0),(-1,-1),8)])))
    story.append(Spacer(1,10))

    story.append(Paragraph("CONSULADO / UBICACIÓN",styles["Heading2"]))
    rows=[]
    for f in data().get("consulado",{}).get("campos",[]):
        fid=f.get("id");rows.append([txt(f.get("nombre",fid)),txt(payload.consulado.get(fid))])
    story.append(Table(rows,colWidths=[170,340],style=TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])))
    story.append(Spacer(1,10))

    story.append(Paragraph("RESPUESTAS DEL TRÁMITE",styles["Heading2"]))
    rows=[]
    qm=qmap(m)
    for qid,v in payload.respuestas.items():
        q=qm.get(qid)
        if q and visible(q,payload.respuestas):rows.append([txt(q.get("texto",qid)),txt(v)])
        detalle=payload.respuestas.get(qid+"_detalle")
        if detalle:rows.append(["Detalle",txt(detalle)])
    story.append(Table(rows or [["Respuestas","No indicadas"]],colWidths=[300,210],
                       style=TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"TOP")])))
    story.append(Spacer(1,10))

    story.append(Paragraph("DOCUMENTOS QUE CORRESPONDEN",styles["Heading2"]))
    drows=[["Documento","Estado","Motivo"]]
    ds=normalize_docs(payload.documentos)
    for d in applicable_docs(m,payload.respuestas):
        x=ds.get(d.get("id"),{})
        drows.append([txt(d.get("nombre",d.get("id"))),txt(x.get("estado","NO INDICADO")),txt(x.get("motivo",""))])
    story.append(Table(drows,colWidths=[270,120,120],repeatRows=1,
                       style=TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),
                                         ("BACKGROUND",(0,0),(-1,0),colors.lightgrey),
                                         ("FONTSIZE",(0,0),(-1,-1),8),
                                         ("VALIGN",(0,0),(-1,-1),"TOP")])))
    story.append(Spacer(1,10))

    if result.get("documentos_faltantes"):
        story.append(Paragraph("LO QUE FALTA",styles["Heading2"]))
        for x in result["documentos_faltantes"]:
            d=dmap(m).get(x,{})
            story.append(Paragraph("• "+txt(d.get("nombre",x)),normal))
    if result.get("documentos_dudosos"):
        story.append(Paragraph("LO QUE DEBES CONFIRMAR",styles["Heading2"]))
        for x in result["documentos_dudosos"]:
            d=dmap(m).get(x,{})
            story.append(Paragraph("• "+txt(d.get("nombre",x)),normal))
    if result.get("inconsistencias"):
        story.append(Paragraph("INCONSISTENCIAS",styles["Heading2"]))
        for x in result["inconsistencias"]:story.append(Paragraph("• "+txt(x),normal))
    if result.get("confirmaciones"):
        story.append(Paragraph("PUNTOS POR CONFIRMAR",styles["Heading2"]))
        for x in result["confirmaciones"]:story.append(Paragraph("• "+txt(x),normal))

    story += [Spacer(1,12),Paragraph("IMPORTANTE",styles["Heading2"]),
              Paragraph("SAVE MÉXICO AYUDAR es un servicio privado e independiente de MAY ROGA LLC, Florida. No es una agencia del Gobierno de México ni representa a ningún consulado mexicano. Esta guía organiza la información proporcionada por el usuario y ayuda a preparar el trámite. La autoridad competente decide los requisitos finales, aceptación de documentos, citas y resolución.",normal),
              Spacer(1,8),
              Paragraph("Antes de acudir al consulado, confirma siempre la información vigente con la autoridad correspondiente.",normal)]
    SimpleDocTemplate(str(path),pagesize=LETTER,rightMargin=35,leftMargin=35,topMargin=35,bottomMargin=35).build(story)
    return name

@app.post("/api/generar-guia-consular")
async def generar_guia(payload:Guide,request:Request):
    require_access(request)
    p=payload.model_dump()
    result=evaluate(p)
    if result["resultado"]=="HAY_INCONSISTENCIAS":
        raise HTTPException(409,detail={"message":"Corrige las inconsistencias antes de generar la guía.","resultado":result})
    if result["preguntas_faltantes"]:
        raise HTTPException(422,detail={"message":"Faltan respuestas obligatorias.","resultado":result})
    name=make_pdf(payload,result)
    return {"status":"success","resultado":result,"archivo":name,"download":f"/descargar/{name}"}

@app.get("/descargar/{name}")
async def download(name:str,request:Request):
    require_access(request)
    safe=Path(name).name
    path=OUT/safe
    if not path.exists():raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(path,filename=safe,media_type="application/pdf")

# ------------------------- DOCUMENTOS SUBIDOS -------------------------

@app.post("/api/subir-documento")
async def subir_documento(request:Request,file:UploadFile=File(...)):
    require_access(request)
    ext=Path(file.filename or "").suffix.lower()
    if ext not in {".pdf",".jpg",".jpeg",".png"}:raise HTTPException(400,"Formato no permitido.")
    if not file.filename:raise HTTPException(400,"Archivo inválido.")
    content=await file.read()
    if len(content)>10*1024*1024:raise HTTPException(413,"Archivo demasiado grande.")
    sid=uuid.uuid4().hex
    path=OUT/f"documento_{sid}{ext}"
    path.write_bytes(content)
    return {"status":"success","id":sid,"nombre":path.name}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
