from flask import Flask, jsonify, request
from datetime import datetime
import os
import time
import threading
import math

app = Flask(__name__)

# Configurar este secreto en las variables de entorno de Render
API_TOKEN = os.environ.get("API_TOKEN", "")

bloqueo = threading.Lock()

datos = {
    "temperatura": None,
    "conexion": "Esperando datos reales del PC",
    "hora": "--",
    "motor": "Sin datos",
    "velocidad": "Sin datos",
    "historial": []
}

ultima_lectura = 0
motor_encendido = False


def calcular_estado(temperatura):
    global motor_encendido

    if not motor_encendido and temperatura >= 25:
        motor_encendido = True
    elif motor_encendido and temperatura < 24:
        motor_encendido = False

    if not motor_encendido:
        return "APAGADO", "Sin velocidad"

    if temperatura >= 35:
        return "ENCENDIDO", "Alto"
    elif temperatura >= 30:
        return "ENCENDIDO", "Medio"

    return "ENCENDIDO", "Bajo"


@app.route("/")
def inicio():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#12263a">
<title>Detector Inteligente de Temperatura 4.0</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    padding: 20px;
    background: #eef2f7;
    color: #1e293b;
    font-family: Arial, sans-serif;
}
header {
    background: #12263a;
    color: white;
    padding: 26px;
    border-radius: 15px;
    margin-bottom: 20px;
}
header h1 { margin: 0 0 10px; }
header p { color: #cbd5e1; }
.aviso {
    padding: 12px;
    background: #e0f2fe;
    color: #075985;
    border-radius: 8px;
}
.contenedor {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
}
.tarjeta {
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 4px 15px #0000000c;
    min-width: 0;
}
.etiqueta { color: #64748b; font-size: 14px; }
.valor {
    font-size: clamp(25px, 4vw, 35px);
    font-weight: bold;
    margin: 20px 0;
    overflow-wrap: anywhere;
}
.temperatura { color: #16804a; }
.estado { color: #1675b9; }
.grafica { margin-top: 20px; }
canvas { width: 100%; height: 260px; display: block; }
footer {
    margin-top: 22px;
    color: #64748b;
    text-align: center;
    font-size: 13px;
}
@media (max-width: 480px) {
    body { padding: 12px; }
    header, .tarjeta { padding: 17px; }
}
</style>
</head>
<body>
<header>
    <h1>Detector Inteligente de Temperatura 4.0</h1>
    <p>Monitoreo térmico con PT100 y control del ventilador</p>
    <div class="aviso" id="aviso">
        Esperando lecturas reales del Arduino a través del PC.
    </div>
</header>

<div class="contenedor">
    <section class="tarjeta">
        <div class="etiqueta">Temperatura PT100</div>
        <div class="valor temperatura" id="temperatura">-- °C</div>
        <div class="etiqueta">Última temperatura recibida</div>
    </section>
    <section class="tarjeta">
        <div class="etiqueta">Conexión</div>
        <div class="valor estado" id="conexion">Esperando datos</div>
        <div class="etiqueta" id="hora">Última lectura: --</div>
    </section>
    <section class="tarjeta">
        <div class="etiqueta">Estado estimado del motor</div>
        <div class="valor estado" id="motor">Sin datos</div>
        <div class="etiqueta">Según los umbrales programados</div>
    </section>
    <section class="tarjeta">
        <div class="etiqueta">Nivel de velocidad solicitado</div>
        <div class="valor estado" id="velocidad">Sin datos</div>
        <div class="etiqueta">No representa RPM medidas</div>
    </section>
</div>

<section class="tarjeta grafica">
    <h2>Historial de temperatura</h2>
    <p class="etiqueta">Últimas 60 lecturas reales recibidas</p>
    <canvas id="grafica"></canvas>
</section>

<footer>
    Proyecto académico desarrollado con Python y Flask.
</footer>

<script>
let historialActual = [];

async function actualizar() {
    try {
        const respuesta = await fetch("/api/datos", {
            cache: "no-store"
        });
        const datos = await respuesta.json();

        document.getElementById("conexion").textContent =
            datos.conexion;
        document.getElementById("hora").textContent =
            "Última lectura: " + datos.hora;
        document.getElementById("motor").textContent =
            datos.motor;
        document.getElementById("velocidad").textContent =
            datos.velocidad;

        if (datos.temperatura !== null) {
            document.getElementById("temperatura").textContent =
                Number(datos.temperatura).toFixed(1) + " °C";
        } else {
            document.getElementById("temperatura").textContent = "-- °C";
        }

        document.getElementById("aviso").textContent =
            datos.conexion === "Arduino conectado mediante el PC"
            ? "Recibiendo mediciones reales del PT100."
            : "Esperando nuevas mediciones reales del Arduino a través del PC.";

        historialActual = datos.historial || [];
        dibujarGrafica();
    } catch (error) {
        document.getElementById("conexion").textContent =
            "Error de conexión";
    }
}

function dibujarGrafica() {
    const canvas = document.getElementById("grafica");
    const ctx = canvas.getContext("2d");
    const ancho = canvas.clientWidth;
    const alto = canvas.clientHeight;
    const escala = window.devicePixelRatio || 1;

    canvas.width = ancho * escala;
    canvas.height = alto * escala;
    ctx.setTransform(escala, 0, 0, escala, 0, 0);
    ctx.clearRect(0, 0, ancho, alto);

    if (!historialActual.length) {
        ctx.fillStyle = "#64748b";
        ctx.font = "15px Arial";
        ctx.fillText("Esperando mediciones reales...", 15, 30);
        return;
    }

    const valores = historialActual.map(p => p.temperatura);
    let minimo = Math.min(...valores);
    let maximo = Math.max(...valores);

    if (minimo === maximo) {
        minimo -= 1;
        maximo += 1;
    }

    const margen = 42;
    const anchoUtil = Math.max(1, ancho - margen - 12);
    const altoUtil = alto - margen * 2;

    ctx.font = "11px Arial";
    ctx.fillStyle = "#64748b";
    ctx.strokeStyle = "#e2e8f0";

    for (let i = 0; i <= 4; i++) {
        const y = margen + altoUtil * i / 4;
        ctx.beginPath();
        ctx.moveTo(margen, y);
        ctx.lineTo(ancho - 8, y);
        ctx.stroke();

        const valor = maximo - (maximo - minimo) * i / 4;
        ctx.fillText(valor.toFixed(1) + " °C", 2, y - 4);
    }

    ctx.strokeStyle = "#16804a";
    ctx.lineWidth = 2.5;
    ctx.beginPath();

    historialActual.forEach((p, i) => {
        const x = margen + anchoUtil *
            (historialActual.length === 1
                ? 0 : i / (historialActual.length - 1));
        const y = margen + altoUtil *
            (maximo - p.temperatura) / (maximo - minimo);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });

    ctx.stroke();
}

actualizar();
setInterval(actualizar, 2000);
window.addEventListener("resize", dibujarGrafica);
</script>
</body>
</html>
"""


@app.route("/api/recibir", methods=["POST"])
def recibir():
    global ultima_lectura

    if not API_TOKEN:
        return jsonify({"error": "Falta configurar API_TOKEN"}), 503

    if request.headers.get("Authorization") != f"Bearer {API_TOKEN}":
        return jsonify({"error": "No autorizado"}), 401

    contenido = request.get_json(silent=True) or {}

    try:
        temperatura = float(contenido["temperatura"])
        if not math.isfinite(temperatura) or not -50 <= temperatura <= 200:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Temperatura inválida"}), 400

    with bloqueo:
        hora = datetime.now().strftime("%H:%M:%S")
        motor, velocidad = calcular_estado(temperatura)

        datos["temperatura"] = round(temperatura, 1)
        datos["conexion"] = "Arduino conectado mediante el PC"
        datos["hora"] = hora
        datos["motor"] = motor
        datos["velocidad"] = velocidad

        datos["historial"].append({
            "hora": hora,
            "temperatura": round(temperatura, 1)
        })
        datos["historial"] = datos["historial"][-60:]
        ultima_lectura = time.time()

    return jsonify({"ok": True})


@app.route("/api/datos")
def api_datos():
    with bloqueo:
        resultado = dict(datos)
        resultado["historial"] = list(datos["historial"])

        if ultima_lectura == 0:
            resultado["conexion"] = "Esperando datos reales del PC"
            resultado["motor"] = "Sin datos"
            resultado["velocidad"] = "Sin datos"
        elif time.time() - ultima_lectura > 15:
            resultado["conexion"] = "PC sin lecturas recientes"

        return jsonify(resultado)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
