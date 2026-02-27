# Taller RMI/gRPC — Sistema de Gestión de Biblioteca

**Curso:** Introducción a Sistemas Distribuidos  
**Universidad:** Pontificia Universidad Javeriana  
**Fecha:** Febrero 2026  
**Autores:** Juan Diego Ariza, Nicolas Leon

---

## Descripción

Sistema cliente-servidor implementado con **gRPC en C++** que simula la gestión de préstamos de una biblioteca. Un servidor central expone 4 servicios remotos que los clientes pueden invocar desde otras máquinas a través de la red.

### Servicios disponibles

| Servicio | Entrada | Descripción |
|---|---|---|
| `PrestamoPorIsbn` | ISBN | Presta un libro buscándolo por ISBN |
| `PrestamoPorTitulo` | Título | Presta un libro buscándolo por título |
| `Consulta` | ISBN | Consulta disponibilidad de un libro |
| `Devolucion` | ISBN | Registra la devolución de un libro |

---

## Requisitos

- Ubuntu 22.04 o superior
- CMake 3.15+
- Compilador g++ con soporte C++17
- Librerías gRPC y Protobuf

### Instalar dependencias

```bash
sudo apt update
sudo apt install -y cmake build-essential libgrpc++-dev libprotobuf-dev protobuf-compiler-grpc
```

---

## Compilación

```bash
# Clonar o descomprimir el proyecto
cd Taller_RMI_gRPC

# Crear carpeta de compilación limpia
mkdir build && cd build

# Configurar y compilar
cmake ..
make
```

Esto genera dos ejecutables dentro de `build/`:
- `servidor` — el proceso del servidor
- `cliente` — el proceso del cliente

---

## Ejecución

### Computadora 1 — Servidor

El servidor debe ejecutarse desde la carpeta raíz del proyecto (donde está `libros.txt`):

```bash
cd Taller_RMI_gRPC
./build/servidor
```

Salida esperada:
```
Base de datos cargada: 4 libros.
--- Servidor Biblioteca Iniciado ---
Escuchando en: 0.0.0.0:50051
```

Obtener la IP del servidor (para dársela al cliente):
```bash
ip a
# Buscar la línea "inet" de la interfaz de red (ej: 10.43.98.100)
```

### Computadora 2 — Cliente

Antes de compilar, editar `cliente.cpp` y cambiar la IP del servidor:

```cpp
// Línea a modificar en cliente.cpp:
std::string target_str = "IP_DEL_SERVIDOR:50051";
// Ejemplo: "10.43.98.100:50051"
```

Luego compilar y ejecutar:

```bash
cd Taller_RMI_gRPC
mkdir build && cd build
cmake .. && make
./cliente
```

---

## Base de datos (libros.txt)

El inventario se almacena en `libros.txt` junto al ejecutable del servidor.  
Formato de cada línea: `isbn,titulo,total_ejemplares,ejemplares_prestados`

```
9786071511471,Sistemas Operativos,5,0
9788448197503,Estructuras de Datos,3,1
9786073236973,Sistemas Distribuidos,4,0
1111111111111,El Hobbit,2,2
```

El servidor actualiza este archivo automáticamente tras cada préstamo o devolución.

---

## Ejemplo de uso

```
=== MENU DEL SOLICITANTE PS ===
1. Consultar disponibilidad (por ISBN)
2. Solicitar prestamo (por ISBN)
3. Solicitar prestamo (por Titulo)
4. Devolver libro (por ISBN)
5. Salir
Seleccione una opcion: 1
Ingrese el ISBN a consultar: 9786071511471
-> [EXITO] El libro existe. Ejemplares disponibles: 5

Seleccione una opcion: 2
Ingrese el ISBN para el prestamo: 9786071511471
-> [APROBADO] Prestamo exitoso. Fecha limite de devolucion: 05/03/2026
```

---

## Estructura del proyecto

```
Taller_RMI_gRPC/
├── servidor.cpp            # Implementación del servidor gRPC
├── cliente.cpp             # Cliente con menú interactivo
├── biblioteca.proto        # Contrato del servicio (interfaz remota)
├── biblioteca.pb.cc        # Código generado por protoc (serialización)
├── biblioteca.pb.h
├── biblioteca.grpc.pb.cc   # Código generado por protoc (servicios gRPC)
├── biblioteca.grpc.pb.h
├── libros.txt              # Base de datos del inventario
├── CMakeLists.txt          # Configuración de compilación
└── README.md
```

---

## Arquitectura

```
  Cliente (PC 2)                    Servidor (PC 1)
  ┌─────────────┐    red/gRPC       ┌──────────────────┐
  │  cliente.cpp│ ──────────────►   │   servidor.cpp   │
  │             │ ◄──────────────   │                  │
  └─────────────┘                   │   libros.txt     │
                                    └──────────────────┘
```

Todas las operaciones son **síncronas**: el cliente espera la respuesta del servidor antes de continuar.
