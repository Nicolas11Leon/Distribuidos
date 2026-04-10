# sensor_espira.py
# Sensor de espira inductiva — genera EVENTO_CONTEO_VEHICULAR
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time
import random
import sys
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

def crear_payload(interseccion, intervalo):
    # vehiculos contados entre 0 y 30 por intervalo
    vehiculos = random.randint(0, 30)
    ahora = datetime.now(timezone.utc)
    ts_inicio = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")
    ts_fin = datetime.fromtimestamp(
        ahora.timestamp() + intervalo, tz=timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "sensor_id": f"ESP-{interseccion}",
        "tipo_sensor": "espira_inductiva",
        "interseccion": f"INT-{interseccion}",
        "vehiculos_contados": vehiculos,
        "intervalo_segundos": intervalo,
        "timestamp_inicio": ts_inicio,
        "timestamp_fin": ts_fin
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

    # pausa inicial para que el broker este listo
    time.sleep(1)

    print(f"[ESPIRA] Iniciando {len(intersecciones)} sensores de espira")
    print(f"[ESPIRA] Conectado a tcp://{ip_pc1}:{puerto_sub}")

    try:
        while True:
            for interseccion in intersecciones:
                payload = crear_payload(interseccion, intervalo)
                topico = "espira"
                mensaje = f"{topico} {json.dumps(payload)}"
                socket.send_string(mensaje)
                print(f"[ESPIRA] {payload['sensor_id']} → "
                      f"vehiculos={payload['vehiculos_contados']} "
                      f"en {payload['interseccion']}")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("[ESPIRA] Detenido por el usuario")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    main()
