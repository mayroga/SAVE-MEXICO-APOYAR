import os,io,html
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse,StreamingResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from consular_engine import iniciar,interpretar,continuar,seleccionar_caso

app=FastAPI(title="MEXICANO APOYA MEXICANO",version="5.2.0")
os.makedirs("static",exist_ok=True)
app.mount("/static",StaticFiles(directory="static"),name="static")

def limpio(v):
    return "" if v is None else str(v).strip()

def esc(v):
    return html.escape(limpio(v))

def lista(v):
    return [limpio(x) for x in v] if isinstance(v,list) else []

def unicos(v):
    r=[]
    for x in lista(v):
        if x and x not in r:r.append(x)
    return r

def pendiente(v):
    return limpio(v) or "PENDIENTE DE COMPLETAR"

def datos_personales(r):
    p=r.get("perfil") or {}
    return [
        ("Nombre",p.get("nombre")),
        ("Nacionalidad",p.get("nacionalidad")),
        ("Teléfono",p.get("telefono")),
        ("Dirección",p.get("direccion")),
        ("Estado",p.get("estado")),
        ("ZIP",p.get("zip")),
        ("Correo",p.get("email"))
    ]

def build_pdf(r):
    b=io.BytesIO()
    doc=SimpleDocTemplate(
        b,pagesize=letter,leftMargin=42,rightMargin=42,
        topMargin=42,bottomMargin=42,
        title="Hoja de Ruta - MEXICANO APOYA MEXICANO"
    )
    s=getSampleStyleSheet()
    titulo=ParagraphStyle(
        "titulo",parent=s["Title"],fontName="Helvetica-Bold",
        fontSize=17,leading=21,alignment=TA_CENTER,
        textColor=colors.HexColor("#17324d"),spaceAfter=7
    )
    subt=ParagraphStyle(
        "sub",parent=s["Normal"],fontName="Helvetica",
        fontSize=9,leading=12,alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),spaceAfter=18
    )
    sec=ParagraphStyle(
        "sec",parent=s["Heading2"],fontName="Helvetica-Bold",
        fontSize=11,leading=14,textColor=colors.HexColor("#17324d"),
        spaceBefore=14,spaceAfter=8
    )
    body=ParagraphStyle(
        "body",parent=s["BodyText"],fontName="Helvetica",
        fontSize=9.5,leading=13,spaceAfter=5
    )
    small=ParagraphStyle(
        "small",parent=body,fontSize=8.5,leading=11,
        textColor=colors.HexColor("#555555")
    )

    story=[
        Paragraph("MEXICANO APOYA MEXICANO",titulo),
        Paragraph("HOJA DE RUTA PERSONAL PARA TU TRÁMITE CONSULAR",subt)
    ]

    nivel=r.get("nivel","amarillo")
    estado=r.get("estado_texto","TE FALTA ALGO")
    bg={"verde":"#d9f4e5","amarillo":"#fff2c2","rojo":"#f8d7da"}.get(nivel,"#fff2c2")
    fg={"verde":"#176b3a","amarillo":"#785900","rojo":"#8b1e28"}.get(nivel,"#785900")

    tb=Table([[Paragraph(f"<b>{esc(estado)}</b>",body)]],colWidths=[doc.width])
    tb.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor(bg)),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor(fg)),
        ("BOX",(0,0),(-1,-1),0.7,colors.HexColor(fg)),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),9),
        ("BOTTOMPADDING",(0,0),(-1,-1),9)
    ]))
    story.extend([tb,Spacer(1,10)])

    def section(n,t):
        story.append(Paragraph(f"{n}. {esc(t)}",sec))

    def bullets(items,texto="PENDIENTE DE COMPLETAR"):
        items=unicos(items)
        if not items:
            story.append(Paragraph(texto,body))
            return
        for x in items:
            story.append(Paragraph("• "+esc(x),body))

    section(1,"DATOS PERSONALES")
    rows=[]
    for k,v in datos_personales(r):
        rows.append([
            Paragraph(f"<b>{esc(k)}</b>",body),
            Paragraph(esc(pendiente(v)),body)
        ])
    tb=Table(rows,colWidths=[130,doc.width-130])
    tb.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#ccd4dc")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#eef2f5")),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),7),
        ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story.append(tb)

    section(2,"TU TRÁMITE")
    story.append(Paragraph(
        esc(r.get("tramite") or r.get("titulo") or "PENDIENTE DE COMPLETAR"),body
    ))

    section(3,"PERSONAS QUE DEBEN PRESENTARSE")
    bullets(r.get("personas_obligatorias"))

    section(4,"REQUISITOS OBLIGATORIOS")
    bullets(r.get("requisitos_obligatorios"))

    opc=unicos(r.get("opcionales"))
    if opc:
        story.append(Paragraph("<b>REQUISITOS OPCIONALES</b>",body))
        bullets(opc)

    section(5,"LO QUE YA TIENES")
    bullets(r.get("tiene"))

    section(6,"LO QUE TE FALTA")
    bullets(r.get("falta"))

    section(7,"LO QUE DEBES CONFIRMAR")
    bullets(r.get("revisar"))

    section(8,"¿QUÉ DEBES HACER?")
    acciones=unicos(r.get("acciones"))
    if acciones:
        for i,x in enumerate(acciones,1):
            story.append(Paragraph(f"<b>{i}.</b> {esc(x)}",body))
    else:
        story.append(Paragraph(
            "Reúne los documentos indicados y confirma los puntos pendientes antes de acudir.",body
        ))

    section(9,"CITA")
    bullets(r.get("cita"),"Confirma si necesitas cita para la modalidad elegida.")

    section(10,"DOCUMENTOS ORIGINALES")
    bullets(r.get("originales"))

    section(11,"COPIAS")
    copias=unicos(r.get("copias"))
    if copias:
        bullets(copias)
    else:
        story.append(Paragraph("No se identificaron copias obligatorias.",body))

    section(12,"PAGO")
    story.append(Paragraph(
        esc(r.get("pago") or "Confirma la tarifa vigente antes de acudir."),body
    ))

    section(13,"ANTES DE FIRMAR O IMPRIMIR")
    story.append(Paragraph(
        esc(r.get("revision") or "Revisa cuidadosamente todos tus datos."),body
    ))

    n=14
    if r.get("vigencia"):
        section(n,"VIGENCIA")
        story.append(Paragraph(esc(r["vigencia"]),body))
        n+=1

    if r.get("entrega"):
        section(n,"ENTREGA")
        story.append(Paragraph(esc(r["entrega"]),body))
        n+=1

    section(n,"INFORMACIÓN IMPORTANTE")
    importantes=unicos(r.get("importante"))
    bullets(importantes,"No se identificó información adicional.")
    n+=1

    section(n,"INFORMACIÓN OFICIAL")
    fuente=limpio(r.get("fuente"))
    if fuente:
        story.append(Paragraph("Consulta siempre la fuente oficial correspondiente:",body))
        story.append(Paragraph(esc(fuente),small))
    else:
        story.append(Paragraph("PENDIENTE DE COMPLETAR",body))

    story.extend([
        Spacer(1,18),
        Paragraph(
            "<b>IMPORTANTE:</b> Esta aplicación es independiente. "
            "No es el Gobierno de México ni representa a ningún Consulado. "
            "La información se organiza como apoyo para preparar tu trámite. "
            "La autoridad consular determina los requisitos aplicables y puede "
            "solicitar documentación o información adicional.",small
        ),
        Spacer(1,8),
        Paragraph(
            "Revisa tus datos personales y tus documentos antes de acudir.",small
        )
    ])

    doc.build(story)
    b.seek(0)
    return b

@app.get("/")
async def inicio():
    return FileResponse("static/index.html")

@app.get("/api/estado")
async def estado():
    return {"status":"ok","app":"MEXICANO APOYA MEXICANO","version":"5.2.0"}

@app.get("/api/inicio/{servicio}")
async def api_inicio_get(servicio:str):
    if servicio not in ("cita","documento"):
        raise HTTPException(400,"Servicio no válido.")
    try:
        return iniciar(servicio,{})
    except Exception as e:
        raise HTTPException(500,f"No se pudo iniciar: {e}")

@app.post("/api/inicio/{servicio}")
async def api_inicio_servicio(servicio:str,request:Request):
    if servicio not in ("cita","documento"):
        raise HTTPException(400,"Servicio no válido.")
    try:
        try:x=await request.json()
        except Exception:x={}
        r=x.get("respuestas") or {}
        texto=limpio(x.get("texto") or x.get("mensaje"))
        return iniciar(servicio,r,texto)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500,f"No se pudo iniciar: {e}")

@app.post("/api/iniciar")
async def api_iniciar(request:Request):
    try:
        x=await request.json()
        servicio=limpio(x.get("servicio") or "cita")
        if servicio not in ("cita","documento"):
            raise HTTPException(400,"Servicio no válido.")
        return iniciar(
            servicio,
            x.get("respuestas") or {},
            limpio(x.get("texto") or x.get("mensaje"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400,f"No se pudo iniciar: {e}")

@app.post("/api/entender")
async def api_entender(request:Request):
    try:
        x=await request.json()
        servicio=limpio(x.get("servicio") or "cita")
        texto=limpio(x.get("texto") or x.get("mensaje"))
        if not texto:
            raise HTTPException(400,"Escribe o dicta la información.")
        return interpretar(
            servicio,texto,x.get("respuestas") or {},
            limpio(x.get("pregunta_id"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500,f"Error procesando la información: {e}")

@app.post("/api/responder")
async def api_responder(request:Request):
    try:
        x=await request.json()
        caso=limpio(x.get("caso") or x.get("tramite") or x.get("id"))
        pid=limpio(x.get("pregunta_id"))
        texto=limpio(x.get("texto") or x.get("respuesta") or x.get("valor"))
        if not caso:
            raise HTTPException(400,"No se identificó el trámite.")
        return continuar(caso,x.get("respuestas") or {},pid,texto)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500,f"Error procesando respuesta: {e}")

@app.post("/api/seleccionar")
async def api_seleccionar(request:Request):
    try:
        x=await request.json()
        caso=limpio(x.get("caso") or x.get("tramite") or x.get("id"))
        if not caso:
            raise HTTPException(400,"No se seleccionó un trámite.")
        return seleccionar_caso(
            caso,
            x.get("respuestas") or {},
            limpio(x.get("texto") or x.get("mensaje"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500,f"No se pudo seleccionar el trámite: {e}")

@app.post("/api/pdf")
async def api_pdf(request:Request):
    try:
        r=await request.json()
        if isinstance(r.get("resultado"),dict):
            r=r["resultado"]
        if not r.get("tramite") and not r.get("titulo"):
            raise HTTPException(400,"No existe una Hoja de Ruta para generar.")
        pdf=build_pdf(r)
        return StreamingResponse(
            pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                'attachment; filename="hoja_ruta_mexicano_apoya_mexicano.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500,f"No se pudo generar el PDF: {e}")

@app.post("/api/generar-pdf")
async def api_generar_pdf(request:Request):
    return await api_pdf(request)

@app.post("/api/pdf-hoja-ruta")
async def api_pdf_hoja_ruta(request:Request):
    return await api_pdf(request)

@app.exception_handler(Exception)
async def error_general(request:Request,exc:Exception):
    return JSONResponse(
        status_code=500,
        content={"error":"Error interno del servidor."}
    )

if __name__=="__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")),reload=False)
