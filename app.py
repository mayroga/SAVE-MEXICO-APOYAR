import os,json,secrets,uuid,re
from datetime import datetime
from pathlib import Path
from typing import Any,Optional
import stripe
from fastapi import FastAPI,HTTPException,Request,UploadFile,File
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
STATIC=BASE/"static"
DATA=BASE/"data"
OUT=BASE/"out"
TRAMITES=DATA/"tramites.json"
STATIC.mkdir(parents=True,exist_ok=True)
DATA.mkdir(parents=True,exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)

ADMIN_USERNAME=os.getenv("ADMIN_USERNAME","")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","")
STRIPE_SECRET_KEY=os.getenv("STRIPE_SECRET_KEY","")
STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET","")
APP_URL=os.getenv("APP_URL","https://save-mexico-apoyar.onrender.com").rstrip("/")
PRICE_DAILY=os.getenv("STRIPE_PRICE_ID_DAILY") or os.getenv("STRIPE_PRICE_ID1","")
PRICE_MONTHLY=os.getenv("STRIPE_PRICE_ID_MONTHLY") or os.getenv("STRIPE_PRICE_ID2","")
PRICE_ANNUAL=os.getenv("STRIPE_PRICE_ID_ANNUAL","")

if STRIPE_SECRET_KEY:
    stripe.api_key=STRIPE_SECRET_KEY

app=FastAPI(title="SAVE MÉXICO AYUDAR",version="5.1.0")
app.mount("/static",StaticFiles(directory=str(STATIC)),name="static")

ADMIN_TOKENS=set()
ACCESS_TOKENS=set()

class Login(BaseModel):
    username:str
    password:str

class Checkout(BaseModel):
    plan:str

class Guide(BaseModel):
    tramite:str
    modalidad:str=""
    datos_personales:dict=Field(default_factory=dict)
    datos_especificos:dict=Field(default_factory=dict)
    documentos:dict=Field(default_factory=dict)
    documentos_disponibles:list=Field(default_factory=list)
    documentos_faltantes:list=Field(default_factory=list)
    documentos_dudosos:list=Field(default_factory=list)
    situaciones:list=Field(default_factory=list)
    aclaraciones:list=Field(default_factory=list)
    idioma:str="es"

def load_data():
    if not TRAMITES.exists():
        raise HTTPException(500,"No existe data/tramites.json.")
    try:
        return json.loads(TRAMITES.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(500,f"No se pudo leer tramites.json: {e}")

def get_tramites():
    x=load_data().get("tramites",{})
    return x if isinstance(x,dict) else {}

def get_tramite(tid):
    t=get_tramites().get(tid)
    if not t: raise HTTPException(404,"Trámite no encontrado.")
    return t

def get_modalidad(tid,mid):
    m=get_tramite(tid).get("modalidades",{}).get(mid)
    if not m: raise HTTPException(404,"Modalidad no encontrada.")
    return m

def new_token(store):
    token=secrets.token_urlsafe(32)
    store.add(token)
    return token

def cookie_access(request):
    a=request.cookies.get("save_admin_token")
    p=request.cookies.get("save_access_token")
    return a in ADMIN_TOKENS,p in ACCESS_TOKENS

def require_access(request):
    admin,paid=cookie_access(request)
    if not(admin or paid):
        raise HTTPException(401,"Se requiere acceso autorizado.")
    return True

def clean_name(name):
    return re.sub(r"[^A-Za-z0-9._-]","_",str(name))[:120]

def txt(v):
    if v is None:return ""
    if isinstance(v,bool):return "Sí" if v else "No"
    if isinstance(v,(list,tuple,set)):return ", ".join(txt(x) for x in v)
    if isinstance(v,dict):return ", ".join(f"{k}: {txt(x)}" for k,x in v.items())
    return str(v)

def norm(v):
    return re.sub(r"\s+"," ",txt(v)).strip().lower()

def label(v):
    s=re.sub(r"[_-]+"," ",str(v))
    return s[:1].upper()+s[1:]

def question_map(m):
    return {str(x.get("id")):x for x in m.get("preguntas",[]) if isinstance(x,dict)}

def flatten_values(v):
    if isinstance(v,(list,tuple,set)):
        out=[]
        for x in v:out.extend(flatten_values(x))
        return out
    if isinstance(v,dict):
        out=[]
        for x in v.values():out.extend(flatten_values(x))
        return out
    return [txt(v)]

def selected_values(respuestas):
    out=[]
    for v in respuestas.values():out.extend(flatten_values(v))
    return [x for x in out if x!=""]

def find_question(qmap,key):
    if key in qmap:return qmap[key]
    nk=norm(key)
    for k,q in qmap.items():
        if nk==norm(k) or nk==norm(q.get("texto","")):return q
    return {}

def answer_for(respuestas,key):
    if key in respuestas:return respuestas[key]
    nk=norm(key)
    for k,v in respuestas.items():
        if nk==norm(k):return v
    return None

def answer_has(respuestas,terms):
    if isinstance(terms,str):terms=[terms]
    terms=[norm(x) for x in terms]
    return any(t and (norm(v)==t or t in norm(v))
               for v in selected_values(respuestas) for t in terms)

def values_match(value,expected):
    vals=[norm(x) for x in flatten_values(value)]
    exps=[norm(x) for x in flatten_values(expected)]
    return any(e and (v==e or e in v or v in e) for v in vals for e in exps)

def condition_match(respuestas,condition):
    if not condition or not isinstance(condition,dict):return True
    key=condition.get("respuesta") or condition.get("pregunta") or condition.get("campo")
    value=answer_for(respuestas,key) if key else None
    vals=flatten_values(value)
    if "incluye" in condition:return values_match(value,condition["incluye"])
    if "contiene" in condition:return values_match(value,condition["contiene"])
    if "igual_a" in condition or "es" in condition:
        return values_match(value,condition.get("igual_a",condition.get("es")))
    if "distinto_de" in condition:
        return not values_match(value,condition["distinto_de"])
    if "no_es" in condition:return not values_match(value,condition["no_es"])
    if "no_incluye" in condition:return not values_match(value,condition["no_incluye"])
    if "alguno_de" in condition:
        return any(values_match(value,x) for x in condition["alguno_de"])
    if "todos_de" in condition:
        return all(values_match(value,x) for x in condition["todos_de"])
    if "cantidad_mayor_que" in condition:
        return len([x for x in vals if txt(x)])>float(condition["cantidad_mayor_que"])
    if "cantidad_igual_a" in condition:
        return len([x for x in vals if txt(x)])==int(condition["cantidad_igual_a"])
    if "existe" in condition:
        return (value not in (None,"",[],{}))==bool(condition["existe"])
    return True

def question_visible(q,respuestas):
    if not isinstance(q,dict):return False
    cond=q.get("mostrar_si") or q.get("si") or q.get("condicion") or q.get("cuando")
    if not cond:return True
    if isinstance(cond,list):return all(condition_match(respuestas,x) for x in cond)
    return condition_match(respuestas,cond)

def visible_questions(m,respuestas):
    return [q for q in m.get("preguntas",[])
            if isinstance(q,dict) and question_visible(q,respuestas)]

def unanswered_required(m,respuestas):
    missing=[]
    for q in visible_questions(m,respuestas):
        if not q.get("obligatoria",False):continue
        qid=str(q.get("id",""))
        if not qid:continue
        v=answer_for(respuestas,qid)
        if v is None or v=="" or v==[] or v=={}:
            missing.append(q.get("texto",label(qid)))
    return missing

def dynamic_situations(m,respuestas):
    found=[]
    qmap=question_map(m)
    for key,value in respuestas.items():
        q=find_question(qmap,key)
        if not q or not question_visible(q,respuestas):continue
        special=q.get("situaciones") or q.get("casos_especiales") or []
        if isinstance(special,str):special=[special]
        for val in flatten_values(value):
            nv=norm(val)
            for s in special:
                if norm(s) and (norm(s) in nv or nv in norm(s)) and s not in found:
                    found.append(s)
            if any(x in nv for x in ["perdí","perdi","robaron","robada","robado","extrav","perdida"]):
                if "Pérdida, robo o extravío de documento" not in found:
                    found.append("Pérdida, robo o extravío de documento")
            if any(x in nv for x in ["diferente","distinto","no coincide","error","corregir","corrección"]):
                if "Diferencias o errores entre documentos" not in found:
                    found.append("Diferencias o errores entre documentos")
            if any(x in nv for x in ["vencid","caduc"]):
                if "Documento vencido" not in found:
                    found.append("Documento vencido")
    return found

def document_condition(d,respuestas):
    if not isinstance(d,dict):return True
    cond=d.get("mostrar_si") or d.get("si") or d.get("condicion") or d.get("cuando")
    if not cond:return True
    if isinstance(cond,list):return all(condition_match(respuestas,x) for x in cond)
    return condition_match(respuestas,cond)

def document_items(m):
    base=m.get("documentos",[]) or []
    if isinstance(base,dict):
        out=[]
        for k,v in base.items():
            if isinstance(v,dict):
                x=dict(v)
                x.setdefault("id",k)
                x.setdefault("nombre",k)
                out.append(x)
            else:
                out.append({"id":k,"nombre":k,"obligatorio":bool(v)})
        return out
    out=[]
    for d in base:
        if isinstance(d,dict):
            x=dict(d)
            x.setdefault("id",x.get("nombre",""))
            out.append(x)
        else:
            out.append({"id":str(d),"nombre":str(d),"obligatorio":True})
    return out

def normalize_document_names(value):
    if isinstance(value,dict):
        result=[]
        for k,v in value.items():
            if isinstance(v,dict):
                status=v.get("estado") or v.get("status")
                if norm(status) in ("lo_tengo","disponible","si","sí","tengo"):
                    result.append(k)
            elif isinstance(v,str) and norm(v) in ("lo_tengo","disponible","si","sí","tengo"):
                result.append(k)
        return result
    return [txt(x) for x in flatten_values(value) if txt(x)]

def document_status_map(g):
    result={}
    groups=[
        ("LO_TENGO",g.documentos_disponibles),
        ("NO_LO_TENGO",g.documentos_faltantes),
        ("NO_ESTOY_SEGURO",g.documentos_dudosos)
    ]
    for status,items in groups:
        for x in normalize_document_names(items):
            result[norm(x)]=status
    if isinstance(g.documentos,dict):
        for k,v in g.documentos.items():
            if isinstance(v,dict):
                s=v.get("estado") or v.get("status")
            else:s=v
            if s:result[norm(k)]=txt(s)
    return result

def document_rules(m,respuestas,disponibles,faltantes,dudosos,documentos=None):
    result=[]
    status_map=document_status_map(Guide(
        tramite="",modalidad="",documentos=documentos or {},
        documentos_disponibles=disponibles or [],
        documentos_faltantes=faltantes or [],
        documentos_dudosos=dudosos or []
    ))
    def add(d,status="POR_REVISAR",reason=""):
        if not d:return
        did=norm(d.get("id") or d.get("nombre") or d.get("documento") or d.get("titulo"))
        name=d.get("nombre") or d.get("documento") or d.get("titulo") or did
        for x in result:
            if norm(x["id"])==did:return
        result.append({
            "id":did,
            "documento":txt(name),
            "estado":status,
            "motivo":txt(reason),
            "confirmar":bool(d.get("confirmar",False)),
            "obligatorio":bool(d.get("obligatorio",d.get("requerido",True))),
            "bloque":d.get("bloque","")
        })
    for d in document_items(m):
        if not document_condition(d,respuestas):continue
        did=norm(d.get("id") or d.get("nombre") or d.get("documento") or d.get("titulo"))
        status=status_map.get(did)
        if status:
            ns=norm(status)
            if ns in ("lo_tengo","disponible","si","sí","tengo"):
                status="LO_TENGO"
            elif ns in ("no_lo_tengo","falta","faltante","no"):
                status="NO_LO_TENGO"
            elif ns in ("no_estoy_seguro","dudoso","revision","revisión_necesaria"):
                status="NO_ESTOY_SEGURO"
            elif ns in ("no_aplica","no aplica"):
                status="NO_APLICA"
            else:status="POR_REVISAR"
        else:status="POR_REVISAR"
        add(d,status,d.get("motivo") or d.get("razon",""))
    return result

def contradictions(g,m):
    issues=[]
    respuestas=g.datos_especificos or {}
    disp={norm(x) for x in normalize_document_names(g.documentos_disponibles)}
    falt={norm(x) for x in normalize_document_names(g.documentos_faltantes)}
    duda={norm(x) for x in normalize_document_names(g.documentos_dudosos)}
    for x in sorted(disp&falt):
        issues.append(f"El documento «{x}» aparece como disponible y faltante.")
    for x in sorted(disp&duda):
        issues.append(f"El documento «{x}» aparece como disponible y dudoso.")
    for x in sorted(falt&duda):
        issues.append(f"El documento «{x}» aparece como faltante y dudoso.")
    for q in visible_questions(m,respuestas):
        if q.get("tipo") in ("single","select","radio") and q.get("obligatoria"):
            v=answer_for(respuestas,str(q.get("id","")))
            if isinstance(v,list) and len(v)>1:
                issues.append(f"La pregunta «{q.get('texto','')}» recibió varias respuestas cuando requiere una sola.")
    for v in selected_values(respuestas):
        if norm(v) in ("otro","__otro__"):
            if not answer_has(respuestas,["detalle","especifica","especifique"]):
                issues.append("Se seleccionó «Otro» y debe explicarse qué situación corresponde.")
            break
    return issues

def evaluate_case(g,m):
    respuestas=g.datos_especificos or {}
    qmap=question_map(m)
    situations=[]
    for x in m.get("casos_especiales",[]) or []:
        if answer_has(respuestas,[x]) and x not in situations:situations.append(x)
    for x in dynamic_situations(m,respuestas):
        if x not in situations:situations.append(x)
    issues=contradictions(g,m)
    pending=unanswered_required(m,respuestas)
    docs=document_rules(m,respuestas,g.documentos_disponibles,
                        g.documentos_faltantes,g.documentos_dudosos,g.documentos)
    for d in docs:
        if d["estado"]=="POR_REVISAR":
            for x in g.aclaraciones:
                if norm(d["documento"]) in norm(x) or norm(d["id"]) in norm(x):
                    d["estado"]="REQUIERE_CONFIRMACION"
                    break
    missing=[d["documento"] for d in docs if d["estado"]=="NO_LO_TENGO" and d["obligatorio"]]
    doubtful=[d["documento"] for d in docs if d["estado"]=="NO_ESTOY_SEGURO" or d["estado"]=="REQUIERE_CONFIRMACION"]
    if pending or issues:
        status="Necesita aclaración"
    elif missing:
        status="Falta documentación"
    elif doubtful:
        status="Revisión necesaria"
    else:
        status="Preparación avanzada"
    return {
        "estado":status,
        "documentos":docs,
        "faltantes":missing,
        "dudosos":doubtful,
        "situaciones":situations,
        "contradicciones":issues,
        "preguntas":qmap,
        "preguntas_pendientes":pending
    }

def pdf_line(c,text,x,y,width=500,size=10,leading=14):
    c.setFont("Helvetica",size)
    lines=simpleSplit(txt(text),"Helvetica",size,width) or [""]
    for line in lines:
        if y<55:
            c.showPage()
            y=LETTER[1]-55
            c.setFont("Helvetica",size)
        c.drawString(x,y,line)
        y-=leading
    return y

def pdf_section(c,title,y):
    if y<85:
        c.showPage()
        y=LETTER[1]-55
    c.setFont("Helvetica-Bold",12)
    c.drawString(45,y,title)
    return y-19

def pdf_bullet(c,text,y):
    return pdf_line(c,f"• {text}",55,y,480,10,14)

def pdf_document(c,d,y):
    if y<105:
        c.showPage()
        y=LETTER[1]-55
    c.setFont("Helvetica-Bold",10)
    y=pdf_line(c,f"DOCUMENTO: {d.get('id','')}",55,y,480,10,13)
    y=pdf_line(c,f"Nombre: {d.get('documento','')}",70,y,465,10,13)
    y=pdf_line(c,f"Estado: {label(d.get('estado',''))}",70,y,465,10,13)
    if d.get("obligatorio"):
        y=pdf_line(c,"Importancia: documento aplicable al caso.",70,y,465,9,12)
    if d.get("motivo"):
        y=pdf_line(c,f"Nota: {d['motivo']}",70,y,465,9,12)
    if d.get("confirmar"):
        y=pdf_line(c,"CONFIRMAR CON LA AUTORIDAD antes de acudir.",70,y,465,9,12)
    return y-5

def make_pdf(g):
    t=get_tramite(g.tramite)
    m=get_modalidad(g.tramite,g.modalidad)
    evaluation=evaluate_case(g,m)
    nombre=t.get("nombre",g.tramite)
    modalidad=m.get("nombre",g.modalidad)
    autoridad=t.get("autoridad","")
    now=datetime.now().strftime("%Y-%m-%d %H:%M")
    filename=clean_name(f"guia_{g.tramite}_{g.modalidad}_{uuid.uuid4().hex[:10]}.pdf")
    path=OUT/filename
    c=canvas.Canvas(str(path),pagesize=LETTER)
    c.setTitle(f"SAVE MÉXICO AYUDAR - {nombre}")
    y=LETTER[1]-50

    c.setFont("Helvetica-Bold",18)
    c.drawString(45,y,"SAVE MÉXICO AYUDAR")
    y-=25
    y=pdf_line(c,nombre,45,y,500,14,18)
    y=pdf_line(c,f"Modalidad: {modalidad}",45,y-3,500,10,14)
    if autoridad:y=pdf_line(c,f"Autoridad: {autoridad}",45,y-2,500,10,14)
    y=pdf_line(c,f"Preparado: {now}",45,y-2,500,9,13)
    y-=8

    y=pdf_section(c,"1. RESULTADO DE LA REVISIÓN",y)
    estado=evaluation["estado"]
    y=pdf_line(c,f"Estado del caso: {estado}",55,y,480,11,15)
    mensajes={
        "Preparación avanzada":"La información proporcionada permite continuar con la preparación.",
        "Falta documentación":"Todavía existe documentación marcada como faltante.",
        "Necesita aclaración":"Antes de considerar el caso preparado deben aclararse las situaciones indicadas.",
        "Revisión necesaria":"Existen documentos o circunstancias que requieren revisión antes de acudir."
    }
    y=pdf_line(c,mensajes.get(estado,"Debe revisarse la información del caso."),55,y,480)

    if evaluation["preguntas_pendientes"]:
        y-=5
        y=pdf_section(c,"2. PREGUNTAS O DATOS PENDIENTES",y)
        for x in evaluation["preguntas_pendientes"]:y=pdf_bullet(c,x,y)

    y-=5
    y=pdf_section(c,"3. DATOS PERSONALES",y)
    if g.datos_personales:
        for k,v in g.datos_personales.items():
            if v not in ("",None,[],{}):
                y=pdf_line(c,f"{label(k)}: {txt(v)}",55,y,480)
    else:y=pdf_line(c,"No se proporcionaron datos personales.",55,y,480)

    y-=5
    y=pdf_section(c,"4. SITUACIÓN DEL TRÁMITE",y)
    if g.datos_especificos:
        qmap=question_map(m)
        for k,v in g.datos_especificos.items():
            q=find_question(qmap,k)
            if q and not question_visible(q,g.datos_especificos):continue
            y=pdf_line(c,q.get("texto",label(k)),55,y,480,10,14)
            y=pdf_line(c,f"Respuesta: {txt(v) if txt(v) else 'Sin respuesta'}",70,y,465,10,14)
            y-=2
    else:y=pdf_line(c,"No se proporcionaron respuestas específicas.",55,y,480)

    y-=5
    y=pdf_section(c,"5. DOCUMENTOS APLICABLES A ESTE CASO",y)
    docs=evaluation["documentos"]
    if docs:
        for d in docs:y=pdf_document(c,d,y)
    else:y=pdf_line(c,"No se pudo determinar un documento aplicable. POR CONFIRMAR CON LA AUTORIDAD.",55,y,480)

    y-=5
    y=pdf_section(c,"6. DOCUMENTOS QUE LA PERSONA DECLARA TENER",y)
    disponibles=normalize_document_names(g.documentos_disponibles)
    if disponibles:
        for d in disponibles:y=pdf_bullet(c,d,y)
    else:y=pdf_line(c,"No se identificó ningún documento como disponible.",55,y,480)

    y-=5
    y=pdf_section(c,"7. DOCUMENTOS FALTANTES",y)
    if evaluation["faltantes"]:
        for d in evaluation["faltantes"]:y=pdf_bullet(c,d,y)
    else:y=pdf_line(c,"No se identificó documentación faltante en las respuestas proporcionadas.",55,y,480)

    y-=5
    y=pdf_section(c,"8. DOCUMENTOS O SITUACIONES POR REVISAR",y)
    if evaluation["dudosos"]:
        for d in evaluation["dudosos"]:y=pdf_bullet(c,d,y)
    else:y=pdf_line(c,"No se identificaron documentos marcados como dudosos.",55,y,480)

    if evaluation["situaciones"]:
        y-=5
        y=pdf_section(c,"9. SITUACIONES ESPECÍFICAS DETECTADAS",y)
        for x in evaluation["situaciones"]:y=pdf_bullet(c,x,y)

    if evaluation["contradicciones"]:
        y-=5
        y=pdf_section(c,"10. ACLARACIONES NECESARIAS",y)
        for x in evaluation["contradicciones"]:y=pdf_bullet(c,x,y)

    y-=5
    y=pdf_section(c,"11. INFORMACIÓN QUE DEBE CONFIRMARSE",y)
    confirm=[]
    for x in g.aclaraciones:
        if x not in confirm:confirm.append(x)
    for x in evaluation["preguntas_pendientes"]:
        z=f"Completar: {x}"
        if z not in confirm:confirm.append(z)
    if evaluation["dudosos"]:
        confirm.append("Confirmar con la autoridad la aceptación de los documentos o circunstancias marcadas para revisión.")
    if any(d.get("confirmar") for d in docs):
        confirm.append("Confirmar con la autoridad los documentos señalados expresamente como POR CONFIRMAR.")
    if not confirm:
        confirm=["Verificar la información oficial vigente antes de acudir."]
    for x in confirm:y=pdf_bullet(c,x,y)

    y-=5
    y=pdf_section(c,"12. INFORMACIÓN OFICIAL Y ADVERTENCIAS",y)
    warnings=[
        "Esta guía es un servicio privado de organización y preparación documental.",
        "SAVE MÉXICO AYUDAR no es el Gobierno de México, la SRE, un Consulado ni el INE.",
        "La guía no sustituye la decisión ni las instrucciones de la autoridad competente.",
        "Los requisitos, documentos aceptados, costos, citas y procedimientos pueden cambiar.",
        "No se garantiza la aprobación del trámite.",
        "Una situación especial o una duda no resuelta debe confirmarse antes de acudir."
    ]
    for x in warnings:y=pdf_bullet(c,x,y)

    y-=5
    y=pdf_section(c,"13. FUENTES OFICIALES",y)
    fuentes=t.get("fuentes",[]) or m.get("fuentes",[])
    if fuentes:
        for x in fuentes:y=pdf_bullet(c,x,y)
    else:y=pdf_line(c,"POR CONFIRMAR CON LA AUTORIDAD.",55,y,480)

    y-=10
    y=pdf_line(c,"Documento generado por SAVE MÉXICO AYUDAR.",45,y,500,8,11)
    pdf_line(c,"Verifique la información oficial vigente antes de acudir.",45,y,500,8,11)
    c.save()
    return path

@app.get("/")
async def home():
    p=STATIC/"index.html"
    if not p.exists():raise HTTPException(404,"No existe static/index.html.")
    return FileResponse(str(p))

@app.get("/api/check-access")
async def check_access(request:Request):
    admin,paid=cookie_access(request)
    return {"access":bool(admin or paid),"admin":admin,"paid":paid}

@app.post("/api/admin-login")
async def admin_login(data:Login):
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise HTTPException(503,"El acceso administrativo no está configurado.")
    if not secrets.compare_digest(data.username,ADMIN_USERNAME) or not secrets.compare_digest(data.password,ADMIN_PASSWORD):
        raise HTTPException(401,"Usuario o contraseña incorrectos.")
    token=new_token(ADMIN_TOKENS)
    r=JSONResponse({"ok":True,"access":True,"admin":True,"message":"Acceso administrativo autorizado."})
    r.set_cookie("save_admin_token",token,httponly=True,secure=True,samesite="lax",max_age=86400)
    return r

@app.post("/api/create-checkout-session")
async def create_checkout_session(data:Checkout):
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado.")
    prices={"daily":PRICE_DAILY,"monthly":PRICE_MONTHLY,"annual":PRICE_ANNUAL}
    price=prices.get(data.plan)
    if not price:raise HTTPException(400,"Plan de pago no configurado.")
    try:
        mode="subscription" if data.plan in ("monthly","annual") else "payment"
        s=stripe.checkout.Session.create(
            mode=mode,
            line_items=[{"price":price,"quantity":1}],
            success_url=f"{APP_URL}/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?payment=cancelled",
            metadata={"plan":data.plan,"app":"save_mexico_ayudar"},
            allow_promotion_codes=True
        )
        return {"ok":True,"id":s.id,"url":s.url}
    except Exception as e:
        raise HTTPException(500,f"No se pudo crear el pago: {e}")

@app.get("/api/verify-payment")
async def verify_payment(session_id:str):
    if not STRIPE_SECRET_KEY:raise HTTPException(503,"Stripe no está configurado.")
    if not session_id:raise HTTPException(400,"Falta session_id.")
    try:
        s=stripe.checkout.Session.retrieve(session_id)
        paid=s.get("payment_status")=="paid"
        complete=s.get("status")=="complete"
        if not paid or not complete:
            return {"access":False,"paid":False,"status":s.get("status"),"payment_status":s.get("payment_status")}
        token=new_token(ACCESS_TOKENS)
        r=JSONResponse({"access":True,"paid":True,"status":"complete"})
        r.set_cookie("save_access_token",token,httponly=True,secure=True,samesite="lax",max_age=86400)
        return r
    except Exception as e:
        raise HTTPException(400,f"No se pudo verificar el pago: {e}")

@app.post("/api/webhook/stripe")
async def stripe_webhook(request:Request):
    payload=await request.body()
    signature=request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:raise HTTPException(503,"Webhook de Stripe no configurado.")
    try:
        event=stripe.Webhook.construct_event(payload,signature,STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400,"Webhook inválido.")
    return {"received":True,"event":event.get("type","")}

@app.get("/api/tramites")
async def tramites(request:Request):
    require_access(request)
    return {
        "tramites":[
            {
                "id":tid,
                "nombre":t.get("nombre",tid),
                "nombre_corto":t.get("nombre_corto",t.get("nombre",tid)),
                "autoridad":t.get("autoridad","")
            }
            for tid,t in get_tramites().items()
        ]
    }

@app.get("/api/modalidades")
async def modalidades(tramite:str,request:Request):
    require_access(request)
    t=get_tramite(tramite)
    return {
        "tramite":tramite,
        "modalidades":[
            {"id":mid,"nombre":m.get("nombre",mid),"descripcion":m.get("descripcion","")}
            for mid,m in t.get("modalidades",{}).items()
        ]
    }

@app.get("/api/ficha-tramite")
async def ficha_tramite(tramite:str,request:Request,modalidad:Optional[str]=None):
    require_access(request)
    t=get_tramite(tramite)
    if modalidad:
        m=get_modalidad(tramite,modalidad)
        return {
            "tramite":tramite,
            "nombre":t.get("nombre",tramite),
            "autoridad":t.get("autoridad",""),
            "modalidad":modalidad,
            "ficha":m,
            "fuentes":t.get("fuentes",[])
        }
    return {
        "tramite":tramite,
        "nombre":t.get("nombre",tramite),
        "autoridad":t.get("autoridad",""),
        "modalidades":{
            k:{"nombre":v.get("nombre",k),"descripcion":v.get("descripcion","")}
            for k,v in t.get("modalidades",{}).items()
        },
        "fuentes":t.get("fuentes",[])
    }

@app.get("/api/perfil-tramite")
async def perfil_tramite(tramite:str,request:Request,modalidad:Optional[str]=None):
    require_access(request)
    t=get_tramite(tramite)
    base={
        "tramite":tramite,
        "nombre":t.get("nombre",tramite),
        "autoridad":t.get("autoridad",""),
        "costo":t.get("costo",""),
        "vigencia":t.get("vigencia",""),
        "cita":t.get("cita",""),
        "fuentes":t.get("fuentes",[])
    }
    if modalidad:
        m=get_modalidad(tramite,modalidad)
        base.update({"modalidad":modalidad,"modalidad_nombre":m.get("nombre",modalidad)})
    else:
        base["modalidades"]={k:v.get("nombre",k) for k,v in t.get("modalidades",{}).items()}
    return base

@app.get("/api/pregunta")
async def pregunta(tramite:str,modalidad:str,numero:int,request:Request):
    require_access(request)
    m=get_modalidad(tramite,modalidad)
    preguntas=m.get("preguntas",[])
    if numero<0 or numero>=len(preguntas):
        raise HTTPException(404,"Pregunta no encontrada.")
    q=dict(preguntas[numero])
    q.setdefault("tipo","single")
    q.setdefault("opciones",q.get("options",[]))
    q.setdefault("permite_multiple",q.get("tipo") in ("multiple","multi_select"))
    q.setdefault("permite_otro",True)
    return {
        "numero":numero,
        "total":len(preguntas),
        "pregunta":q
    }

@app.post("/api/resultado-tramite")
async def resultado_tramite(payload:dict,request:Request):
    require_access(request)
    tramite=payload.get("tramite")
    modalidad=payload.get("modalidad")
    if not tramite or not modalidad:
        raise HTTPException(400,"Faltan trámite o modalidad.")
    m=get_modalidad(tramite,modalidad)
    g=Guide(
        tramite=tramite,
        modalidad=modalidad,
        datos_personales=payload.get("datos_personales") or {},
        datos_especificos=payload.get("datos_especificos") or {},
        documentos=payload.get("documentos") or {},
        documentos_disponibles=payload.get("documentos_disponibles") or [],
        documentos_faltantes=payload.get("documentos_faltantes") or [],
        documentos_dudosos=payload.get("documentos_dudosos") or [],
        situaciones=payload.get("situaciones") or [],
        aclaraciones=payload.get("aclaraciones") or [],
        idioma=payload.get("idioma","es")
    )
    r=evaluate_case(g,m)
    return {
        "ok":True,
        "tramite":tramite,
        "modalidad":modalidad,
        "modalidad_nombre":m.get("nombre",modalidad),
        "estado":r["estado"],
        "listo":r["estado"]=="Preparación avanzada",
        "documentos_correspondientes":r["documentos"],
        "documentos_disponibles":normalize_document_names(g.documentos_disponibles),
        "documentos_faltantes":r["faltantes"],
        "documentos_dudosos":r["dudosos"],
        "respuestas":g.datos_especificos,
        "situaciones":r["situaciones"],
        "contradicciones":r["contradicciones"],
        "preguntas_pendientes":r["preguntas_pendientes"],
        "siguiente_accion":(
            "Completar las preguntas pendientes." if r["preguntas_pendientes"] else
            "Aclarar las respuestas indicadas." if r["contradicciones"] else
            "Completar los documentos faltantes." if r["faltantes"] else
            "Revisar los documentos marcados." if r["dudosos"] else
            "Continuar con la preparación de la guía."
        ),
        "pdf":m.get("pdf",{})
    }

@app.post("/api/generar-guia-consular")
async def generar_guia(g:Guide,request:Request):
    require_access(request)
    if g.tramite not in get_tramites():
        raise HTTPException(404,"Trámite no encontrado.")
    if g.modalidad not in get_tramite(g.tramite).get("modalidades",{}):
        raise HTTPException(404,"Modalidad no encontrada.")
    try:
        result=evaluate_case(g,get_modalidad(g.tramite,g.modalidad))
        path=make_pdf(g)
        return {
            "ok":True,
            "filename":path.name,
            "file":path.name,
            "download":f"/descargar/{path.name}",
            "estado":result["estado"],
            "listo":result["estado"]=="Preparación avanzada",
            "faltantes":result["faltantes"],
            "dudosos":result["dudosos"],
            "contradicciones":result["contradicciones"],
            "preguntas_pendientes":result["preguntas_pendientes"]
        }
    except Exception as e:
        raise HTTPException(500,f"No se pudo generar el PDF: {e}")

@app.post("/api/extraer-pdf")
async def extraer_pdf(request:Request,file:UploadFile=File(...)):
    require_access(request)
    if not(file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400,"El archivo debe ser PDF.")
    raw=await file.read()
    if len(raw)>15*1024*1024:
        raise HTTPException(400,"El PDF supera el tamaño permitido.")
    temp=OUT/f"tmp_{uuid.uuid4().hex}.pdf"
    try:
        temp.write_bytes(raw)
        reader=PdfReader(str(temp))
        text="\n".join((p.extract_text() or "") for p in reader.pages)
        return {"ok":True,"filename":file.filename,"pages":len(reader.pages),"text":text[:100000]}
    except Exception as e:
        raise HTTPException(400,f"No se pudo leer el PDF: {e}")
    finally:
        try:temp.unlink(missing_ok=True)
        except Exception:pass

@app.post("/api/subir-fotos")
async def subir_fotos(request:Request,files:list[UploadFile]=File(...)):
    require_access(request)
    saved=[]
    allowed={".jpg",".jpeg",".png",".webp"}
    for f in files[:10]:
        ext=Path(f.filename or "").suffix.lower()
        if ext not in allowed:continue
        raw=await f.read()
        if len(raw)>8*1024*1024:continue
        name=f"foto_{uuid.uuid4().hex}{ext}"
        (OUT/name).write_bytes(raw)
        saved.append(name)
    return {"ok":True,"files":saved}

@app.get("/descargar/{nombre}")
async def descargar(nombre:str,request:Request):
    require_access(request)
    safe=Path(nombre).name
    path=OUT/safe
    if not path.exists() or path.suffix.lower()!=".pdf":
        raise HTTPException(404,"Archivo no encontrado.")
    return FileResponse(
        str(path),
        media_type="application/pdf",
        filename=safe,
        headers={"Content-Disposition":f'attachment; filename="{safe}"'}
    )

@app.get("/api/fuentes")
async def fuentes(request:Request,tramite:Optional[str]=None):
    require_access(request)
    if tramite:
        t=get_tramite(tramite)
        return {"tramite":tramite,"fuentes":t.get("fuentes",[])}
    data=load_data()
    return {
        "fuentes_generales":data.get("fuentes_oficiales",{}),
        "nota":data.get("nota_general","")
    }

@app.post("/api/logout")
async def logout(request:Request):
    a=request.cookies.get("save_admin_token")
    p=request.cookies.get("save_access_token")
    if a:ADMIN_TOKENS.discard(a)
    if p:ACCESS_TOKENS.discard(p)
    r=JSONResponse({"ok":True})
    r.delete_cookie("save_admin_token")
    r.delete_cookie("save_access_token")
    return r

@app.get("/health")
async def health():
    data=load_data()
    return {
        "ok":True,
        "app":"SAVE MÉXICO AYUDAR",
        "version":"5.1.0",
        "datos_version":data.get("version",""),
        "datos_actualizado":data.get("actualizado",""),
        "tramites":list(get_tramites().keys()),
        "stripe":bool(STRIPE_SECRET_KEY),
        "stripe_webhook":bool(STRIPE_WEBHOOK_SECRET),
        "admin_configured":bool(ADMIN_USERNAME and ADMIN_PASSWORD)
    }

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")))
