import os,json,re,secrets,uuid
from pathlib import Path
from datetime import datetime
from typing import Any
import stripe
from fastapi import FastAPI,HTTPException,Request,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib.units import inch

BASE=Path(__file__).resolve().parent
DATA=BASE/"data"
STATIC=BASE/"static"
OUT=BASE/"out"
JSON_FILE=DATA/"tramites.json"
OUT.mkdir(exist_ok=True)

ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
PRICE_DAILY=os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1","")
PRICE_MONTHLY=os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2","")
PRICE_ANNUAL=os.getenv("STRIPE_PRICE_ID_ANNUAL") or os.getenv("STRIPE_PRICE_ID3","")

if STRIPE_SECRET_KEY:
    stripe.api_key=STRIPE_SECRET_KEY

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="6.0.0")
if STATIC.exists():
    app.mount("/static",StaticFiles(directory=STATIC),name="static")

SESSIONS={}

def load_data():
    if not JSON_FILE.exists():
        raise RuntimeError("No existe data/tramites.json")
    with open(JSON_FILE,"r",encoding="utf-8") as f:
        return json.load(f)

def data():
    return load_data()

def clean(v):
    if isinstance(v,str): return v.strip()
    return v

def get_tramite(tid):
    for t in data().get("tramites",[]):
        if t.get("id")==tid:return t
    return None

def get_modalidad(tid,mid):
    t=get_tramite(tid)
    if not t:return None
    for m in t.get("modalidades",[]):
        if m.get("id")==mid:return m
    return None

def questions(mod):
    return mod.get("preguntas",[]) if mod else []

def docs(mod):
    return mod.get("documentos",[]) if mod else []

def qmap(mod):
    return {q.get("id"):q for q in questions(mod) if q.get("id")}

def options(q):
    return q.get("opciones",[]) or []

def option_values(q):
    return {str(x.get("valor")) for x in options(q) if x.get("valor") is not None}

def answer_value(ans,key):
    return ans.get(key)

def scalar_list(v):
    if isinstance(v,list):return v
    if v is None:return []
    return [v]

def match_value(actual,cond):
    if isinstance(cond,dict):
        if "es" in cond:return actual==cond["es"]
        if "igual_a" in cond:return actual==cond["igual_a"]
        if "distinto_de" in cond:return actual!=cond["distinto_de"]
        if "no_es" in cond:return actual!=cond["no_es"]
        if "incluye" in cond:return cond["incluye"] in scalar_list(actual)
        if "no_incluye" in cond:return cond["no_incluye"] not in scalar_list(actual)
        if "en" in cond:return any(x in cond["en"] for x in scalar_list(actual))
        if "alguno_de" in cond:return any(x in cond["alguno_de"] for x in scalar_list(actual))
        if "todos_de" in cond:return all(x in scalar_list(actual) for x in cond["todos_de"])
        if "existe" in cond:return actual is not None and actual!="" and actual!=[]
        if "cantidad_mayor_que" in cond:return len(scalar_list(actual))>int(cond["cantidad_mayor_que"])
        if "cantidad_igual_a" in cond:return len(scalar_list(actual))==int(cond["cantidad_igual_a"])
        if "cantidad_menor_que" in cond:return len(scalar_list(actual))<int(cond["cantidad_menor_que"])
        if "cantidad_mayor_igual_que" in cond:return len(scalar_list(actual))>=int(cond["cantidad_mayor_igual_que"])
        if "cantidad_menor_igual_que" in cond:return len(scalar_list(actual))<=int(cond["cantidad_menor_igual_que"])
    return actual==cond

def cond_match(cond,ans):
    if cond is None:return True
    if isinstance(cond,bool):return cond
    if isinstance(cond,list):return all(cond_match(x,ans) for x in cond)
    if not isinstance(cond,dict):return False
    if "y" in cond or "and" in cond:
        arr=cond.get("y",cond.get("and"))
        return all(cond_match(x,ans) for x in arr)
    if "o" in cond or "or" in cond:
        arr=cond.get("o",cond.get("or"))
        return any(cond_match(x,ans) for x in arr)
    if "respuesta" in cond:
        return match_value(ans.get(cond["respuesta"]),cond)
    return False

def visible(q,ans):
    for key in ("mostrar_si","visible_si","condicion","cuando"):
        if key in q and not cond_match(q[key],ans):return False
    if "depende_de" in q:
        dep=q["depende_de"]
        if isinstance(dep,str) and ans.get(dep) in (None,"",[]):return False
    return True

def required(q):
    return q.get("obligatorio") is True or q.get("required") is True

def valid_type(q,v):
    if v is None:return False
    typ=q.get("tipo","texto")
    if typ=="multiple":
        return isinstance(v,list)
    if typ in ("si_no","opciones","select","single"):
        return isinstance(v,str)
    if typ=="numero":
        try:float(v);return True
        except:return False
    if typ=="fecha":
        try:datetime.strptime(str(v),"%Y-%m-%d");return True
        except:return False
    if typ=="email":
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$",str(v)))
    return isinstance(v,str)

def validate_answer(q,v):
    errs=[]
    if not valid_type(q,v):
        return ["TIPO_DE_RESPUESTA_INVALIDO"]
    typ=q.get("tipo","texto")
    vals=option_values(q)
    if typ in ("si_no","opciones","select","single"):
        if vals and str(v) not in vals:
            errs.append("OPCION_NO_PERMITIDA")
    if typ=="multiple":
        if not isinstance(v,list):return ["MULTIPLE_DEBE_SER_LISTA"]
        if not v:return ["SELECCION_VACIA"]
        if vals:
            bad=[x for x in v if str(x) not in vals]
            if bad:errs.append("OPCION_NO_PERMITIDA")
        if "NO_SE" in v and len(v)>1:errs.append("NO_SE_NO_PUEDE_COMBINARSE")
        if "NINGUNO" in v and len(v)>1:errs.append("NINGUNO_NO_PUEDE_COMBINARSE")
    return errs

def required_missing(mod,ans):
    out=[]
    for q in questions(mod):
        if not visible(q,ans):continue
        if required(q):
            v=ans.get(q.get("id"))
            if v is None or v=="" or v==[]:
                out.append(q.get("id"))
    return out

def normalize_docs(payload):
    if isinstance(payload,dict):
        payload=payload.get("documentos",[])
    if not isinstance(payload,list):return {}
    out={}
    for x in payload:
        if not isinstance(x,dict):continue
        did=x.get("id")
        st=x.get("estado")
        if did:out[did]=st
    return out

def doc_condition(d,ans):
    c=d.get("cuando")
    if c is None:return True
    return cond_match(c,ans)

def applicable_docs(mod,ans):
    return [d for d in docs(mod) if doc_condition(d,ans)]

def doc_required(d):
    return d.get("obligatorio") is True or d.get("required") is True or d.get("obligatorio_base") is True

def validate_document_states(mod,doc_states,ans):
    valid_ids={d.get("id") for d in applicable_docs(mod,ans)}
    errors=[]
    for did,st in doc_states.items():
        if did not in valid_ids:
            errors.append(f"DOCUMENTO_NO_APLICABLE:{did}")
        elif st not in ("LO_TENGO","NO_LO_TENGO","NO_ESTOY_SEGURO","NO_APLICA"):
            errors.append(f"ESTADO_DOCUMENTO_INVALIDO:{did}")
    return errors

def evaluate(mod,ans,doc_states,personal=None,consulate=None):
    missing_q=required_missing(mod,ans)
    invalid=[]
    for q in questions(mod):
        qid=q.get("id")
        if qid in ans and visible(q,ans):
            invalid.extend([f"{qid}:{x}" for x in validate_answer(q,ans[qid])])
    applicable=applicable_docs(mod,ans)
    missing=[]
    unsure=[]
    no_status=[]
    for d in applicable:
        did=d.get("id")
        st=doc_states.get(did)
        if st is None:
            no_status.append(did)
        elif st=="NO_LO_TENGO" and doc_required(d):
            missing.append(did)
        elif st=="NO_ESTOY_SEGURO":
            unsure.append(did)
    inconsist=[]
    confirm=[]
    details=[]
    for r in mod.get("reglas",[]) or []:
        if cond_match(r.get("cuando"),ans):
            action=r.get("accion","")
            msg=r.get("mensaje","")
            if action=="HAY_INCONSISTENCIAS":inconsist.append(msg or r.get("id"))
            elif action=="FALTAN_DOCUMENTOS":missing.append(r.get("id"))
            elif action in ("REQUIERE_CONFIRMACION","CONFIRMAR_CONSULADO","CASO_ESPECIAL","REVISAR_MODALIDAD"):
                confirm.append(msg or r.get("id"))
            elif action in ("EXIGIR_DETALLE","EXIGIR_ACLARACION","EXIGIR_DOCUMENTO_CAMBIO"):
                details.append(msg or r.get("id"))
    for q in questions(mod):
        qid=q.get("id")
        v=ans.get(qid)
        if not visible(q,ans):continue
        if isinstance(v,list):
            if "NO_SE" in v:confirm.append(qid+":NO_SE")
            if "OTRO" in v:
                detail_key=qid+"_detalle"
                if not ans.get(detail_key):details.append(qid+":OTRO_SIN_DETALLE")
        elif v=="NO_SE":confirm.append(qid+":NO_SE")
    if not isinstance(personal,dict):personal={}
    for f in data().get("datos_personales",{}).get("campos",[]):
        if f.get("obligatorio") and not personal.get(f.get("id")):
            missing_q.append("PERSONAL:"+f.get("id"))
    c=consulate or {}
    if not c.get("estado") or not c.get("ciudad") or not c.get("consulado"):
        confirm.append("CONFIRMAR_CONSULADO")
    if invalid:inconsist.extend(invalid)
    if details:confirm.extend(details)
    missing=list(dict.fromkeys(missing))
    unsure=list(dict.fromkeys(unsure))
    no_status=list(dict.fromkeys(no_status))
    inconsist=list(dict.fromkeys([x for x in inconsist if x]))
    confirm=list(dict.fromkeys([x for x in confirm if x]))
    if inconsist:result="HAY_INCONSISTENCIAS"
    elif missing:result="FALTAN_DOCUMENTOS"
    elif missing_q or unsure or no_status or confirm:result="REQUIERE_CONFIRMACION"
    else:result="LISTO_PARA_CONFIRMAR"
    return {
        "resultado":result,
        "preguntas_faltantes":missing_q,
        "documentos_aplicables":[d.get("id") for d in applicable],
        "documentos_faltantes":missing,
        "documentos_dudosos":unsure,
        "documentos_sin_estado":no_status,
        "inconsistencias":inconsist,
        "confirmaciones":confirm
    }

def session_id():
    return secrets.token_urlsafe(24)

class Access(BaseModel):
    token:str=""

class AdminLogin(BaseModel):
    username:str
    password:str

class Checkout(BaseModel):
    plan:str

class Guide(BaseModel):
    tramite:str
    modalidad:str
    datos_personales:dict={}
    datos_especificos:dict={}
    documentos:list=[]
    documentos_disponibles:list=[]
    documentos_faltantes:list=[]
    documentos_dudosos:list=[]
    situaciones:list=[]
    aclaraciones:list=[]
    idioma:str="es"
    consulado:dict={}
    respuestas:dict={}
    resultado:str=""

def access_ok(token):
    if not token or token not in SESSIONS:return False
    s=SESSIONS[token]
    return bool(s.get("access") or s.get("admin"))

@app.get("/")
def home():
    p=STATIC/"index.html"
    if not p.exists():raise HTTPException(404,"No existe static/index.html")
    return FileResponse(p)

@app.get("/health")
def health():
    d=data()
    return {
        "ok":True,
        "version":d.get("version"),
        "app_version":"6.0.0",
        "tramites":[x.get("id") for x in d.get("tramites",[])],
        "stripe":bool(STRIPE_SECRET_KEY),
        "prices":{
            "daily":bool(PRICE_DAILY),
            "monthly":bool(PRICE_MONTHLY),
            "annual":bool(PRICE_ANNUAL)
        },
        "admin":bool(ADMIN_USERNAME and ADMIN_PASSWORD)
    }

@app.post("/api/admin-login")
def admin_login(x:AdminLogin):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD or not secrets.compare_digest(x.username,ADMIN_USERNAME) or not secrets.compare_digest(x.password,ADMIN_PASSWORD):
        raise HTTPException(401,"Usuario o contraseña incorrectos")
    tok=session_id()
    SESSIONS[tok]={"access":True,"admin":True,"created":datetime.utcnow().isoformat()}
    return {"ok":True,"token":tok,"admin":True,"access":True}

@app.post("/api/logout")
def logout(x:Access):
    SESSIONS.pop(x.token,None)
    return {"ok":True}

@app.post("/api/check-access")
def check_access(x:Access):
    s=SESSIONS.get(x.token,{})
    return {"access":bool(s.get("access")),"admin":bool(s.get("admin"))}

@app.post("/api/create-checkout-session")
def checkout(x:Checkout):
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado")
    prices={"daily":PRICE_DAILY,"monthly":PRICE_MONTHLY,"annual":PRICE_ANNUAL}
    price=prices.get(x.plan)
    if not price:raise HTTPException(400,"Plan no configurado")
    try:
        tok=session_id()
        SESSIONS[tok]={"access":False,"admin":False,"created":datetime.utcnow().isoformat()}
        s=stripe.checkout.Session.create(
            mode="subscription" if x.plan in ("monthly","annual") else "payment",
            line_items=[{"price":price,"quantity":1}],
            success_url=f"{APP_URL}/?payment=success&session_id={{CHECKOUT_SESSION_ID}}&token={tok}",
            cancel_url=f"{APP_URL}/?payment=cancel",
            metadata={"access_token":tok,"plan":x.plan}
        )
        return {"ok":True,"url":s.url,"session_id":s.id,"token":tok}
    except Exception as e:
        raise HTTPException(500,f"Stripe: {e}")

@app.get("/api/verify-payment")
def verify_payment(session_id:str="",token:str=""):
    if not STRIPE_SECRET_KEY:return {"ok":False,"paid":False}
    if not session_id or not token:return {"ok":False,"paid":False}
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        paid=s.get("payment_status")=="paid" or s.get("status")=="complete"
        if paid:
            meta=s.get("metadata") or {}
            if meta.get("access_token")==token and token in SESSIONS:
                SESSIONS[token]["access"]=True
                SESSIONS[token]["stripe_session"]=session_id
        return {"ok":True,"paid":paid,"access":bool(SESSIONS.get(token,{}).get("access"))}
    except Exception as e:
        return {"ok":False,"paid":False,"error":str(e)}

@app.post("/api/stripe-webhook")
async def stripe_webhook(request:Request):
    payload=await request.body()
    sig=request.headers.get("stripe-signature","")
    try:
        if STRIPE_WEBHOOK_SECRET:
            event=stripe.Webhook.construct_event(payload,sig,STRIPE_WEBHOOK_SECRET)
        else:
            event=json.loads(payload)
    except Exception as e:
        raise HTTPException(400,f"Webhook inválido: {e}")
    if event.get("type") in ("checkout.session.completed","checkout.session.async_payment_succeeded"):
        s=event["data"]["object"]
        if s.get("payment_status")=="paid" or event.get("type")=="checkout.session.async_payment_succeeded":
            tok=(s.get("metadata") or {}).get("access_token")
            if tok in SESSIONS:
                SESSIONS[tok]["access"]=True
                SESSIONS[tok]["stripe_session"]=s.get("id")
    return {"received":True}

@app.get("/api/tramites")
def tramites():
    return {"tramites":[
        {"id":t.get("id"),"nombre":t.get("nombre"),"autoridad":t.get("autoridad"),"descripcion":t.get("descripcion")}
        for t in data().get("tramites",[])
    ]}

@app.get("/api/modalidades")
def modalidades(tramite:str):
    t=get_tramite(tramite)
    if not t:raise HTTPException(404,"Trámite no encontrado")
    return {"tramite":tramite,"modalidades":[
        {"id":m.get("id"),"nombre":m.get("nombre"),"edad":m.get("edad")}
        for m in t.get("modalidades",[])
    ]}

@app.get("/api/ficha-tramite")
def ficha_tramite(tramite:str,modalidad:str):
    t=get_tramite(tramite)
    m=get_modalidad(tramite,modalidad)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados")
    return {
        "tramite":{"id":t["id"],"nombre":t["nombre"],"autoridad":t["autoridad"],"descripcion":t.get("descripcion","")},
        "modalidad":{"id":m["id"],"nombre":m["nombre"],"edad":m.get("edad")},
        "preguntas":m.get("preguntas",[]),
        "documentos":m.get("documentos",[]),
        "reglas":m.get("reglas",[])
    }

@app.get("/api/datos-personales")
def datos_personales():
    return data().get("datos_personales",{})

@app.post("/api/resultado-tramite")
def resultado(g:Guide):
    t=get_tramite(g.tramite)
    m=get_modalidad(g.tramite,g.modalidad)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados")
    ans=g.datos_especificos or g.respuestas or {}
    ds=normalize_docs(g.documentos)
    errors=validate_document_states(m,ds,ans)
    if errors:return JSONResponse(status_code=422,content={"ok":False,"errores":errors})
    r=evaluate(m,ans,ds,g.datos_personales,g.consulado)
    return {"ok":True,"tramite":t["nombre"],"modalidad":m["nombre"],**r}

def pdf_escape(v):
    if isinstance(v,list):return ", ".join(map(str,v))
    if isinstance(v,dict):return json.dumps(v,ensure_ascii=False)
    return "" if v is None else str(v)

def make_pdf(g,r):
    t=get_tramite(g.tramite)
    m=get_modalidad(g.tramite,g.modalidad)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados")
    name=f"save_mexico_{uuid.uuid4().hex}.pdf"
    path=OUT/name
    styles=getSampleStyleSheet()
    title=ParagraphStyle("title",parent=styles["Title"],alignment=TA_CENTER,fontSize=17,leading=21,spaceAfter=12)
    h=ParagraphStyle("h",parent=styles["Heading2"],fontSize=12,leading=15,spaceBefore=10,spaceAfter=6)
    body=ParagraphStyle("body",parent=styles["BodyText"],fontSize=9.5,leading=13,spaceAfter=4)
    doc=SimpleDocTemplate(str(path),pagesize=letter,rightMargin=.55*inch,leftMargin=.55*inch,topMargin=.55*inch,bottomMargin=.55*inch)
    story=[]
    story.append(Paragraph("SAVE MÉXICO AYUDAR",title))
    story.append(Paragraph("Preparación documental privada",styles["Heading3"]))
    story.append(Spacer(1,8))
    story.append(Paragraph(f"<b>Fecha:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",body))
    story.append(Paragraph(f"<b>Trámite:</b> {t['nombre']}",body))
    story.append(Paragraph(f"<b>Modalidad:</b> {m['nombre']}",body))
    story.append(Paragraph(f"<b>Autoridad:</b> {t['autoridad']}",body))

    story.append(Paragraph("DATOS PERSONALES",h))
    for f in data().get("datos_personales",{}).get("campos",[]):
        val=g.datos_personales.get(f["id"],"")
        if val!="" and val is not None:
            story.append(Paragraph(f"<b>{f.get('etiqueta',f['id'])}:</b> {pdf_escape(val)}",body))

    story.append(Paragraph("CONSULADO U OFICINA",h))
    c=g.consulado or {}
    for k,label in (("estado","Estado"),("ciudad","Ciudad"),("consulado","Consulado u oficina")):
        story.append(Paragraph(f"<b>{label}:</b> {pdf_escape(c.get(k,'POR CONFIRMAR'))}",body))

    story.append(Paragraph("SITUACIÓN Y RESPUESTAS",h))
    qm=qmap(m)
    for qid,v in (g.datos_especificos or {}).items():
        if qid.endswith("_detalle"):continue
        q=qm.get(qid)
        if q:
            story.append(Paragraph(f"<b>{q.get('texto',qid)}</b><br/>{pdf_escape(v)}",body))
            if f"{qid}_detalle" in g.datos_especificos:
                story.append(Paragraph(f"<b>Detalle:</b> {pdf_escape(g.datos_especificos[f'{qid}_detalle'])}",body))

    story.append(Paragraph("DOCUMENTOS APLICABLES",h))
    ds=normalize_docs(g.documentos)
    groups={}
    for d in applicable_docs(m,g.datos_especificos or {}):
        groups.setdefault(d.get("seccion","DOCUMENTOS"),[]).append(d)
    for sec,items in groups.items():
        story.append(Paragraph(sec.replace("_"," "),styles["Heading3"]))
        for d in items:
            st=ds.get(d["id"],"SIN ESTADO")
            story.append(Paragraph(
                f"<b>{d['nombre']}</b><br/>"
                f"Estado: {st}<br/>"
                f"{d.get('motivo','')}",body))

    if r["documentos_faltantes"]:
        story.append(Paragraph("DOCUMENTOS FALTANTES",h))
        for x in r["documentos_faltantes"]:
            d=next((z for z in docs(m) if z.get("id")==x),None)
            story.append(Paragraph(f"• {d.get('nombre',x) if d else x}",body))

    if r["documentos_dudosos"]:
        story.append(Paragraph("DOCUMENTOS DUDOSOS",h))
        for x in r["documentos_dudosos"]:
            d=next((z for z in docs(m) if z.get("id")==x),None)
            story.append(Paragraph(f"• {d.get('nombre',x) if d else x} — POR CONFIRMAR",body))

    if r["inconsistencias"]:
        story.append(Paragraph("INCONSISTENCIAS",h))
        for x in r["inconsistencias"]:story.append(Paragraph("• "+pdf_escape(x),body))

    if r["confirmaciones"]:
        story.append(Paragraph("PUNTOS POR CONFIRMAR",h))
        for x in r["confirmaciones"]:story.append(Paragraph("• "+pdf_escape(x),body))

    story.append(Paragraph("RESULTADO FINAL",h))
    story.append(Paragraph(f"<b>{r['resultado']}</b>",body))
    story.append(Spacer(1,8))
    story.append(Paragraph(data().get("mensajes",{}).get("no_oficial","SAVE MÉXICO AYUDAR es un servicio privado de preparación documental. No es el Gobierno de México, la SRE ni el INE."),body))
    story.append(Paragraph("Los requisitos particulares, documentos aceptables, citas, costos y situaciones especiales deben confirmarse con la autoridad competente.",body))
    doc.build(story)
    return name

@app.post("/api/generar-guia-consular")
def generar(g:Guide):
    t=get_tramite(g.tramite)
    m=get_modalidad(g.tramite,g.modalidad)
    if not t or not m:raise HTTPException(404,"Trámite o modalidad no encontrados")
    ans=g.datos_especificos or g.respuestas or {}
    ds=normalize_docs(g.documentos)
    errors=validate_document_states(m,ds,ans)
    if errors:raise HTTPException(422,detail={"errores":errors})
    r=evaluate(m,ans,ds,g.datos_personales,g.consulado)
    if r["resultado"]=="HAY_INCONSISTENCIAS":
        raise HTTPException(422,detail={"resultado":r["resultado"],"inconsistencias":r["inconsistencias"]})
    if r["preguntas_faltantes"]:
        raise HTTPException(422,detail={"resultado":"REQUIERE_CONFIRMACION","preguntas_faltantes":r["preguntas_faltantes"]})
    name=make_pdf(g,r)
    return {"ok":True,"archivo":name,"descarga":f"/descargar/{name}","resultado":r["resultado"],"evaluacion":r}

@app.get("/descargar/{name}")
def descargar(name:str):
    if Path(name).name!=name:raise HTTPException(400,"Nombre inválido")
    p=OUT/name
    if not p.exists():raise HTTPException(404,"Archivo no encontrado")
    return FileResponse(p,media_type="application/pdf",filename=name)

@app.post("/api/subir-documento")
async def subir_documento(file:UploadFile=File(...)):
    allowed={"application/pdf","image/jpeg","image/png"}
    if file.content_type not in allowed:
        raise HTTPException(400,"Solo PDF, JPG o PNG")
    content=await file.read()
    if len(content)>15*1024*1024:
        raise HTTPException(400,"El archivo supera 15 MB")
    ext=Path(file.filename or "").suffix.lower()
    name=f"{uuid.uuid4().hex}{ext}"
    path=OUT/name
    path.write_bytes(content)
    return {"ok":True,"archivo":name,"nombre_original":file.filename,"tamano":len(content)}

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
