
from flask import Flask, jsonify
from datetime import datetime, timedelta
import os
import random
import time
import threading

app = Flask(__name__)

# Datos de demostración: no requiere Arduino
bloqueo = threading.Lock()

temperatura = 24.0
motor_encendido = False
ultima_actualizacion = time.monotonic()

# Historial inicial para mostrar la gráfica
valores_iniciales = [
    21.5, 22.0, 22.8, 23.2, 22.7,
    23.8, 24.4, 25.2, 24.8, 25.6,
    24.9, 24.2, 23.7, 24.5, 24.0
]

historial = []

for i, valor in enumerate(valores_iniciales):
    momento = datetime.now() - timedelta(
        seconds=(len(valores_iniciales) - i) * 2
    )

    historial.append({
        "hora": momento.strftime("%H:%M:%S"),
        "temperatura": valor
    })

temperatura = valores_iniciales[-1]


def obtener_estado(temp):
    global motor_encendido

    # Encender a 25 °C y apagar por debajo de 24 °C
    if not motor_encendido and temp >= 25:
        motor_encendido = True
    elif motor_encendido and temp < 24:
        motor_encendido = False

    if not motor_encendido:
        return "APAGADO", "Sin velocidad"

    if temp >= 35:
        return "ENCENDIDO", "Alto"

    if temp >= 30:
        return "ENCENDIDO", "Medio"

    return "ENCENDIDO", "Bajo"


def actualizar_datos():
    global temperatura, ultima_actualizacion

    with bloqueo:
        ahora = time.monotonic()

        # Actualizar cada dos segundos
        if ahora - ultima_actualizacion >= 2:
            # Variación simulada para la demostración
            temperatura += random.uniform(-0.7, 0.7)
            temperatura = max(20.0, min(38.0, temperatura))

            ultima_actualizacion = ahora

            historial.append({
                "hora": datetime.now().strftime("%H:%M:%S"),
                "temperatura": round(temperatura, 1)
            })

            # Conservar las últimas 60 lecturas
            del historial[:-60]

        motor, velocidad = obtener_estado(temperatura)

        return {
            "temperatura": round(temperatura, 1),
            "conexion": "Servidor en línea · DEMO",
            "hora": datetime.now().strftime("%H:%M:%S"),
            "motor": motor,
            "velocidad": velocidad,
            "historial": list(historial),
            "modo": "Demostración con datos simulados"
        }


@app.route("/")
def inicio():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#12263a">

<title>Detector Inteligente 4.0</title>

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

header h1 {
    margin: 0 0 10px;
    font-size: clamp(23px, 4vw, 34px);
}

header p {
    color: #cbd5e1;
    margin: 0;
}

.aviso {
    margin-top: 16px;
    padding: 10px 13px;
    border-radius: 8px;
    background: #fff7d6;
    color: #805b00;
    font-size: 13px;
}

.contenedor {
    display: grid;
    grid-template-columns:
        repeat(auto-fit, minmax(min(100%, 220px), 1fr));
    gap: 16px;
}

.tarjeta {
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 4px 15px #0000000c;
    min-width: 0;
}

.etiqueta {
    color: #64748b;
    font-size: 14px;
}

.valor {
    font-size: clamp(25px, 5vw, 35px);
    font-weight: bold;
    margin: 20px 0;
    overflow-wrap: anywhere;
}

.temperatura { color: #16804a; }
.estado { color: #1675b9; }

.grafica { margin-top: 20px; }

canvas {
    width: 100%;
    height: 260px;
    display: block;
}

footer {
    margin-top: 22px;
    color: #64748b;
    text-align: center;
    font-size: 13px;
}

@media (max-width: 480px) {
    body { padding: 12px; }
    header { padding: 20px; }
    .tarjeta { padding: 17px; }
}
</style>
</head>

<body>

<header>
    <h1>Detector Inteligente de Temperatura 4.0</h1>
    <p>Monitoreo térmico y control automático del ventilador</p>
    <div class="aviso">
        MODO DEMOSTRACIÓN: los valores son simulados,
        no son mediciones de un sensor real.
    </div>
</header>

<div class="contenedor">

    <section class="tarjeta">
        <div class="etiqueta">Temperatura PT100</div>
        <div class="valor temperatura" id="temperatura">-- °C</div>
        <div class="etiqueta">Temperatura de demostración</div>
    </section>

    <section class="tarjeta">
        <div class="etiqueta">Servidor</div>
        <div class="valor estado" id="conexion">Conectando...</div>
        <div class="etiqueta" id="hora">Última actualización: --</div>
    </section>

    <section class="tarjeta">
        <div class="etiqueta">Estado estimado del motor</div>
        <div class="valor estado" id="motor">--</div>
        <div class="etiqueta">Según los umbrales programados</div>
    </section>

    <section class="tarjeta">
        <div class="etiqueta">Nivel de velocidad solicitado</div>
        <div class="valor estado" id="velocidad">--</div>
        <div class="etiqueta">No representa RPM medidas</div>
    </section>

</div>

<section class="tarjeta grafica">
    <h2>Historial de temperatura</h2>
    <p class="etiqueta">Últimas 60 lecturas simuladas</p>
    <canvas id="grafica"></canvas>
</section>

<footer>
    Proyecto académico desarrollado con Python y Flask.
    <br>Datos de demostración; no controla un motor real.
</footer>

<script>
let historialActual = [];

async function actualizar() {
    try {
        const respuesta = await fetch("/api/datos", {
            cache: "no-store"
        });

        if (!respuesta.ok) {
            throw new Error("Respuesta del servidor incorrecta");
        }

        const datos = await respuesta.json();

        document.getElementById("conexion").textContent =
            datos.conexion;

        document.getElementById("hora").textContent =
            "Última actualización: " + datos.hora;

        document.getElementById("motor").textContent =
            datos.motor;

        document.getElementById("velocidad").textContent =
            datos.velocidad;

        document.getElementById("temperatura").textContent =
            Number(datos.temperatura).toFixed(1) + " °C";

        historialActual = datos.historial || [];
        dibujarGrafica();

    } catch (error) {
        document.getElementById("conexion").textContent =
            "Reconectando...";
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

    if (historialActual.length === 0) {
        ctx.fillStyle = "#64748b";
        ctx.font = "14px Arial";
        ctx.fillText("Esperando datos...", 15, 30);
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
    const altoUtil = alto - 2 * margen;

    ctx.font = "11px Arial";
    ctx.fillStyle = "#64748b";
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;

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
                ? 0
                : i / (historialActual.length - 1));

        const y = margen + altoUtil *
            (maximo - p.temperatura) / (maximo - minimo);

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
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


@app.route("/api/datos")
def api_datos():
    return jsonify(actualizar_datos())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
