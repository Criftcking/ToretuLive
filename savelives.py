import psycopg2
import psycopg2.extras
# Configuración de conexión PostgreSQL (igual que en SQL SEARCHER LIVE.py)
BASE_URL = "postgresql://postgres:HHksJErrGGMthwnZbmGxpckTusSlfrmK@crossover.proxy.rlwy.net:26803/railway"
def get_conn():
    return psycopg2.connect(BASE_URL, cursor_factory=psycopg2.extras.DictCursor)

# Crear tabla si no existe
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bloques_guardados (
            id SERIAL PRIMARY KEY,
            bloque TEXT UNIQUE,
            archivo TEXT,
            fecha TIMESTAMP DEFAULT NOW()
        )
    ''')
    conn.commit()
    conn.close()
from telethon import TelegramClient, events
import asyncio
import os

api_id = 26682067
api_hash = '68fa0932dbe4f52c38a53e36c617338d'
# Usar un archivo de sesión único para este bot
SESSION_FILE = 'savelives.session'
client = TelegramClient(SESSION_FILE, api_id, api_hash)

SEPARADOR = "━━━━━━━━━━━━━━━━━━━━━━━━"

def extraer_bloques(texto):
    lineas = texto.splitlines()
    bloques = []
    bloque_actual = []

    for linea in lineas:
        if linea.strip() == SEPARADOR:
            if bloque_actual:
                bloques.append("\n".join(bloque_actual + [SEPARADOR]))
                bloque_actual = []
            bloque_actual.append(SEPARADOR)
        else:
            bloque_actual.append(linea.strip())

    if bloque_actual and bloque_actual != [SEPARADOR]:
        bloques.append("\n".join(bloque_actual))

    return bloques

def limpiar_bloques_duplicados(archivo):
    # Limpiar duplicados en TXT
    if not os.path.exists(archivo):
        bloques_txt = []
    else:
        with open(archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
        bloques_txt = extraer_bloques(contenido)
    bloques_sin_duplicados = list(dict.fromkeys([b.strip() for b in bloques_txt if b.strip()]))
    with open(archivo, 'w', encoding='utf-8') as f:
        for bloque in bloques_sin_duplicados:
            f.write(bloque + '\n')
    eliminados = len(bloques_txt) - len(bloques_sin_duplicados)
    print(f"🧹 Limpieza TXT: {eliminados} bloques duplicados eliminados.")

    # Limpiar duplicados en la base de datos
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT bloque, MIN(id) FROM bloques_guardados WHERE archivo = %s GROUP BY bloque", (archivo,))
    keep_ids = set(row[1] for row in c.fetchall())
    c.execute("SELECT id FROM bloques_guardados WHERE archivo = %s", (archivo,))
    all_ids = set(row[0] for row in c.fetchall())
    to_delete = all_ids - keep_ids
    if to_delete:
        c.execute(f"DELETE FROM bloques_guardados WHERE id IN ({','.join(['%s']*len(to_delete))})", tuple(to_delete))
        print(f"🧹 Limpieza DB: {len(to_delete)} duplicados eliminados.")
    conn.commit()
    conn.close()

    # Retornar el set de bloques únicos (de la base de datos)
    return set(bloques_sin_duplicados)

def agregar_bloque_si_es_nuevo(archivo, bloque, bloques_guardados):
    bloque = bloque.strip()
    if bloque and bloque not in bloques_guardados:
        # Guardar en TXT
        with open(archivo, 'a', encoding='utf-8') as f:
            f.write(bloque + '\n')
        # Guardar en base de datos
        conn = get_conn()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO bloques_guardados (bloque, archivo) VALUES (%s, %s) ON CONFLICT DO NOTHING", (bloque, archivo))
            conn.commit()
        except Exception as e:
            print(f"Error al guardar en DB: {e}")
        conn.close()
        bloques_guardados.add(bloque)
        return True
    return False

async def main():
    init_db()
    await client.start()
    print("✅ Conectado a Telegram")


    dialogs = await client.get_dialogs()
    # Buscar automáticamente el grupo/canal llamado 'Team Wolf Lives'
    target = None
    target_name = None
    for dialog in dialogs:
        if (dialog.is_group or dialog.is_channel) and dialog.name.strip().lower() == 'team wolf lives':
            target = dialog.entity
            target_name = dialog.name.replace(" ", "_")
            break
    if not target:
        print("❌ No se encontró el grupo/canal 'Team Wolf Lives'.")
        return
    archivo = f"{target_name}_mensajes.txt"

    # Variable mutable compartida
    bloques_guardados = limpiar_bloques_duplicados(archivo)

    print("\n📥 Descargando mensajes antiguos...")
    nuevos = 0
    async for message in client.iter_messages(target, reverse=True):
        if message.text and SEPARADOR in message.text:
            bloque = message.text.strip()
            if agregar_bloque_si_es_nuevo(archivo, bloque, bloques_guardados):
                nuevos += 1

    print(f"✅ {nuevos} bloques antiguos nuevos guardados.")
    bloques_guardados = limpiar_bloques_duplicados(archivo)

    # ✅ Handler accediendo correctamente a la variable
    @client.on(events.NewMessage(chats=target))
    async def handler(event):
        nonlocal bloques_guardados  # ← NECESARIO para modificar la variable de main()

        if event.text and SEPARADOR in event.text:
            bloque = event.text.strip()
            if agregar_bloque_si_es_nuevo(archivo, bloque, bloques_guardados):
                print(f"[{event.chat.title}] ✅ Nuevo bloque guardado.")
                bloques_guardados = limpiar_bloques_duplicados(archivo)

    print(f"\n⏳ Escuchando mensajes nuevos en: {target_name}")
    await asyncio.Future()

with client:
    client.loop.run_until_complete(main())
