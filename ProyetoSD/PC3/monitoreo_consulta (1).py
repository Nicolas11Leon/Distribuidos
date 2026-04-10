# monitoreo_consulta.py
# Servicio de monitoreo y consulta — interfaz de usuario para consultas
# e indicaciones directas al sistema de semaforos
# Autores: Juan Diego Ariza, Nicolas Leon, Juan Diego Pardo, Juan Sebastian Urbano
# Sistemas Distribuidos — Pontificia Universidad Javeriana 2026

import zmq
import json
import time
from datetime import datetime, timezone

def cargar_config(ruta="config.json"):
    with open(ruta, "r") as f:
        return json.load(f)

def crear_socket_req(context, ip_pc2, puerto):
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)
    socket.setsockopt(zmq.LINGER, 0)
    socket.connect(f"tcp://{ip_pc2}:{puerto}")
    return socket

def enviar_consulta(socket, req):
    try:
        socket.send_json(req)
        respuesta = socket.recv_json()
        return respuesta
    except zmq.error.Again:
        print("[MONITOR] Timeout — analitica no responde")
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        print(f"[MONITOR] Error: {e}")
        return {"ok": False, "error": str(e)}

def menu():
    print("\n" + "="*50)
    print("  SISTEMA DE MONITOREO DE TRAFICO URBANO")
    print("="*50)
    print("  1. Consulta historica por rango de tiempo")
    print("  2. Consulta puntual por interseccion")
    print("  3. Forzar semaforo individual")
    print("  4. Priorizar via completa (ola verde)")
    print("  5. Restablecer estado normal global")
    print("  6. Salir")
    print("="*50)
    return input("  Seleccione una opcion: ").strip()

def main():
    config = cargar_config()
    ip_pc2 = config["red"]["ip_pc2"]
    puerto_rep = config["red"]["puerto_analitica_rep"]

    context = zmq.Context()

    print("[MONITOR] Servicio de monitoreo y consulta iniciado")
    print(f"[MONITOR] Conectando a analitica en "
          f"tcp://{ip_pc2}:{puerto_rep}")

    try:
        while True:
            opcion = menu()

            # crear socket nuevo por cada consulta para evitar
            # estados invalidos en REQ/REP
            socket = crear_socket_req(context, ip_pc2, puerto_rep)

            if opcion == "1":
                inicio = input("  Fecha inicio (YYYY-MM-DDTHH:MM:SSZ): ").strip()
                fin = input("  Fecha fin    (YYYY-MM-DDTHH:MM:SSZ): ").strip()
                req = {
                    "tipo": "consulta_historico",
                    "inicio": inicio,
                    "fin": fin
                }
                print(f"\n[MONITOR] Consultando historico {inicio} → {fin}")
                respuesta = enviar_consulta(socket, req)
                if respuesta.get("ok"):
                    print(f"[MONITOR] Total eventos: {respuesta.get('total')}")
                    for ev in respuesta.get("eventos", [])[:10]:
                        print(f"  {ev['timestamp']} | {ev['interseccion']} "
                              f"| {ev['estado']} | {ev['sensor_id']}")
                    if respuesta.get("total", 0) > 10:
                        print(f"  ... y {respuesta['total']-10} eventos mas")
                else:
                    print(f"[MONITOR] Error: {respuesta.get('error')}")

            elif opcion == "2":
                interseccion = input(
                    "  Interseccion (ej. INT-C5): ").strip()
                req = {
                    "tipo": "consulta_interseccion",
                    "interseccion": interseccion
                }
                print(f"\n[MONITOR] Consultando {interseccion}")
                respuesta = enviar_consulta(socket, req)
                if respuesta.get("ok"):
                    eventos = respuesta.get("eventos", [])
                    print(f"[MONITOR] Ultimos {len(eventos)} eventos "
                          f"en {interseccion}:")
                    for ev in eventos:
                        print(f"  {ev['timestamp']} | {ev['tipo']} "
                              f"| estado={ev['estado']}")
                else:
                    print(f"[MONITOR] Error: {respuesta.get('error')}")

            elif opcion == "3":
                interseccion = input(
                    "  Interseccion (ej. INT-C3): ").strip()
                estado = input(
                    "  Estado (VERDE/ROJO): ").strip().upper()
                duracion = int(input(
                    "  Duracion en segundos: ").strip())
                req = {
                    "tipo": "forzar_semaforo",
                    "interseccion": interseccion,
                    "estado": estado,
                    "duracion_segundos": duracion
                }
                t1 = time.time()
                print(f"\n[MONITOR] Forzando {interseccion} → {estado} "
                      f"t1={t1:.6f}")
                respuesta = enviar_consulta(socket, req)
                if respuesta.get("ok"):
                    print(f"[MONITOR] {respuesta.get('mensaje')}")
                else:
                    print(f"[MONITOR] Error: {respuesta.get('error')}")

            elif opcion == "4":
                via = input(
                    "  Via a priorizar (fila/columna): ").strip().lower()
                identificador = input(
                    "  Identificador (ej. C para fila, 3 para columna): "
                ).strip()
                duracion = int(input(
                    "  Duracion en segundos [45]: ").strip() or "45")
                motivo = input(
                    "  Motivo [paso_ambulancia]: ").strip() or \
                    "paso_ambulancia"
                req = {
                    "tipo": "forzar_priorizacion",
                    "via": via,
                    "identificador": identificador,
                    "estado": "VERDE",
                    "duracion_segundos": duracion,
                    "motivo": motivo
                }
                print(f"\n[MONITOR] Priorizando {via} {identificador}")
                respuesta = enviar_consulta(socket, req)
                if respuesta.get("ok"):
                    print(f"[MONITOR] {respuesta.get('mensaje')}")
                    for sem in respuesta.get("semaforos", []):
                        print(f"  → {sem} en VERDE")
                else:
                    print(f"[MONITOR] Error: {respuesta.get('error')}")

            elif opcion == "5":
                req = {
                    "tipo": "restablecer_normal",
                    "alcance": "global"
                }
                print("\n[MONITOR] Restableciendo estado normal global")
                respuesta = enviar_consulta(socket, req)
                if respuesta.get("ok"):
                    print(f"[MONITOR] {respuesta.get('mensaje')}")
                else:
                    print(f"[MONITOR] Error: {respuesta.get('error')}")

            elif opcion == "6":
                print("[MONITOR] Cerrando servicio de monitoreo")
                break

            else:
                print("[MONITOR] Opcion invalida")

            socket.close()

    except KeyboardInterrupt:
        print("\n[MONITOR] Detenido por el usuario")
    finally:
        context.term()

if __name__ == "__main__":
    main()
