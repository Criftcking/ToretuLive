from telethon import TelegramClient, events
import asyncio
import os

api_id = 26682067
api_hash = '68fa0932dbe4f52c38a53e36c617338d'

client = TelegramClient('session', api_id, api_hash)

def cargar_mensajes_guardados(archivo):
    if not os.path.exists(archivo):
        return set()
    with open(archivo, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

async def main():
    await client.start()
    print("Conectado a Telegram\n")

    # Mostrar lista de grupos/canales
    dialogs = await client.get_dialogs()
    print("Chats disponibles:\n")
    for i, dialog in enumerate(dialogs):
        if dialog.is_group or dialog.is_channel:
            print(f"{i}: {dialog.name}")

    index = int(input("\nSelecciona el número del grupo/canal: "))
    target = dialogs[index].entity
    target_name = dialogs[index].name.replace(" ", "_")
    archivo = f"{target_name}_mensajes.txt"

    # Cargar mensajes guardados para evitar duplicados
    mensajes_guardados = cargar_mensajes_guardados(archivo)

    # Escuchar nuevos mensajes
    @client.on(events.NewMessage(chats=target))
    async def handler(event):
        if event.text:
            texto = event.text.strip()
            if texto and texto not in mensajes_guardados:
                with open(archivo, "a", encoding="utf-8") as f:
                    f.write(f"{texto}\n")
                mensajes_guardados.add(texto)
                print(f"[{event.chat.title}] {event.sender_id}: {texto}")

    print(f"\nEscuchando nuevos mensajes en: {dialogs[index].name}")
    await asyncio.Future()  # Mantener el script corriendo

with client:
    client.loop.run_until_complete(main())
