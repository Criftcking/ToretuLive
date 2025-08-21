from telethon import TelegramClient, events
import asyncio
import os

api_id = 26682067
api_hash = '68fa0932dbe4f52c38a53e36c617338d'
client = TelegramClient('session', api_id, api_hash)

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
    if not os.path.exists(archivo):
        return set()

    with open(archivo, 'r', encoding='utf-8') as f:
        contenido = f.read()

    bloques = extraer_bloques(contenido)
    bloques_sin_duplicados = list(dict.fromkeys([b.strip() for b in bloques if b.strip()]))

    with open(archivo, 'w', encoding='utf-8') as f:
        for bloque in bloques_sin_duplicados:
            f.write(bloque + '\n')

    eliminados = len(bloques) - len(bloques_sin_duplicados)
    print(f"🧹 Limpieza: {eliminados} bloques duplicados eliminados.")
    return set(bloques_sin_duplicados)

def agregar_bloque_si_es_nuevo(archivo, bloque, bloques_guardados):
    bloque = bloque.strip()
    if bloque and bloque not in bloques_guardados:
        with open(archivo, 'a', encoding='utf-8') as f:
            f.write(bloque + '\n')
        bloques_guardados.add(bloque)
        return True
    return False

async def main():
    await client.start()
    print("✅ Conectado a Telegram")

    dialogs = await client.get_dialogs()

    # Buscar automáticamente el chat "Team Wolf Lives"
    target_dialog = next((d for d in dialogs if d.name == "Team Wolf Lives"), None)
    if not target_dialog:
        print("❌ No se encontró el chat 'Team Wolf Lives'.")
        return

    target = target_dialog.entity
    target_name = target_dialog.name.replace(" ", "_")
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

    # Handler para nuevos mensajes
    @client.on(events.NewMessage(chats=target))
    async def handler(event):
        nonlocal bloques_guardados

        if event.text and SEPARADOR in event.text:
            bloque = event.text.strip()
            if agregar_bloque_si_es_nuevo(archivo, bloque, bloques_guardados):
                print(f"[{event.chat.title}] ✅ Nuevo bloque guardado.")
                bloques_guardados = limpiar_bloques_duplicados(archivo)

    print(f"\n⏳ Escuchando mensajes nuevos en: {target_dialog.name}")
    await asyncio.Future()


with client:
    client.loop.run_until_complete(main())
