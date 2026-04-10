# servicio_analitica.py
# Servicio de analitica — procesa eventos, detecta congestion y controla semaforos
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time
import threading
import sqlite3
from datetime import datetime, timezone

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def evaluar_estado(cola, velocidad, volumen):
    if velocidad < 5:
        return "PRIORIZACION"
    if cola >= 10 and velocidad < 15 and volumen >= 15:
        return "CONGESTION"
    if cola < 5 and velocidad > 35 and volumen < 8:
        return "NORMAL"
    return "NORMAL"

def inicializar_bd(ruta):
    conn = sqlite3.connect(ruta, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT, tipo_sensor TEXT, interseccion TEXT,
            datos TEXT, estado_trafico TEXT, timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semaforos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semaforo_id TEXT, interseccion TEXT, estado TEXT,
            duracion INTEGER, motivo TEXT, timestamp TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interseccion TEXT, tipo_alerta TEXT,
            descripcion TEXT, timestamp TEXT
        )
    """)
    conn.commit()
    return conn

estado_sistema = {"bd_activa": "principal"}
lock_estado = threading.Lock()
lock_bd = threading.Lock()

def guardar_evento(conn, payload, estado_trafico):
    with lock_bd:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO eventos
            (sensor_id, tipo_sensor, interseccion, datos, estado_trafico, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            payload.get("sensor_id", ""),
            payload.get("tipo_sensor", ""),
            payload.get("interseccion", ""),
            json.dumps(payload),
            estado_trafico,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ))
        conn.commit()

def guardar_alerta(conn, interseccion, tipo, descripcion):
    with lock_bd:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO alertas (interseccion, tipo_alerta, descripcion, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            interseccion, tipo, descripcion,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ))
        conn.commit()

def guardar_cambio_semaforo(conn, interseccion, estado, duracion, motivo):
    with lock_bd:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO semaforos
            (semaforo_id, interseccion, estado, duracion, motivo, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f"SEM-{interseccion.replace('INT-', '')}",
            interseccion, estado, duracion, motivo,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ))
        conn.commit()

def hilo_procesar_eventos(config, conn, socket_push_ctrl,
                          socket_push_bd_principal):
    ip_pc1 = config["red"]["ip_pc1"]
    puerto_pub = config["red"]["puerto_broker_pub"]

    context = zmq.Context()
    socket_sub = context.socket(zmq.SUB)
    socket_sub.connect(f"tcp://{ip_pc1}:{puerto_pub}")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, "espira")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, "camara")
    socket_sub.setsockopt_string(zmq.SUBSCRIBE, "gps")

    print(f"[ANALITICA] Suscrito al broker en tcp://{ip_pc1}:{puerto_pub}")

    datos_interseccion = {}

    while True:
        try:
            mensaje = socket_sub.recv_string()
            topico = mensaje.split(" ")[0]
            payload = json.loads(mensaje[len(topico)+1:])
            interseccion = payload.get("interseccion", "")

            if interseccion not in datos_interseccion:
                datos_interseccion[interseccion] = {
                    "cola": 0, "velocidad": 50.0, "volumen": 0
                }

            if topico == "camara":
                datos_interseccion[interseccion]["cola"] = payload.get("volumen", 0)
                datos_interseccion[interseccion]["velocidad"] = payload.get("velocidad_promedio", 50.0)
            elif topico == "espira":
                intervalo = payload.get("intervalo_segundos", 30)
                vehiculos = payload.get("vehiculos_contados", 0)
                datos_interseccion[interseccion]["volumen"] = round(
                    vehiculos / intervalo * 60, 1)
            elif topico == "gps":
                datos_interseccion[interseccion]["velocidad"] = payload.get(
                    "velocidad_promedio", 50.0)

            d = datos_interseccion[interseccion]
            estado = evaluar_estado(d["cola"], d["velocidad"], d["volumen"])

            print(f"[ANALITICA] {interseccion} → estado={estado} "
                  f"cola={d['cola']} vel={d['velocidad']} vol={d['volumen']}")

            guardar_evento(conn, payload, estado)

            with lock_estado:
                bd_activa = estado_sistema["bd_activa"]

            if bd_activa == "principal":
                socket_push_bd_principal.send_json({
                    "accion": "guardar_evento",
                    "payload": payload,
                    "estado_trafico": estado
                })

            if estado == "CONGESTION":
                guardar_alerta(conn, interseccion, "CONGESTION",
                               f"cola={d['cola']} vel={d['velocidad']}")
                print(f"[ANALITICA] ALERTA congestion en {interseccion}")
                cmd = {
                    "interseccion": interseccion,
                    "estado": "VERDE",
                    "duracion_segundos": config["semaforos"]["tiempo_verde_congestion"],
                    "motivo": "congestion"
                }
                socket_push_ctrl.send_json(cmd)
                guardar_cambio_semaforo(conn, interseccion, "VERDE",
                                        cmd["duracion_segundos"], "congestion")

            elif estado == "PRIORIZACION":
                guardar_alerta(conn, interseccion, "PRIORIZACION",
                               f"vel={d['velocidad']} — posible emergencia")
                print(f"[ANALITICA] PRIORIZACION activada en {interseccion}")
                cmd = {
                    "interseccion": interseccion,
                    "estado": "VERDE",
                    "duracion_segundos": config["semaforos"]["tiempo_verde_priorizacion"],
                    "motivo": "priorizacion_automatica"
                }
                socket_push_ctrl.send_json(cmd)
                guardar_cambio_semaforo(conn, interseccion, "VERDE",
                                        cmd["duracion_segundos"],
                                        "priorizacion_automatica")

        except Exception as e:
            print(f"[ANALITICA] Error procesando evento: {e}")

def hilo_atender_consultas(config, conn, socket_push_ctrl):
    puerto_rep = config["red"]["puerto_analitica_rep"]

    context = zmq.Context()
    socket_rep = context.socket(zmq.REP)
    socket_rep.bind(f"tcp://*:{puerto_rep}")

    print(f"[ANALITICA] Esperando consultas en puerto {puerto_rep}")

    while True:
        try:
            req = socket_rep.recv_json()
            tipo = req.get("tipo", "")
            print(f"[ANALITICA] Consulta recibida: tipo={tipo}")

            if tipo == "consulta_historico":
                inicio = req.get("inicio", "")
                fin = req.get("fin", "")
                with lock_bd:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT sensor_id, interseccion, estado_trafico, timestamp
                        FROM eventos
                        WHERE timestamp >= ? AND timestamp <= ?
                        ORDER BY timestamp ASC
                    """, (inicio, fin))
                    filas = cursor.fetchall()
                resultado = [
                    {"sensor_id": f[0], "interseccion": f[1],
                     "estado": f[2], "timestamp": f[3]}
                    for f in filas
                ]
                socket_rep.send_json({"ok": True, "total": len(resultado),
                                      "eventos": resultado})

            elif tipo == "consulta_interseccion":
                interseccion = req.get("interseccion", "")
                with lock_bd:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT sensor_id, tipo_sensor, datos,
                        estado_trafico, timestamp
                        FROM eventos WHERE interseccion = ?
                        ORDER BY timestamp DESC LIMIT 10
                    """, (interseccion,))
                    filas = cursor.fetchall()
                resultado = [
                    {"sensor_id": f[0], "tipo": f[1],
                     "datos": json.loads(f[2]),
                     "estado": f[3], "timestamp": f[4]}
                    for f in filas
                ]
                socket_rep.send_json({"ok": True,
                                      "interseccion": interseccion,
                                      "eventos": resultado})

            elif tipo == "forzar_semaforo":
                interseccion = req.get("interseccion", "")
                estado = req.get("estado", "VERDE")
                duracion = req.get("duracion_segundos",
                    config["semaforos"]["tiempo_verde_priorizacion"])
                cmd = {
                    "interseccion": interseccion,
                    "estado": estado,
                    "duracion_segundos": duracion,
                    "motivo": "indicacion_directa_usuario"
                }
                socket_push_ctrl.send_json(cmd)
                guardar_cambio_semaforo(conn, interseccion, estado,
                                        duracion, "indicacion_directa_usuario")
                print(f"[ANALITICA] Semaforo forzado: "
                      f"{interseccion} → {estado} ({duracion}s)")
                socket_rep.send_json({"ok": True,
                    "mensaje": f"Semaforo {interseccion} → {estado}"})

            elif tipo == "forzar_priorizacion":
                via = req.get("via", "columna")
                identificador = req.get("identificador", "")
                duracion = req.get("duracion_segundos",
                    config["semaforos"]["tiempo_verde_priorizacion"])
                motivo = req.get("motivo", "priorizacion_manual")
                filas_ciudad = config["ciudad"]["filas"]
                cols_ciudad = config["ciudad"]["cols"]

                intersecciones_via = []
                if via == "columna":
                    for fila in filas_ciudad:
                        intersecciones_via.append(f"INT-{fila}{identificador}")
                elif via == "fila":
                    for col in range(1, cols_ciudad + 1):
                        intersecciones_via.append(f"INT-{identificador}{col}")

                for inter in intersecciones_via:
                    cmd = {
                        "interseccion": inter,
                        "estado": "VERDE",
                        "duracion_segundos": duracion,
                        "motivo": motivo
                    }
                    socket_push_ctrl.send_json(cmd)
                    guardar_cambio_semaforo(conn, inter, "VERDE",
                                            duracion, motivo)

                print(f"[ANALITICA] Priorizacion {via} {identificador} "
                      f"— {len(intersecciones_via)} semaforos en VERDE")
                socket_rep.send_json({
                    "ok": True,
                    "mensaje": f"Priorizacion activada en {via} {identificador}",
                    "semaforos": intersecciones_via
                })

            elif tipo == "restablecer_normal":
                print("[ANALITICA] Restableciendo estado normal global")
                socket_rep.send_json({"ok": True,
                    "mensaje": "Estado normal restablecido"})

            elif tipo == "heartbeat":
                socket_rep.send_json({"status": "ok"})

            else:
                socket_rep.send_json({"ok": False,
                    "mensaje": f"Tipo desconocido: {tipo}"})

        except Exception as e:
            print(f"[ANALITICA] Error atendiendo consulta: {e}")
            try:
                socket_rep.send_json({"ok": False, "error": str(e)})
            except:
                pass

def main():
    config = cargar_config()

    conn = inicializar_bd("bd_replica.db")
    print("[ANALITICA] BD replica inicializada en bd_replica.db")

    context = zmq.Context()
    socket_push_ctrl = context.socket(zmq.PUSH)
    socket_push_ctrl.bind(
        f"tcp://*:{config['red']['puerto_ctrl_semaforos']}")

    ip_pc3 = config["red"]["ip_pc3"]
    puerto_bd = config["red"]["puerto_bd_principal"]
    socket_push_bd_principal = context.socket(zmq.PUSH)
    socket_push_bd_principal.connect(f"tcp://{ip_pc3}:{puerto_bd}")

    print("[ANALITICA] Servicio de analitica iniciado")

    t1 = threading.Thread(
        target=hilo_procesar_eventos,
        args=(config, conn, socket_push_ctrl, socket_push_bd_principal),
        daemon=True
    )
    t2 = threading.Thread(
        target=hilo_atender_consultas,
        args=(config, conn, socket_push_ctrl),
        daemon=True
    )

    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[ANALITICA] Detenido por el usuario")
    finally:
        conn.close()
        context.term()

if __name__ == "__main__":
    main()
