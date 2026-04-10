# control_semaforos.py
# Control de semaforos — recibe comandos y los envia a los semaforos en PC1
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def main():
    config = cargar_config()
    puerto_pull = config["red"]["puerto_ctrl_semaforos"]
    ip_pc1 = config["red"]["ip_pc1"]
    puerto_sem = config["red"]["puerto_semaforos_pull"]

    context = zmq.Context()

    # PULL: recibe comandos del servicio de analitica
    socket_pull = context.socket(zmq.PULL)
    socket_pull.connect(f"tcp://localhost:{puerto_pull}")

    # PUSH: envia comandos a los semaforos en PC1
    socket_push = context.socket(zmq.PUSH)
    socket_push.connect(f"tcp://{ip_pc1}:{puerto_sem}")

    print(f"[CTRL_SEM] Escuchando comandos en puerto {puerto_pull}")
    print(f"[CTRL_SEM] Enviando ordenes a semaforos en "
          f"tcp://{ip_pc1}:{puerto_sem}")

    try:
        while True:
            cmd = socket_pull.recv_json()
            interseccion = cmd.get("interseccion", "")
            estado = cmd.get("estado", "VERDE")
            duracion = cmd.get("duracion_segundos", 15)
            motivo = cmd.get("motivo", "automatico")

            print(f"[CTRL_SEM] Ejecutando: {interseccion} → {estado} "
                  f"({duracion}s) motivo={motivo}")

            socket_push.send_json(cmd)

    except KeyboardInterrupt:
        print("[CTRL_SEM] Detenido por el usuario")
    finally:
        socket_pull.close()
        socket_push.close()
        context.term()

if __name__ == "__main__":
    main()
