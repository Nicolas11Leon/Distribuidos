# health_check.py
# Health check — monitorea PC3 y activa replica si falla
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time
import sqlite3
from datetime import datetime, timezone

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def main():
    config = cargar_config()
    ip_pc3 = config["red"]["ip_pc3"]
    puerto_hc = config["red"]["puerto_healthcheck"]
    intervalo = config["healthcheck"]["intervalo_heartbeat"]
    timeout = config["healthcheck"]["timeout_segundos"]
    intervalo_reconexion = config["healthcheck"]["intervalo_reconexion"]

    context = zmq.Context()

    pc3_activo = True
    bd_activa = "principal"

    print("[HEALTHCHECK] Iniciando monitoreo de PC3")

    while True:
        # crear socket REQ nuevo en cada intento para evitar bloqueos
        socket_req = context.socket(zmq.REQ)
        socket_req.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        socket_req.setsockopt(zmq.LINGER, 0)
        socket_req.connect(f"tcp://{ip_pc3}:{puerto_hc}")

        try:
            socket_req.send_json({"tipo": "heartbeat"})
            respuesta = socket_req.recv_json()

            if respuesta.get("status") == "ok":
                if not pc3_activo:
                    # PC3 se recupero
                    print("[HEALTHCHECK] PC3 recuperado — "
                          "iniciando sincronizacion")
                    pc3_activo = True
                    bd_activa = "principal"
                    # notificar a analitica (escribir en archivo de estado)
                    with open("estado_sistema.json", "w") as f:
                        json.dump({"bd_activa": "principal"}, f)
                    print("[HEALTHCHECK] BD principal activa nuevamente")
                else:
                    print(f"[HEALTHCHECK] PC3 OK — "
                          f"ts={datetime.now(timezone.utc).strftime('%H:%M:%S')}")

        except zmq.error.Again:
            # timeout — PC3 no responde
            if pc3_activo:
                pc3_activo = False
                bd_activa = "replica"
                print("[HEALTHCHECK] ALERTA: PC3 no responde — "
                      "activando BD replica")
                # notificar a analitica via archivo de estado
                with open("estado_sistema.json", "w") as f:
                    json.dump({"bd_activa": "replica"}, f)
                print("[HEALTHCHECK] BD replica activa en PC2")
            else:
                print("[HEALTHCHECK] PC3 sigue caido — "
                      "manteniendo replica activa")

        except Exception as e:
            print(f"[HEALTHCHECK] Error: {e}")

        finally:
            socket_req.close()

        # esperar segun estado de PC3
        if pc3_activo:
            time.sleep(intervalo)
        else:
            time.sleep(intervalo_reconexion)

if __name__ == "__main__":
    main()
