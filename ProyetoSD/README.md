# Gestión Inteligente de Tráfico Urbano
**Introducción a los Sistemas Distribuidos — 2026-30**
Pontificia Universidad Javeriana · Departamento de Ingeniería de Sistemas

**Integrantes:**
- Juan Diego Ariza
- Nicolas Leon
- Juan Diego Pardo
- Juan Sebastian Urbano

**Profesor:** John Corredor, Ph.D.

---

## Descripción

Sistema distribuido que simula la gestión inteligente del tráfico urbano en una ciudad
representada como una matriz de 5×6 intersecciones (30 intersecciones, 90 sensores,
30 semáforos). Los componentes se comunican mediante ZeroMQ y se distribuyen en
tres máquinas físicas del laboratorio.

---

## Arquitectura

| Máquina | Hostname | IP | Componentes |
|---------|----------|----|-------------|
| PC1 | MIG220 | 10.43.99.161 | Sensores (espira, cámara, GPS), Broker ZeroMQ, Semáforos |
| PC2 | MIG322 | 10.43.100.24 | Servicio de Analítica, Control de Semáforos, BD Réplica, Health Check |
| PC3 | MIG29  | 10.43.98.223 | BD Principal, Monitoreo y Consulta |

### Patrones de comunicación

| Patrón | Uso |
|--------|-----|
| PUB/SUB | Sensores → Broker → Analítica |
| PUSH/PULL | Analítica → Control Semáforos · Analítica → BD Principal · Analítica → BD Réplica |
| REQ/REP | Monitoreo → Analítica · Health Check PC2 → PC3 |

---

## Requisitos

Python 3.8 o superior. Instalar dependencias en los tres PCs:

```bash
pip install -r requirements.txt
```

---

## Ejecución

Los servicios deben iniciarse en este orden: primero PC3, luego PC2, luego PC1.
Esperar a que cada PC imprima sus mensajes de inicio antes de pasar al siguiente.

### PC3 — MIG29 (10.43.98.223)

Abrir dos terminales:

```bash
# Terminal 1 — Base de datos principal
python pc3/bd_principal.py

# Terminal 2 — Monitoreo y consulta
python pc3/monitoreo_consulta.py
```

### PC2 — MIG322 (10.43.100.24)

Abrir tres terminales:

```bash
# Terminal 1 — Servicio de analítica
python pc2/servicio_analitica.py

# Terminal 2 — Control de semáforos
python pc2/control_semaforos.py

# Terminal 3 — Health Check (detecta caída de PC3)
python pc2/health_check.py
```

### PC1 — MIG220 (10.43.99.161)

Abrir seis terminales (una por tipo de proceso):

```bash
# Broker ZeroMQ — iniciar primero
python pc1/broker_zmq.py

# Sensores (uno por tipo es suficiente para prueba básica)
python pc1/sensor_espira.py
python pc1/sensor_camara.py
python pc1/sensor_gps.py

# Semáforos
python pc1/semaforo.py
```

---

## Configuración

Todos los parámetros del sistema están centralizados en `config/config.py`:

```python
PC1_IP = "10.43.99.161"
PC2_IP = "10.43.100.24"
PC3_IP = "10.43.98.223"

PUERTO_BROKER_SUB   = 5555   # Sensores → Broker
PUERTO_BROKER_PUB   = 5556   # Broker → Analítica
PUERTO_ANALITICA    = 5557   # Indicaciones directas desde Monitoreo
PUERTO_BD_PRINCIPAL = 5558   # Analítica → BD Principal (PC3)
PUERTO_BD_REPLICA   = 5559   # Analítica → BD Réplica (PC2)
PUERTO_SEMAFOROS    = 5560   # Control → Semáforos
PUERTO_HEARTBEAT    = 5561   # Health Check PC2 → PC3
PUERTO_MONITOREO    = 5562   # Consultas usuario → Analítica
```

Para cambiar IPs o puertos, editar únicamente ese archivo.

---

## Estados de tráfico y reglas

| Estado | Condición | Semáforo |
|--------|-----------|----------|
| Normal | Q < 5 veh · Vp > 35 km/h · V < 8 veh/min | Verde 15s / Rojo 15s |
| Congestión | Q ≥ 10 veh · Vp < 15 km/h · V ≥ 15 veh/min | Verde 30s / Rojo 10s |
| Priorización | Vp < 5 km/h (GPS) o comando manual | Verde 45s en vía priorizada |

---

## Tolerancia a fallas

El sistema maneja la caída del PC3 de forma automática:

1. **Detección:** Health Check en PC2 envía heartbeat cada 5s. Sin respuesta en 15s → falla declarada.
2. **Enmascaramiento:** Analítica redirige escrituras a BD Réplica en PC2.
3. **Continuidad:** El sistema sigue procesando eventos y controlando semáforos.
4. **Recuperación:** Al volver PC3, se realiza sincronización delta con los eventos pendientes.

```

---

## Ciudad simulada

```
     1       2       3       4       5       6
A  INT_A1  INT_A2  INT_A3  INT_A4  INT_A5  INT_A6
B  INT_B1  INT_B2  INT_B3  INT_B4  INT_B5  INT_B6
C  INT_C1  INT_C2  INT_C3  INT_C4  INT_C5  INT_C6
D  INT_D1  INT_D2  INT_D3  INT_D4  INT_D5  INT_D6
E  INT_E1  INT_E2  INT_E3  INT_E4  INT_E5  INT_E6
```

Cada intersección tiene: 1 sensor espira (ESP-X#), 1 cámara (CAM-X#), 1 sensor GPS (GPS-X#) y 1 semáforo (SEM-X#).

---

*Primera Entrega — Semana 10 · Abril 2026*
