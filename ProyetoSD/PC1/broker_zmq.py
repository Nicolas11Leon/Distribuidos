# broker_zmq.py
# Broker ZeroMQ — recibe eventos de sensores y los reenvía a PC2
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def main():
    config = cargar_config()
    puerto_sub = config["red"]["puerto_broker_sub"]
    puerto_pub = config["red"]["puerto_broker_pub"]

    context = zmq.Context()

    # socket SUB: escucha a los sensores
    socket_sub = context.socket(zmq.SUB)
    socket_sub.bind(f"tcp://*:{puerto_sub}")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, "espira")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, "camara")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, "gps")

    # socket PUB: reenvía eventos hacia PC2
    socket_pub = context.socket(zmq.PUB)
    socket_pub.bind(f"tcp://*:{puerto_pub}")

    print(f"[BROKER] Escuchando sensores en puerto {puerto_sub}")
    print(f"[BROKER] Publicando hacia PC2 en puerto {puerto_pub}")
    print(f"[BROKER] Suscrito a topicos: espira, camara, gps")

    try:
        while True:
            mensaje = socket_sub.recv_string()
            topico = mensaje.split(" ")[0]
            datos = mensaje[len(topico)+1:]
            print(f"[BROKER] Recibido [{topico}] → reenviando a PC2")
            socket_pub.send_string(mensaje)
    except KeyboardInterrupt:
        print("[BROKER] Detenido por el usuario")
    finally:
        socket_sub.close()
        socket_pub.close()
        context.term()

if __name__ == "__main__":
    main()
