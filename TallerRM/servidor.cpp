/*
 * servidor.cpp
 * 
 * Servidor gRPC del sistema de gestión de biblioteca.
 * Implementa los 4 servicios remotos definidos en biblioteca.proto:
 * PrestamoPorIsbn, PrestamoPorTitulo, Consulta y Devolucion.
 * 
 * La persistencia se maneja mediante el archivo libros.txt, que se
 * carga al iniciar el servidor y se actualiza tras cada operación
 * que modifique el inventario.
 * 
 * Formato de libros.txt: isbn,titulo,cantidad_total,cantidad_prestada
 * 
 * Autores: Juan Diego Ariza, Nicolas Leon
 * Curso: Introducción a Sistemas Distribuidos
 * Universidad: Pontificia Universidad Javeriana
 * Fecha: Febrero 2026
 */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <grpcpp/grpcpp.h>
#include "biblioteca.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;
using biblioteca::GestionBiblioteca;
using biblioteca::PeticionIsbn;
using biblioteca::PeticionTitulo;
using biblioteca::RespuestaPrestamo;
using biblioteca::RespuestaConsulta;
using biblioteca::RespuestaDevolucion;

/*
 * Estructura que representa un libro en el inventario.
 * cantidad_prestada indica cuántos ejemplares están actualmente fuera.
 * Los ejemplares disponibles se calculan como: cantidad_total - cantidad_prestada.
 */
struct Libro {
    std::string isbn;
    std::string titulo;
    int cantidad_total;
    int cantidad_prestada;
};

/*
 * BibliotecaServiceImpl
 * 
 * Clase principal del servidor. Hereda de GestionBiblioteca::Service
 * (generado por protoc) e implementa cada método remoto del contrato .proto.
 * 
 * El inventario se mantiene en memoria como un unordered_map indexado
 * por ISBN para búsquedas O(1). Cada operación que modifica el estado
 * persiste los cambios inmediatamente en libros.txt.
 */
class BibliotecaServiceImpl final : public GestionBiblioteca::Service {
private:
    std::unordered_map<std::string, Libro> inventario;

    /*
     * Carga el inventario desde libros.txt al iniciar el servidor.
     * Cada línea tiene el formato: isbn,titulo,total,prestados
     * Si el archivo no existe o está vacío, el inventario queda vacío.
     */
    void cargarBaseDeDatos() {
        std::ifstream archivo("libros.txt");
        std::string linea;
        
        while (std::getline(archivo, linea)) {
            std::stringstream ss(linea);
            std::string isbn, titulo, str_total, str_prestada;
            
            std::getline(ss, isbn, ',');
            std::getline(ss, titulo, ',');
            std::getline(ss, str_total, ',');
            std::getline(ss, str_prestada, ',');
            
            inventario[isbn] = {isbn, titulo, std::stoi(str_total), std::stoi(str_prestada)};
        }
        std::cout << "Base de datos cargada: " << inventario.size() << " libros." << std::endl;
    }

    /*
     * Persiste el estado actual del inventario en libros.txt.
     * Sobreescribe el archivo completo (ios::trunc) con los datos actuales.
     * Se llama después de cada préstamo o devolución exitosa.
     */
    void guardarBaseDeDatos() {
        std::ofstream archivo("libros.txt", std::ios::trunc);
        for (const auto& par : inventario) {
            const Libro& l = par.second;
            archivo << l.isbn << "," << l.titulo << "," << l.cantidad_total << "," << l.cantidad_prestada << "\n";
        }
    }

    /*
     * Calcula la fecha de devolución: fecha actual + 7 días.
     * Retorna la fecha formateada como dd/mm/aaaa.
     */
    std::string calcularFechaDevolucion() {
        auto hoy = std::chrono::system_clock::now();
        auto devolucion = hoy + std::chrono::hours(7 * 24);
        std::time_t tiempo_devolucion = std::chrono::system_clock::to_time_t(devolucion);
        
        char buffer[80];
        std::strftime(buffer, sizeof(buffer), "%d/%m/%Y", std::localtime(&tiempo_devolucion));
        return std::string(buffer);
    }

public:
    /*
     * Constructor: carga el inventario desde libros.txt al instanciar el servicio.
     */
    BibliotecaServiceImpl() {
        cargarBaseDeDatos();
    }

    /*
     * Consulta(isbn)
     * 
     * Busca un libro por ISBN en el inventario.
     * Retorna si el libro existe y cuántos ejemplares están disponibles.
     * No modifica el inventario.
     */
    Status Consulta(ServerContext* context, const PeticionIsbn* request, RespuestaConsulta* reply) override {
        std::string isbn_buscado = request->isbn();
        std::cout << "[CONSULTA] Buscando ISBN: " << isbn_buscado << std::endl;

        auto iterador = inventario.find(isbn_buscado);

        if (iterador != inventario.end()) {
            reply->set_existe(true);
            int disponibles = iterador->second.cantidad_total - iterador->second.cantidad_prestada;
            reply->set_disponibles(disponibles);
        } else {
            reply->set_existe(false);
            reply->set_disponibles(0);
        }
        return Status::OK;
    }

    /*
     * PrestamoPorIsbn(isbn)
     * 
     * Intenta prestar un libro buscándolo por ISBN.
     * Si existe y tiene ejemplares disponibles, incrementa cantidad_prestada,
     * persiste el cambio y retorna aprobado=true con la fecha de devolución.
     * Si no hay disponibles o el ISBN no existe, retorna aprobado=false.
     */
    Status PrestamoPorIsbn(ServerContext* context, const PeticionIsbn* request, RespuestaPrestamo* reply) override {
        std::string isbn = request->isbn();
        auto it = inventario.find(isbn);

        if (it != inventario.end() && (it->second.cantidad_total - it->second.cantidad_prestada) > 0) {
            it->second.cantidad_prestada++;
            guardarBaseDeDatos();
            
            reply->set_aprobado(true);
            reply->set_fecha_devolucion(calcularFechaDevolucion());
            std::cout << "[PRESTAMO] Aprobado por ISBN: " << isbn << std::endl;
        } else {
            reply->set_aprobado(false);
            reply->set_fecha_devolucion("");
            std::cout << "[PRESTAMO] Rechazado por ISBN: " << isbn << std::endl;
        }
        return Status::OK;
    }

    /*
     * PrestamoPorTitulo(titulo)
     * 
     * Intenta prestar un libro buscándolo por título exacto.
     * Recorre el inventario hasta encontrar coincidencia.
     * Si el libro existe y tiene disponibles, incrementa cantidad_prestada,
     * persiste el cambio y retorna aprobado=true con la fecha de devolución.
     * Si no se encuentra o no hay disponibles, retorna aprobado=false.
     */
    Status PrestamoPorTitulo(ServerContext* context, const PeticionTitulo* request, RespuestaPrestamo* reply) override {
        std::string titulo_buscado = request->titulo();
        
        for (auto& par : inventario) {
            if (par.second.titulo == titulo_buscado) {
                if ((par.second.cantidad_total - par.second.cantidad_prestada) > 0) {
                    par.second.cantidad_prestada++;
                    guardarBaseDeDatos();
                    
                    reply->set_aprobado(true);
                    reply->set_fecha_devolucion(calcularFechaDevolucion());
                    std::cout << "[PRESTAMO] Aprobado por Titulo: " << titulo_buscado << std::endl;
                    return Status::OK;
                }
            }
        }
        
        reply->set_aprobado(false);
        reply->set_fecha_devolucion("");
        std::cout << "[PRESTAMO] Rechazado por Titulo: " << titulo_buscado << std::endl;
        return Status::OK;
    }

    /*
     * Devolucion(isbn)
     * 
     * Registra la devolución de un libro buscándolo por ISBN.
     * Si el libro existe y tiene al menos un ejemplar prestado,
     * decrementa cantidad_prestada y persiste el cambio.
     * Retorna exito=false si el ISBN no existe o no había préstamos activos.
     */
    Status Devolucion(ServerContext* context, const PeticionIsbn* request, RespuestaDevolucion* reply) override {
        std::string isbn = request->isbn();
        auto it = inventario.find(isbn);

        if (it != inventario.end() && it->second.cantidad_prestada > 0) {
            it->second.cantidad_prestada--;
            guardarBaseDeDatos();
            reply->set_exito(true);
            std::cout << "[DEVOLUCION] Exitosa del ISBN: " << isbn << std::endl;
        } else {
            reply->set_exito(false);
            std::cout << "[DEVOLUCION] Fallida del ISBN: " << isbn << std::endl;
        }
        return Status::OK;
    }
};

/*
 * EjecutarServidor()
 * 
 * Configura e inicia el servidor gRPC en el puerto 50051.
 * Escucha en 0.0.0.0 para aceptar conexiones de cualquier interfaz de red,
 * lo que permite que clientes remotos se conecten usando la IP de esta máquina.
 * La función bloquea el hilo principal con server->Wait() hasta que el
 * servidor sea interrumpido manualmente.
 */
void EjecutarServidor() {
    std::string direccion_servidor("0.0.0.0:50051");
    BibliotecaServiceImpl servicio;

    ServerBuilder builder;
    builder.AddListeningPort(direccion_servidor, grpc::InsecureServerCredentials());
    builder.RegisterService(&servicio);
    
    std::unique_ptr<Server> server(builder.BuildAndStart());
    std::cout << "--- Servidor Biblioteca Iniciado ---" << std::endl;
    std::cout << "Escuchando en: " << direccion_servidor << std::endl;
    server->Wait();
}

int main(int argc, char** argv) {
    EjecutarServidor();
    return 0;
}
