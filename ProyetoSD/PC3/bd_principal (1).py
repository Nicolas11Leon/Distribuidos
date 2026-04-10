# bd_principal.py
# Base de datos principal — recibe eventos via PULL y los persiste
# Tambien responde heartbeats del health check de PC2
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import sqlite3
import time
import threading
from datetime import datetime, timezone

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def inicializar_bd(ruta):
    conn = sqlite3.connect(ruta, check_same_thread=False)
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

# ── Hilo PULL — recibe y guarda eventos desde analitica ──────────────────────

def hilo_recibir_eventos(config, conn):
    puerto_pull = config["red"]["puerto_bd_principal"]
    lock = threading.Lock()

    context = zmq.Context()
    socket_pull = context.socket(zmq.PULL)
    socket_pull.bind(f"tcp://*:{puerto_pull}")

    print(f"[BD_PRINCIPAL] Escuchando eventos en puerto {puerto_pull}")

    try:
        while True:
            msg = socket_pull.recv_json()
            accion = msg.get("accion", "")

            if accion == "guardar_evento":
                payload = msg.get("payload", {})
                estado = msg.get("estado_trafico", "NORMAL")
                with lock:
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
                        datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                    ))
                    conn.commit()
                print(f"[BD_PRINCIPAL] Evento guardado: "
                      f"{payload.get('sensor_id')} estado={estado}")

            elif accion == "guardar_semaforo":
                with lock:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO semaforos
                        (semaforo_id, interseccion, estado,
                        duracion, motivo, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        msg.get("semaforo_id", ""),
                        msg.get("interseccion", ""),
                        msg.get("estado", ""),
                        msg.get("duracion", 0),
                        msg.get("motivo", ""),
                        datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                    ))
                    conn.commit()
                print(f"[BD_PRINCIPAL] Semaforo guardado: "
                      f"{msg.get('interseccion')} → {msg.get('estado')}")

            elif accion == "guardar_alerta":
                with lock:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO alertas
                        (interseccion, tipo_alerta, descripcion, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (
                        msg.get("interseccion", ""),
                        msg.get("tipo_alerta", ""),
                        msg.get("descripcion", ""),
                        datetime.now(timezone.utc).strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                    ))
                    conn.commit()
                print(f"[BD_PRINCIPAL] Alerta guardada: "
                      f"{msg.get('interseccion')} "
                      f"tipo={msg.get('tipo_alerta')}")

            elif accion == "sincronizar":
                # recibe lista de eventos faltantes durante la caida
                eventos = msg.get("eventos", [])
                with lock:
                    cursor = conn.cursor()
                    for ev in eventos:
                        cursor.execute("""
                            INSERT OR IGNORE INTO eventos
                            (sensor_id, tipo_sensor, interseccion,
                            datos, estado_trafico, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            ev.get("sensor_id", ""),
                            ev.get("tipo_sensor", ""),
                            ev.get("interseccion", ""),
                            ev.get("datos", "{}"),
                            ev.get("estado_trafico", "NORMAL"),
                            ev.get("timestamp", "")
                        ))
                    conn.commit()
                print(f"[BD_PRINCIPAL] Sincronizacion completada: "
                      f"{len(eventos)} eventos importados")

    except KeyboardInterrupt:
        print("[BD_PRINCIPAL] Hilo de eventos detenido")
    finally:
        socket_pull.close()
        context.term()

# ── Hilo REP — responde heartbeats del health check ──────────────────────────

def hilo_heartbeat(config):
    puerto_hc = config["red"]["puerto_healthcheck"]

    context = zmq.Context()
    socket_rep = context.socket(zmq.REP)
    socket_rep.bind(f"tcp://*:{puerto_hc}")

    print(f"[BD_PRINCIPAL] Heartbeat escuchando en puerto {puerto_hc}")

    try:
        while True:
            msg = socket_rep.recv_json()
            if msg.get("tipo") == "heartbeat":
                socket_rep.send_json({"status": "ok"})
                print(f"[BD_PRINCIPAL] Heartbeat respondido — "
                      f"ts={datetime.now(timezone.utc).strftime('%H:%M:%S')}")
            else:
                socket_rep.send_json({"status": "ok"})
    except KeyboardInterrupt:
        print("[BD_PRINCIPAL] Hilo heartbeat detenido")
    finally:
        socket_rep.close()
        context.term()

def main():
    config = cargar_config()
    conn = inicializar_bd("bd_principal.db")
    print("[BD_PRINCIPAL] Base de datos principal inicializada")

    t1 = threading.Thread(
        target=hilo_recibir_eventos,
        args=(config, conn),
        daemon=True
    )
    t2 = threading.Thread(
        target=hilo_heartbeat,
        args=(config,),
        daemon=True
    )

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[BD_PRINCIPAL] Detenido por el usuario")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
