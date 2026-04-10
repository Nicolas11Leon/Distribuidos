# semaforo.py
# Semaforo inteligente — recibe comandos de control de semaforos desde PC2
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time
import threading

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

class Semaforo:
    def __init__(self, interseccion, config):
        self.interseccion = interseccion
        self.semaforo_id = f"SEM-{interseccion}"
        self.estado = "ROJO"
        self.tiempo_verde = config["semaforos"]["tiempo_verde_normal"]
        self.tiempo_rojo = config["semaforos"]["tiempo_rojo_normal"]

    def cambiar_estado(self, nuevo_estado, duracion=None):
        self.estado = nuevo_estado
        if duracion:
            if nuevo_estado == "VERDE":
                self.tiempo_verde = duracion
            else:
                self.tiempo_rojo = duracion
        print(f"[SEMAFORO] {self.semaforo_id} → {self.estado} "
              f"(duracion={duracion or 'normal'}s) "
              f"en INT-{self.interseccion} "
              f"ts={time.time():.6f}")

def main():
    config = cargar_config()
    puerto_pull = config["red"]["puerto_semaforos_pull"]
    intersecciones = generar_intersecciones(config)

    # crear semaforos para todas las intersecciones
    semaforos = {i: Semaforo(i, config) for i in intersecciones}

    context = zmq.Context()
    socket_pull = context.socket(zmq.PULL)
    socket_pull.bind(f"tcp://*:{puerto_pull}")

    print(f"[SEMAFORO] {len(semaforos)} semaforos iniciados en estado ROJO")
    print(f"[SEMAFORO] Escuchando comandos en puerto {puerto_pull}")

    try:
        while True:
            mensaje = socket_pull.recv_json()
            interseccion = mensaje.get("interseccion", "").replace("INT-", "")
            estado = mensaje.get("estado", "VERDE")
            duracion = mensaje.get("duracion_segundos", None)

            if interseccion in semaforos:
                semaforos[interseccion].cambiar_estado(estado, duracion)
            else:
                print(f"[SEMAFORO] Interseccion desconocida: {interseccion}")
    except KeyboardInterrupt:
        print("[SEMAFORO] Detenido por el usuario")
    finally:
        socket_pull.close()
        context.term()

if __name__ == "__main__":
    main()

