# sensor_camara.py
# Sensor de camara de trafico — genera EVENTO_LONGITUD_COLA
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

def crear_payload(interseccion):
    # volumen: num vehiculos en espera (cola)
    volumen = random.randint(0, 20)
    # velocidad promedio entre 0 y 50 km/h
    velocidad = round(random.uniform(0, 50), 1)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "sensor_id": f"CAM-{interseccion}",
        "tipo_sensor": "camara",
        "interseccion": f"INT-{interseccion}",
        "volumen": volumen,
        "velocidad_promedio": velocidad,
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

    print(f"[CAMARA] Iniciando {len(intersecciones)} sensores de camara")
    print(f"[CAMARA] Conectado a tcp://{ip_pc1}:{puerto_sub}")

    try:
        while True:
            for interseccion in intersecciones:
                payload = crear_payload(interseccion)
                topico = "camara"
                mensaje = f"{topico} {json.dumps(payload)}"
                socket.send_string(mensaje)
                print(f"[CAMARA] {payload['sensor_id']} → "
                      f"volumen={payload['volumen']} "
                      f"vel={payload['velocidad_promedio']} km/h "
                      f"en {payload['interseccion']}")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("[CAMARA] Detenido por el usuario")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()




