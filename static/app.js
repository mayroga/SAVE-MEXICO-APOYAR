```javascript
let servidorListo=false;

async function despertarServidor(){
    const estado=document.getElementById("servidor");
    try{
        const r=await fetch("/api/estado",{cache:"no-store"});
        if(r.ok){
            servidorListo=true;
            estado.textContent="Listo";
        }else{
            estado.textContent="Preparando...";
        }
    }catch(e){
        estado.textContent="Preparando...";
    }
}

function mostrar(id){
    document.querySelectorAll(".pantalla").forEach(x=>x.classList.remove("activa"));
    document.getElementById(id).classList.add("activa");
    window.scrollTo(0,0);
}

function entrar(){
    mostrar("paraQue");
}

async function abrirServicio(servicio){
    const titulo=document.getElementById("resultadoTitulo");
    const texto=document.getElementById("resultadoTexto");

    titulo.textContent="PREPARANDO...";
    texto.innerHTML="<p>Espera un momento.</p>";
    mostrar("resultado");

    try{
        const r=await fetch("/api/servicio/"+servicio,{cache:"no-store"});
        const data=await r.json();

        titulo.textContent=data.titulo;
        texto.innerHTML="<p>"+data.texto+"</p>";
    }catch(e){
        titulo.textContent="NO SE PUDO CONECTAR";
        texto.innerHTML="<p>Espera un momento y vuelve a intentarlo.</p>";
    }
}

despertarServidor();
```
