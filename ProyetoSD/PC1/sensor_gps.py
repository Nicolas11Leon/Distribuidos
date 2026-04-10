# sensor_gps.py
# Sensor GPS — genera EVENTO_DENSIDAD_DE_TRAFICO
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time
import random
from datetime import datetime, timezone

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def generar_intersecciones(config):
    filas = config["ciudad"]["filas"]
    cols = config["ciudad"]["cols"]
    intersecciones = []
    for fila in filas:
        for col in range(1, cols + 1):
            intersecciones.append(f"{fila}{col}")
    return intersecciones

def calcular_nivel_congestion(velocidad):
    # ALTA: menor a 10 km/h, NORMAL: entre 11 y 39, BAJA: mayor a 40
    if velocidad < 10:
        return "ALTA"
    elif velocidad <= 39:
        return "NORMAL"
    else:
        return "BAJA"

def crear_payload(interseccion):
    velocidad = round(random.uniform(0, 50), 1)
    nivel = calcular_nivel_congestion(velocidad)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "sensor_id": f"GPS-{interseccion}",
        "tipo_sensor": "gps",
        "interseccion": f"INT-{interseccion}",
        "velocidad_promedio": velocidad,
        "nivel_congestion": nivel,
        "timestamp": timestamp
    }

def main():
    config = cargar_config()
    intervalo = config["sensores"]["intervalo_segundos"]
    ip_pc1 = config["red"]["ip_pc1"]
    puerto_sub = config["red"]["puerto_broker_sub"]

    intersecciones = generar_intersecciones(config)

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect(f"tcp://{ip_pc1}:{puerto_sub}")

    time.sleep(1)

    print(f"[GPS] Iniciando {len(intersecciones)} sensores GPS")
    print(f"[GPS] Conectado a tcp://{ip_pc1}:{puerto_sub}")

    try:
        while True:
            for interseccion in intersecciones:
                payload = crear_payload(interseccion)
                topico = "gps"
                mensaje = f"{topico} {json.dumps(payload)}"
                socket.send_string(mensaje)
                print(f"[GPS] {payload['sensor_id']} → "
                      f"vel={payload['velocidad_promedio']} km/h "
                      f"congestion={payload['nivel_congestion']} "
                      f"en {payload['interseccion']}")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("[GPS] Detenido por el usuario")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
