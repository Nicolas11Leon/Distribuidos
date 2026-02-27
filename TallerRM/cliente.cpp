/*
 * cliente.cpp
 *
 * Cliente gRPC del sistema de gestión de biblioteca.
 * Se conecta al servidor remoto mediante un canal gRPC y expone
 * un menú interactivo para que el usuario invoque los 4 servicios remotos:
 * Consulta, PrestamoPorIsbn, PrestamoPorTitulo y Devolucion.
 *
 * Para conectarse a un servidor remoto, modificar la variable target_str
 * en main() con la IP y puerto del servidor (ej: "192.168.1.5:50051").
 *
 * Autores: Juan Diego Ariza, Nicolas Leon
 * Curso: Introducción a Sistemas Distribuidos
 * Universidad: Pontificia Universidad Javeriana
 * Fecha: Febrero 2026
 */

#include <iostream>
#include <string>
#include <memory>
#include <grpcpp/grpcpp.h>
#include "biblioteca.grpc.pb.h"

using grpc::Channel;
using grpc::ClientContext;
using grpc::Status;
using biblioteca::GestionBiblioteca;
using biblioteca::PeticionIsbn;
using biblioteca::PeticionTitulo;
using biblioteca::RespuestaPrestamo;
using biblioteca::RespuestaConsulta;
using biblioteca::RespuestaDevolucion;

/*
 * ClienteBiblioteca
 *
 * Encapsula la comunicación con el servidor remoto.
 * Internamente usa un stub, que es el proxy local generado por gRPC
 * que traduce cada llamada a método en un mensaje de red hacia el servidor.
 * Desde el punto de vista del cliente, llamar a stub_->Consulta() es
 * equivalente a llamar al método directamente en el servidor.
 */
class ClienteBiblioteca {
private:
    /* Proxy generado por gRPC que representa al servidor de forma local */
    std::unique_ptr<GestionBiblioteca::Stub> stub_;

public:
    /*
     * Constructor: recibe el canal de comunicación (IP:puerto) y crea el stub.
     * El canal define la conexión física; el stub define la interfaz lógica.
     */
    ClienteBiblioteca(std::shared_ptr<Channel> channel)
        : stub_(GestionBiblioteca::NewStub(channel)) {}

    /*
     * ConsultarLibro(isbn)
     *
     * Invoca el servicio remoto Consulta con el ISBN proporcionado.
     * Imprime si el libro existe y cuántos ejemplares están disponibles.
     * No modifica el estado del servidor.
     */
    void ConsultarLibro(const std::string& isbn) {
        PeticionIsbn request;
        request.set_isbn(isbn);
        RespuestaConsulta reply;
        ClientContext context;

        Status status = stub_->Consulta(&context, request, &reply);

        if (status.ok()) {
            if (reply.existe()) {
                std::cout << "-> [EXITO] El libro existe. Ejemplares disponibles: " << reply.disponibles() << std::endl;
            } else {
                std::cout << "-> [ERROR] El libro con ISBN " << isbn << " no se encuentra en la biblioteca." << std::endl;
            }
        } else {
            std::cout << "-> [FALLO DE RED] No se pudo contactar al servidor." << std::endl;
        }
    }

    /*
     * PrestarPorIsbn(isbn)
     *
     * Invoca el servicio remoto PrestamoPorIsbn con el ISBN proporcionado.
     * Si el préstamo es aprobado, muestra la fecha límite de devolución.
     * Si no hay ejemplares disponibles o el ISBN no existe, indica el rechazo.
     */
    void PrestarPorIsbn(const std::string& isbn) {
        PeticionIsbn request;
        request.set_isbn(isbn);
        RespuestaPrestamo reply;
        ClientContext context;

        Status status = stub_->PrestamoPorIsbn(&context, request, &reply);

        if (status.ok()) {
            if (reply.aprobado()) {
                std::cout << "-> [APROBADO] Prestamo exitoso. Fecha limite de devolucion: " << reply.fecha_devolucion() << std::endl;
            } else {
                std::cout << "-> [RECHAZADO] No hay ejemplares disponibles o el ISBN no existe." << std::endl;
            }
        } else {
            std::cout << "-> [FALLO DE RED] No se pudo contactar al servidor." << std::endl;
        }
    }

    /*
     * PrestarPorTitulo(titulo)
     *
     * Invoca el servicio remoto PrestamoPorTitulo con el título exacto del libro.
     * Si el préstamo es aprobado, muestra la fecha límite de devolución.
     * El título debe coincidir exactamente con el almacenado en el servidor.
     */
    void PrestarPorTitulo(const std::string& titulo) {
        PeticionTitulo request;
        request.set_titulo(titulo);
        RespuestaPrestamo reply;
        ClientContext context;

        Status status = stub_->PrestamoPorTitulo(&context, request, &reply);

        if (status.ok()) {
            if (reply.aprobado()) {
                std::cout << "-> [APROBADO] Prestamo exitoso. Fecha limite de devolucion: " << reply.fecha_devolucion() << std::endl;
            } else {
                std::cout << "-> [RECHAZADO] No hay ejemplares disponibles o el titulo no existe." << std::endl;
            }
        } else {
            std::cout << "-> [FALLO DE RED] No se pudo contactar al servidor." << std::endl;
        }
    }

    /*
     * DevolverLibro(isbn)
     *
     * Invoca el servicio remoto Devolucion con el ISBN del libro a devolver.
     * El servidor valida que el ISBN exista y tenga préstamos activos antes
     * de registrar la devolución y actualizar el inventario.
     */
    void DevolverLibro(const std::string& isbn) {
        PeticionIsbn request;
        request.set_isbn(isbn);
        RespuestaDevolucion reply;
        ClientContext context;

        Status status = stub_->Devolucion(&context, request, &reply);

        if (status.ok()) {
            if (reply.exito()) {
                std::cout << "-> [EXITO] Devolucion registrada correctamente." << std::endl;
            } else {
                std::cout << "-> [ERROR] No se pudo realizar la devolucion (ISBN incorrecto o no estaba prestado)." << std::endl;
            }
        } else {
            std::cout << "-> [FALLO DE RED] No se pudo contactar al servidor." << std::endl;
        }
    }
};

/*
 * main()
 *
 * Punto de entrada del cliente. Establece la conexión con el servidor
 * y presenta un menú interactivo en bucle hasta que el usuario seleccione salir.
 *
 * Para conectarse a un servidor remoto, cambiar target_str por la IP real:
 *   std::string target_str = "192.168.X.X:50051";
 */
int main(int argc, char** argv) {
    std::string target_str = "localhost:50051";
    
    ClienteBiblioteca cliente(grpc::CreateChannel(target_str, grpc::InsecureChannelCredentials()));
    
    int opcion = 0;
    std::string entrada;

    while (opcion != 5) {
        std::cout << "\n=== MENU DEL SOLICITANTE PS ===" << std::endl;
        std::cout << "1. Consultar disponibilidad (por ISBN)" << std::endl;
        std::cout << "2. Solicitar prestamo (por ISBN)" << std::endl;
        std::cout << "3. Solicitar prestamo (por Titulo)" << std::endl;
        std::cout << "4. Devolver libro (por ISBN)" << std::endl;
        std::cout << "5. Salir" << std::endl;
        std::cout << "Seleccione una opcion: ";
        std::cin >> opcion;
        std::cin.ignore();

        switch (opcion) {
            case 1:
                std::cout << "Ingrese el ISBN a consultar: ";
                std::getline(std::cin, entrada);
                cliente.ConsultarLibro(entrada);
                break;
            case 2:
                std::cout << "Ingrese el ISBN para el prestamo: ";
                std::getline(std::cin, entrada);
                cliente.PrestarPorIsbn(entrada);
                break;
            case 3:
                std::cout << "Ingrese el Titulo para el prestamo: ";
                std::getline(std::cin, entrada);
                cliente.PrestarPorTitulo(entrada);
                break;
            case 4:
                std::cout << "Ingrese el ISBN a devolver: ";
                std::getline(std::cin, entrada);
                cliente.DevolverLibro(entrada);
                break;
            case 5:
                std::cout << "Saliendo del sistema..." << std::endl;
                break;
            default:
                std::cout << "Opcion invalida." << std::endl;
        }
    }

    return 0;
}
