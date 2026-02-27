# CMakeLists.txt
#
# Configuración de compilación del sistema de gestión de biblioteca.
# Genera dos ejecutables independientes: servidor y cliente.
# Ambos se enlazan contra las librerías gRPC y Protobuf del sistema.
#
# Autores: Juan Diego Ariza, Nicolas Leon
# Curso: Introducción a Sistemas Distribuidos
# Universidad: Pontificia Universidad Javeriana
# Fecha: Febrero 2026

# Versión mínima de CMake requerida para las directivas usadas
cmake_minimum_required(VERSION 3.15)

# Nombre del proyecto y lenguaje principal
project(TallerBiblioteca CXX)

# Estándar C++17 requerido para características modernas del lenguaje
set(CMAKE_CXX_STANDARD 17)

# Buscar la librería Protobuf instalada en el sistema
# Necesaria para deserializar/serializar los mensajes definidos en el .proto
find_package(Protobuf REQUIRED)

# Archivos generados automáticamente por protoc a partir de biblioteca.proto
# Contienen la lógica de serialización (pb) y los stubs gRPC (grpc.pb)
set(ARCHIVOS_AUTOGENERADOS
    biblioteca.pb.cc
    biblioteca.grpc.pb.cc
)

# --- Ejecutable 1: Servidor ---
# Compila servidor.cpp junto con los archivos autogenerados
# y enlaza con grpc++, grpc y protobuf
add_executable(servidor servidor.cpp ${ARCHIVOS_AUTOGENERADOS})
target_link_libraries(servidor grpc++ grpc protobuf::libprotobuf)

# --- Ejecutable 2: Cliente ---
# Compila cliente.cpp junto con los archivos autogenerados
# y enlaza con las mismas librerías que el servidor
add_executable(cliente cliente.cpp ${ARCHIVOS_AUTOGENERADOS})
target_link_libraries(cliente grpc++ grpc protobuf::libprotobuf)
