# bd_replica.py
# Base de datos replica — recibe eventos via PULL y los persiste localmente
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import sqlite3
import time
from datetime import datetime, timezone

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def inicializar_bd(ruta):
    conn = sqlite3.connect(ruta)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT,
            tipo_sensor TEXT,
            interseccion TEXT,
            datos TEXT,
            estado_trafico TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semaforos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semaforo_id TEXT,
            interseccion TEXT,
            estado TEXT,
            duracion INTEGER,
            motivo TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interseccion TEXT,
            tipo_alerta TEXT,
            descripcion TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    return conn

def main():
    config = cargar_config()
    puerto_pull = config["red"]["puerto_bd_replica"]

    conn = inicializar_bd("bd_replica.db")
    print("[BD_REPLICA] Base de datos replica inicializada")

    context = zmq.Context()
    socket_pull = context.socket(zmq.PULL)
    socket_pull.bind(f"tcp://*:{puerto_pull}")

    print(f"[BD_REPLICA] Escuchando en puerto {puerto_pull}")

    try:
        while True:
            msg = socket_pull.recv_json()
            accion = msg.get("accion", "")

            if accion == "guardar_evento":
                payload = msg.get("payload", {})
                estado = msg.get("estado_trafico", "NORMAL")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO eventos
                    (sensor_id, tipo_sensor, interseccion,
                    datos, estado_trafico, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    payload.get("sensor_id", ""),
                    payload.get("tipo_sensor", ""),
                    payload.get("interseccion", ""),
                    json.dumps(payload),
                    estado,
                    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                ))
                conn.commit()
                print(f"[BD_REPLICA] Evento guardado: "
                      f"{payload.get('sensor_id')} estado={estado}")

    except KeyboardInterrupt:
        print("[BD_REPLICA] Detenido por el usuario")
    finally:
        conn.close()
        socket_pull.close()
        context.term()

if __name__ == "__main__":
    main()
