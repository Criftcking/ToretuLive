import psycopg2
import psycopg2.extras
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import re
import os
from datetime import datetime, timedelta
import time

# === CONFIGURACIÓN ===
BOT_TOKEN = "7749960022:AAHRgIbhiV0gAngpCQzSzjpdYthhvn6ghX0"
ARCHIVO_TARJETAS = "Team_Wolf_Lives_mensajes.txt"

# Configuración de conexión PostgreSQL usando variables de entorno
import os
PGUSER = os.environ.get("PGUSER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
RAILWAY_PRIVATE_DOMAIN = os.environ.get("RAILWAY_PRIVATE_DOMAIN")
PGDATABASE = os.environ.get("PGDATABASE")
BASE_URL = f"postgresql://postgres:HHksJErrGGMthwnZbmGxpckTusSlfrmK@crossover.proxy.rlwy.net:26803/railway"

def get_conn():
    return psycopg2.connect(BASE_URL, cursor_factory=psycopg2.extras.DictCursor)

# Lista de administradores (agrega más IDs según necesites)
ADMIN_IDS = [5857858003, 1234567890]  # <-- Agrega los IDs de los administradores

# Límites de planes - MODIFICADO para usuarios free
PLAN_LIMITES = {
    "free": {"tarjetas_por_solicitud": 1, "solicitudes_por_hora": 3, "solicitudes_por_12h": 3, "duracion_dias": 0, "precio": 0},
    "basico": {"tarjetas_por_solicitud": 2, "solicitudes_por_hora": 5, "solicitudes_por_12h": 999, "duracion_dias": 7, "precio": 10},
    "premium": {"tarjetas_por_solicitud": 2, "solicitudes_por_hora": 10, "solicitudes_por_12h": 999, "duracion_dias": 7, "precio": 20},
    "vip": {"tarjetas_por_solicitud": 3, "solicitudes_por_hora": 20, "solicitudes_por_12h": 999, "duracion_dias": 7, "precio": 30}
}

# === BASE DE DATOS DE USUARIOS ===
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id BIGINT PRIMARY KEY,
            username TEXT DEFAULT NULL,
            plan TEXT NOT NULL DEFAULT 'free',
            ultima_solicitud BIGINT DEFAULT 0,
            solicitudes_realizadas INTEGER DEFAULT 0,
            solicitudes_12h INTEGER DEFAULT 0,
            ultima_solicitud_12h BIGINT DEFAULT 0,
            fecha_registro BIGINT DEFAULT 0,
            fecha_expiracion BIGINT DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def usuario_autorizado(user_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, plan, fecha_expiracion FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    conn.close()
    if not resultado:
        return False  # Usuario no existe
    id_usuario, plan, fecha_expiracion = resultado
    if plan != "free" and fecha_expiracion and time.time() > fecha_expiracion:
        cambiar_a_plan_free(user_id)
        return True
    return True

def cambiar_a_plan_free(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET plan = 'free', fecha_expiracion = 0 WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()

def obtener_plan_usuario(user_id: int) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT plan FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else "free"

def obtener_limites_usuario(user_id: int) -> dict:
    plan = obtener_plan_usuario(user_id)
    return PLAN_LIMITES.get(plan, PLAN_LIMITES["free"])

def obtener_tiempo_restante(user_id: int) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT plan, fecha_expiracion FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    conn.close()
    
    if not resultado:
        return "No disponible"
    
    plan, fecha_expiracion = resultado
    
    if plan == "free":
        return "Ilimitado (Plan Free)"
    
    if not fecha_expiracion:
        return "No disponible"
    
    tiempo_restante = fecha_expiracion - time.time()
    
    if tiempo_restante <= 0:
        return "Expirado"
    
    # Convertir a días, horas, minutos
    dias = int(tiempo_restante // (24 * 3600))
    horas = int((tiempo_restante % (24 * 3600)) // 3600)
    minutos = int((tiempo_restante % 3600) // 60)
    
    if dias > 0:
        return f"{dias} días, {horas} horas"
    elif horas > 0:
        return f"{horas} horas, {minutos} minutos"
    else:
        return f"{minutos} minutos"

def obtener_info_usuario_completa(user_id: int) -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, plan, ultima_solicitud, solicitudes_realizadas, solicitudes_12h, ultima_solicitud_12h, fecha_registro, fecha_expiracion FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    conn.close()
    
    if not resultado:
        return None
        
    id_usuario, username, plan, ultima_solicitud, solicitudes_realizadas, solicitudes_12h, ultima_solicitud_12h, fecha_registro, fecha_expiracion = resultado
    
    # Calcular tiempo desde última solicitud
    if ultima_solicitud:
        tiempo_desde_ultima_solicitud = time.time() - ultima_solicitud
        horas_desde_solicitud = int(tiempo_desde_ultima_solicitud // 3600)
        minutos_desde_solicitud = int((tiempo_desde_ultima_solicitud % 3600) // 60)
        ultima_solicitud_str = f"{horas_desde_solicitud}h {minutos_desde_solicitud}m ago"
    else:
        ultima_solicitud_str = "Nunca"
    
    # Calcular tiempo desde última solicitud de 12h
    if ultima_solicitud_12h:
        tiempo_restante_12h = (ultima_solicitud_12h + 12 * 3600) - time.time()
        if tiempo_restante_12h > 0:
            horas_restantes = int(tiempo_restante_12h // 3600)
            minutos_restantes = int((tiempo_restante_12h % 3600) // 60)
            tiempo_restante_12h_str = f"{horas_restantes}h {minutos_restantes}m"
        else:
            tiempo_restante_12h_str = "Reiniciado"
    else:
        tiempo_restante_12h_str = "Nunca"
    
    # Calcular fecha de registro
    if fecha_registro:
        fecha_registro_dt = datetime.fromtimestamp(fecha_registro)
        fecha_registro_str = fecha_registro_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_registro_str = "No disponible"
    
    # Calcular estado de la suscripción
    if plan == "free":
        estado = "🆓 FREE (Gratuito)"
    elif fecha_expiracion and time.time() > fecha_expiracion:
        estado = "❌ Expirado"
    else:
        estado = "✅ Activo"
    
    # Calcular fecha de expiración
    if fecha_expiracion and fecha_expiracion > 0:
        fecha_expiracion_dt = datetime.fromtimestamp(fecha_expiracion)
        fecha_expiracion_str = fecha_expiracion_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_expiracion_str = "No aplica"
    
    return {
        "id": id_usuario,
        "username": username if username else "Sin username",
        "plan": plan,
        "estado": estado,
        "ultima_solicitud": ultima_solicitud_str,
        "solicitudes_realizadas": solicitudes_realizadas,
        "solicitudes_12h": solicitudes_12h,
        "tiempo_restante_12h": tiempo_restante_12h_str,
        "fecha_registro": fecha_registro_str,
        "fecha_expiracion": fecha_expiracion_str,
        "limites": obtener_limites_usuario(user_id),
        "tiempo_restante": obtener_tiempo_restante(user_id)
    }

def puede_realizar_solicitud(user_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT plan, ultima_solicitud, solicitudes_realizadas, solicitudes_12h, ultima_solicitud_12h FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    conn.close()
    
    if not resultado:
        return False
        
    plan, ultima_solicitud, solicitudes_realizadas, solicitudes_12h, ultima_solicitud_12h = resultado
    limites = obtener_limites_usuario(user_id)
    
    # Verificar límites de 12 horas para usuarios free
    if plan == "free":
        tiempo_actual = time.time()
        
        # Si ha pasado más de 12 horas desde la primera solicitud del periodo, reiniciar contador
        if ultima_solicitud_12h and (tiempo_actual - ultima_solicitud_12h) > 12 * 3600:
            reiniciar_contador_12h(user_id)
            return True
            
        # Verificar si ha alcanzado el límite de 3 solicitudes en 12 horas
        if solicitudes_12h >= limites["solicitudes_por_12h"]:
            return False
    
    # Reiniciar contador de hora si ha pasado más de una hora (para todos los planes)
    if time.time() - ultima_solicitud > 3600:
        reiniciar_contador_solicitudes(user_id)
        return True
        
    return solicitudes_realizadas < limites["solicitudes_por_hora"]

def registrar_solicitud(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    tiempo_actual = int(time.time())
    c.execute("SELECT plan, solicitudes_12h, ultima_solicitud_12h FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    if resultado:
        plan, solicitudes_12h_actual, ultima_solicitud_12h_actual = resultado
        if plan == "free":
            if solicitudes_12h_actual == 0 or (tiempo_actual - ultima_solicitud_12h_actual) > 12 * 3600:
                c.execute("""
                    UPDATE usuarios 
                    SET ultima_solicitud = %s, solicitudes_realizadas = 1, 
                        solicitudes_12h = 1, ultima_solicitud_12h = %s
                    WHERE id = %s
                """, (tiempo_actual, tiempo_actual, user_id))
            else:
                c.execute("""
                    UPDATE usuarios 
                    SET ultima_solicitud = %s, solicitudes_realizadas = solicitudes_realizadas + 1, 
                        solicitudes_12h = solicitudes_12h + 1
                    WHERE id = %s
                """, (tiempo_actual, user_id))
        else:
            c.execute("""
                UPDATE usuarios 
                SET ultima_solicitud = %s, solicitudes_realizadas = solicitudes_realizadas + 1 
                WHERE id = %s
            """, (tiempo_actual, user_id))
    conn.commit()
    conn.close()

def reiniciar_contador_solicitudes(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET solicitudes_realizadas = 0 WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()

def reiniciar_contador_12h(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET solicitudes_12h = 0, ultima_solicitud_12h = 0 WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()

def registrar_usuario(user_id: int, username: str = None, plan: str = "free") -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    if plan.lower() != "free":
        duracion_dias = PLAN_LIMITES[plan.lower()]["duracion_dias"]
        fecha_expiracion = int(time.time()) + (duracion_dias * 24 * 3600)
    else:
        fecha_expiracion = 0
    if resultado:
        usuario_id, username_actual = resultado
        nuevo_username = username if username else username_actual
        c.execute("UPDATE usuarios SET plan = %s, fecha_expiracion = %s, username = %s WHERE id = %s", 
                 (plan.lower(), fecha_expiracion, nuevo_username, user_id))
        conn.commit()
        conn.close()
        return True
    else:
        c.execute("INSERT INTO usuarios (id, username, plan, fecha_registro, fecha_expiracion) VALUES (%s, %s, %s, %s, %s)", 
                 (user_id, username, plan.lower(), int(time.time()), fecha_expiracion))
        conn.commit()
        conn.close()
        return True

def eliminar_plan_usuario(user_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    if c.fetchone():
        c.execute("UPDATE usuarios SET plan = 'free', fecha_expiracion = 0 WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def restaurar_plan_usuario(user_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT plan FROM usuarios WHERE id = %s", (user_id,))
    resultado = c.fetchone()
    if not resultado:
        conn.close()
        return False
    plan = resultado[0]
    if plan != "free":
        duracion_dias = PLAN_LIMITES[plan]["duracion_dias"]
        fecha_expiracion = int(time.time()) + (duracion_dias * 24 * 3600)
        c.execute("UPDATE usuarios SET fecha_expiracion = %s, ultima_solicitud = 0, solicitudes_realizadas = 0, solicitudes_12h = 0, ultima_solicitud_12h = 0 WHERE id = %s", 
                 (fecha_expiracion, user_id))
    else:
        c.execute("UPDATE usuarios SET ultima_solicitud = 0, solicitudes_realizadas = 0, solicitudes_12h = 0, ultima_solicitud_12h = 0 WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    return True

def es_administrador(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# === BUSCAR BINS ===
def buscar_bins(bin_input: str, mes=None, año=None, limite=1) -> list:
    if not os.path.exists(ARCHIVO_TARJETAS):
        return []

    with open(ARCHIVO_TARJETAS, 'r', encoding='utf-8') as f:
        contenido = f.read()

    bloques = contenido.split("━━━━━━━━━━━━━━━━━━━━━━━━")
    resultados = []
    contador = 0

    for bloque in bloques:
        if contador >= limite:
            break
            
        bloque = bloque.strip()
        if not bloque:
            continue

        match_tarjeta = re.search(r'💳 Tarjeta: ([\d|]+)', bloque)
        match_banco = re.search(r'💰 Banco: (.+)', bloque)
        match_fecha = re.search(r'🕒 Fecha: (.+)', bloque)

        if match_tarjeta and bin_input in match_tarjeta.group(1):
            tarjeta = match_tarjeta.group(1)
            banco = match_banco.group(1) if match_banco else "Desconocido"
            fecha_str = match_fecha.group(1) if match_fecha else "Desconocida"
            
            # Verificar filtros de fecha si se proporcionan
            if mes and año:
                # Buscar mes y año en la fecha
                fecha_match = re.search(r'(\d{1,2})[/\\|](\d{2,4})', fecha_str)
                if fecha_match:
                    fecha_mes = fecha_match.group(1)
                    fecha_año = fecha_match.group(2)
                    
                    # Normalizar formato de año (2 dígitos a 4 dígitos)
                    if len(fecha_año) == 2:
                        fecha_año = "20" + fecha_año
                    
                    # Normalizar formato de mes (asegurar 2 dígitos)
                    if len(fecha_mes) == 1:
                        fecha_mes = "0" + fecha_mes
                    
                    # Normalizar mes y año de búsqueda
                    mes_busqueda = str(mes).zfill(2)
                    año_busqueda = str(año)
                    if len(año_busqueda) == 2:
                        año_busqueda = "20" + año_busqueda
                    
                    # Si no coinciden, saltar esta tarjeta
                    if fecha_mes != mes_busqueda or fecha_año != año_busqueda:
                        continue
                else:
                    # Si no se puede parsear la fecha y se requirió filtro, saltar
                    continue
            elif mes:
                # Solo filtro por mes
                fecha_match = re.search(r'(\d{1,2})[/\\|]', fecha_str)
                if fecha_match:
                    fecha_mes = fecha_match.group(1)
                    if len(fecha_mes) == 1:
                        fecha_mes = "0" + fecha_mes
                    mes_busqueda = str(mes).zfill(2)
                    if fecha_mes != mes_busqueda:
                        continue
                else:
                    continue
            elif año:
                # Solo filtro por año
                fecha_match = re.search(r'[/\\|](\d{2,4})', fecha_str)
                if fecha_match:
                    fecha_año = fecha_match.group(1)
                    if len(fecha_año) == 2:
                        fecha_año = "20" + fecha_año
                    año_busqueda = str(año)
                    if len(año_busqueda) == 2:
                        año_busqueda = "20" + año_busqueda
                    if fecha_año != año_busqueda:
                        continue
                else:
                    continue

            resultado = f"💳 {tarjeta}\n🏦 {banco}\n🕒 {fecha_str}"
            resultados.append(resultado)
            contador += 1

    return resultados

# === /bin ===
async def bin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username

    if not usuario_autorizado(user_id):
        await update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return

    # Verificar límites de solicitudes
    if not puede_realizar_solicitud(user_id):
        plan = obtener_plan_usuario(user_id)
        if plan == "free":
            # Obtener información del contador de 12 horas
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT solicitudes_12h, ultima_solicitud_12h FROM usuarios WHERE id = %s", (user_id,))
            resultado = c.fetchone()
            conn.close()
            
            if resultado:
                solicitudes_12h, ultima_solicitud_12h = resultado
                tiempo_restante = (ultima_solicitud_12h + 12 * 3600) - time.time()
                if tiempo_restante > 0:
                    horas_restantes = int(tiempo_restante // 3600)
                    minutos_restantes = int((tiempo_restante % 3600) // 60)
                    await update.message.reply_text(f"🚫 Has excedido tu límite de 3 solicitudes en 12 horas (Plan Free). Tiempo restante: {horas_restantes}h {minutos_restantes}m")
                else:
                    await update.message.reply_text("🚫 Has excedido tu límite de 3 solicitudes en 12 horas (Plan Free).")
            else:
                await update.message.reply_text("🚫 Has excedido tu límite de 3 solicitudes en 12 horas (Plan Free).")
        else:
            limites = obtener_limites_usuario(user_id)
            await update.message.reply_text(f"🚫 Has excedido tu límite de {limites['solicitudes_por_hora']} solicitudes por hora.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("❗ Uso: /bin <primeros dígitos> [mes] [año]")
        return

    bin_input = context.args[0].strip()

    if not bin_input.isdigit() or len(bin_input) < 4:
        await update.message.reply_text("❗ Ingresa al menos 4 dígitos numéricos del BIN.")
        return

    # Obtener límites según el plan del usuario
    limites = obtener_limites_usuario(user_id)
    max_tarjetas = limites["tarjetas_por_solicitud"]

    # Procesar argumentos adicionales para filtros de fecha
    mes = None
    año = None
    
    if len(context.args) > 1:
        # Verificar si el segundo argumento es mes|año o mes/año
        fecha_parts = re.split(r'[|/]', context.args[1])
        if len(fecha_parts) == 2:
            mes = fecha_parts[0].strip()
            año = fecha_parts[1].strip()
        elif len(context.args) > 2:
            # O son argumentos separados: mes y año
            mes = context.args[1].strip()
            año = context.args[2].strip() if len(context.args) > 2 else None
        else:
            # Solo se proporcionó un segundo argumento (podría ser mes o año)
            if context.args[1].isdigit():
                if len(context.args[1]) <= 2:
                    mes = context.args[1]
                else:
                    año = context.args[1]
    
    # Validar mes y año
    if mes and (not mes.isdigit() or int(mes) < 1 or int(mes) > 12):
        await update.message.reply_text("❗ El mes debe ser un número entre 1 y 12.")
        return
        
    if año and (not año.isdigit() or (len(año) not in [2, 4])):
        await update.message.reply_text("❗ El año debe tener 2 o 4 dígitos.")
        return

    resultados = buscar_bins(bin_input, mes, año, max_tarjetas)
    registrar_solicitud(user_id)  # Registrar la solicitud después de una búsqueda exitosa

    if resultados:
        filtro_info = ""
        if mes and año:
            filtro_info = f" con fecha {mes}|{año}"
        elif mes:
            filtro_info = f" con mes {mes}"
        elif año:
            filtro_info = f" con año {año}"
            
        respuesta = f"🔍 Resultados encontrados para BIN {bin_input}{filtro_info}:\n\n"
        respuesta += "\n\n".join(resultados)
        
        if len(resultados) == max_tarjetas:
            plan = obtener_plan_usuario(user_id)
            if plan == "free":
                respuesta += f"\n\nℹ️ Límite de {max_tarjetas} tarjeta alcanzado (Plan Free)."
            else:
                respuesta += f"\n\nℹ️ Límite de {max_tarjetas} tarjetas alcanzado (según tu plan {plan.upper()})."
    else:
        respuesta = f"⚠️ No se encontraron resultados con BIN {bin_input}."
        if mes or año:
            respuesta += f" y los filtros aplicados."

    await update.message.reply_text(respuesta)

# === /binfecha ===
async def binfecha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username

    if not usuario_autorizado(user_id):
        await update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return

    # Verificar límites de solicitudes
    if not puede_realizar_solicitud(user_id):
        plan = obtener_plan_usuario(user_id)
        if plan == "free":
            # Obtener información del contador de 12 horas
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT solicitudes_12h, ultima_solicitud_12h FROM usuarios WHERE id = %s", (user_id,))
            resultado = c.fetchone()
            conn.close()
            
            if resultado:
                solicitudes_12h, ultima_solicitud_12h = resultado
                tiempo_restante = (ultima_solicitud_12h + 12 * 3600) - time.time()
                if tiempo_restante > 0:
                    horas_restantes = int(tiempo_restante // 3600)
                    minutos_restantes = int((tiempo_restante % 3600) // 60)
                    await update.message.reply_text(f"🚫 Has excedido tu límite de 3 solicitudes en 12 horas (Plan Free). Tiempo restante: {horas_restantes}h {minutos_restantes}m")
                else:
                    await update.message.reply_text("🚫 Has excedido tu límite de 3 solicitudes en 12 horas (Plan Free).")
            else:
                await update.message.reply_text("🚫 Has excedido tu límite de 3 solicitudes en 12 horas (Plan Free).")
        else:
            limites = obtener_limites_usuario(user_id)
            await update.message.reply_text(f"🚫 Has excedido tu límite de {limites['solicitudes_por_hora']} solicitudes por hora.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("❗ Uso: /binfecha <BIN>|<mes>|<año> o /binfecha <BIN> <mes> <año>")
        return

    # Obtener límites según el plan del usuario
    limites = obtener_limites_usuario(user_id)
    max_tarjetas = limites["tarjetas_por_solicitud"]

    # Procesar argumentos (puede ser un solo argumento con | o / como separador)
    if '|' in context.args[0] or '/' in context.args[0]:
        # Formato: BIN|mes|año
        partes = re.split(r'[|/]', context.args[0])
        if len(partes) < 3:
            await update.message.reply_text("❗ Formato incorrecto. Usa: BIN|mes|año")
            return
        bin_input = partes[0].strip()
        mes = partes[1].strip()
        año = partes[2].strip()
    else:
        # Formato: BIN mes año
        if len(context.args) < 3:
            await update.message.reply_text("❗ Necesitas especificar BIN, mes y año.")
            return
        bin_input = context.args[0].strip()
        mes = context.args[1].strip()
        año = context.args[2].strip()

    if not bin_input.isdigit() or len(bin_input) < 4:
        await update.message.reply_text("❗ Ingresa al menos 4 dígitos numéricos del BIN.")
        return
        
    if not mes.isdigit() or int(mes) < 1 or int(mes) > 12:
        await update.message.reply_text("❗ El mes debe ser un número entre 1 y 12.")
        return
        
    if not año.isdigit() or (len(año) not in [2, 4]):
        await update.message.reply_text("❗ El año debe tener 2 o 4 dígitos.")
        return

    resultados = buscar_bins(bin_input, mes, año, max_tarjetas)
    registrar_solicitud(user_id)  # Registrar la solicitud después de una búsqueda exitosa

    if resultados:
        respuesta = f"🔍 Resultados encontrados para BIN {bin_input} con fecha {mes}|{año}:\n\n"
        respuesta += "\n\n".join(resultados)
        
        if len(resultados) == max_tarjetas:
            plan = obtener_plan_usuario(user_id)
            if plan == "free":
                respuesta += f"\n\nℹ️ Límite de {max_tarjetas} tarjeta alcanzado (Plan Free)."
            else:
                respuesta += f"\n\nℹ️ Límite de {max_tarjetas} tarjetas alcanzado (según tu plan {plan.upper()})."
    else:
        respuesta = f"⚠️ No se encontraron resultados con BIN {bin_input} y fecha {mes}|{año}."

    await update.message.reply_text(respuesta)

# === /start ===
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    username = update.effective_user.username

    # Registrar automáticamente al usuario con plan FREE si no existe
    if not usuario_autorizado(user_id):
        # Nuevo usuario, registrar con plan FREE
        registrar_usuario(user_id, username, "free")
        mensaje_registro = "🎉 ¡Te has registrado automáticamente con plan FREE!"
    else:
        # Actualizar username si ha cambiado
        registrar_usuario(user_id, username, obtener_plan_usuario(user_id))
        mensaje_registro = "✅ Ya estás registrado en el sistema."

    # Obtener información del usuario
    plan_actual = obtener_plan_usuario(user_id)
    limites = obtener_limites_usuario(user_id)
    tiempo_restante = obtener_tiempo_restante(user_id)
    
    usuario_info = f"""
👤 INFORMACIÓN DE TU CUENTA:
• Plan actual: {plan_actual.upper()}
• Límite de tarjetas por solicitud: {limites['tarjetas_por_solicitud']}
• Límite de solicitudes por hora: {limites['solicitudes_por_hora']}
• Límite de solicitudes por 12h: {limites['solicitudes_por_12h']}
• Tiempo restante: {tiempo_restante}

{mensaje_registro}

─────────────────
"""

    # Información sobre planes
    planes_info = """
📋 PLANES DISPONIBLES:

🎁 FREE - $0 USD (Acceso básico)
   • Límite de 1 tarjeta por solicitud
   • 3 solicitudes por 12 horas

💎 BÁSICO - $10 USD (1 semana)
   • Límite de 2 tarjetas por solicitud
   • 5 solicitudes por hora

🌟 PREMIUM - $20 USD (1 semana)
   • Límite de 2 tarjetas por solicitud
   • 10 solicitudes por hora

👑 VIP - $30 USD (1 semana)
   • Límite de 3 tarjetas por solicitud
   • 20 solicitudes por hora

💡 Para actualizar a un plan premium, contacta a un administrador.

─────────────────
"""

    welcome_text = f"""
✨ ¡Hola {user_name}! ✨
Bienvenido al Bot de Búsqueda de Tarjetas @CCCHerker_bot

👤 *Creado por: @GhostHat_Real1  
🤝 *Colaboración con: @thetoretu

 Obten tu UserId con: @userinfobot

 [Unete a nuestra comunidad]
 https://t.me/toretu_updates
 https://t.me/+tbMcgM1LNcIzYWUx


{planes_info}
{usuario_info}
🔍 Funciones disponibles:
• `/bin <BIN>` - Buscar por BIN (primeros 6+ dígitos)  
• `/bin <BIN> <mes>` - Buscar por BIN y mes de expiración  
• `/bin <BIN> <año>` - Buscar por BIN y año de expiración  
• `/bin <BIN> <mes> <año>` - Buscar por BIN, mes y año  
• `/binfecha <BIN>|<mes>|<año>` - Buscar por BIN y fecha específica  
• `/info` - Ver información detallada de tu cuenta

─────────────────

📝 Ejemplos de uso:
• `/bin 490070` - Todos los BINs que comiencen con 490070  
• `/bin 490070 12` - BINs que expiren en diciembre  
• `/bin 490070 2029` - BINs que expiren en 2029  
• `/bin 490070 12 2029` - BINs específicos con fecha  

💡 ¡Explora y encuentra la información que necesitas fácilmente!
"""



    # Intentar enviar la imagen de banner si existe
    banner_paths = ["banner.jpg", "banner.png", "banner.jpeg"]
    banner_file = None
    for path in banner_paths:
        if os.path.exists(path):
            banner_file = path
            break

    try:
        if banner_file:
            # Primero enviar la foto
            await update.message.reply_photo(photo=open(banner_file, "rb"))
            # Luego enviar el texto con formato
            await update.message.reply_text(welcome_text, parse_mode="Markdown")
        else:
            # Si no hay banner, enviar solo el texto
            await update.message.reply_text(welcome_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error al enviar mensaje de inicio: {e}")
        # Si falla el formato Markdown, enviar texto plano
        await update.message.reply_text(welcome_text)

# === /info ===
# === /info ===
async def info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not usuario_autorizado(user_id):
        await update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return

    info = obtener_info_usuario_completa(user_id)
    
    if not info:
        await update.message.reply_text("❌ No se pudo obtener la información de tu cuenta.")
        return

    # Escapar caracteres especiales de Markdown en los campos de texto
    username_escaped = info['username'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
    
    respuesta = f"""
📊 *INFORMACIÓN DETALLADA DE TU CUENTA*

👤 ID de usuario: `{info['id']}`
👥 Username: @{username_escaped} 
📋 Plan actual: {info['plan'].upper()}
🔰 Estado: {info['estado']}

⏰ Tiempo restante: {info['tiempo_restante']}
📅 Fecha de expiración: {info['fecha_expiracion']}
📝 Fecha de registro: {info['fecha_registro']}

🔍 Límites actuales:
   • Tarjetas por solicitud: {info['limites']['tarjetas_por_solicitud']}
   • Solicitudes por hora: {info['limites']['solicitudes_por_hora']}

📈 Estadísticas de uso:
   • Última solicitud: {info['ultima_solicitud']}
   • Solicitudes realizadas: {info['solicitudes_realizadas']}

💡 Para renovar o mejorar tu plan, contacta a un administrador.
"""

    await update.message.reply_text(respuesta, parse_mode="Markdown")

# === /register (solo admin) ===
async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id

    if not es_administrador(sender_id):
        await update.message.reply_text("🚫 Solo los administradores pueden usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❗ Uso: /register <user_id> [plan]")
        await update.message.reply_text("📋 Planes disponibles: free, basico, premium, vip")
        return

    target_id = context.args[0].strip()
    if not target_id.isdigit():
        await update.message.reply_text("❗ El ID debe ser numérico.")
        return

    # Determinar el plan (por defecto: free)
    plan = "free"
    if len(context.args) > 1:
        plan_solicitado = context.args[1].lower().strip()
        if plan_solicitado in PLAN_LIMITES:
            plan = plan_solicitado
        else:
            await update.message.reply_text("❗ Plan no válido. Usa: free, basico, premium o vip")
            return

    target_id = int(target_id)
    precio = PLAN_LIMITES[plan]["precio"]
    duracion = PLAN_LIMITES[plan]["duracion_dias"]
    
    if registrar_usuario(target_id, None, plan):
        if plan == "free":
            await update.message.reply_text(f"✅ Usuario {target_id} registrado correctamente con plan {plan.upper()} (gratuito).")
        else:
            await update.message.reply_text(
                f"✅ Usuario {target_id} registrado correctamente con plan {plan.upper()}.\n"
                f"💲 Precio: ${precio} USD\n"
                f"⏰ Duración: {duracion} días"
            )
    else:
        if plan == "free":
            await update.message.reply_text(f"ℹ️ El usuario {target_id} ya estaba registrado. Se actualizó a plan {plan.upper()} (gratuito).")
        else:
            await update.message.reply_text(
                f"ℹ️ El usuario {target_id} ya estaba registrado. Se actualizó to plan {plan.upper()}.\n"
                f"💲 Precio: ${precio} USD\n"
                f"⏰ Duración: {duracion} días"
            )

# === /deleteplan (solo admin) ===
async def deleteplan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id

    if not es_administrador(sender_id):
        await update.message.reply_text("🚫 Solo los administradores pueden usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❗ Uso: /deleteplan <user_id>")
        return

    target_id = context.args[0].strip()
    if not target_id.isdigit():
        await update.message.reply_text("❗ El ID debe ser numérico.")
        return

    target_id = int(target_id)
    
    if eliminar_plan_usuario(target_id):
        await update.message.reply_text(f"✅ Plan eliminado correctamente para el usuario {target_id}. Ahora tiene plan FREE.")
    else:
        await update.message.reply_text(f"❌ El usuario {target_id} no existe en la base de datos.")

# === /restore (solo admin) ===
async def restore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id

    if not es_administrador(sender_id):
        await update.message.reply_text("🚫 Solo los administradores pueden usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❗ Uso: /restore <user_id>")
        return

    target_id = context.args[0].strip()
    if not target_id.isdigit():
        await update.message.reply_text("❗ El ID debe ser numérico.")
        return

    target_id = int(target_id)
    
    
    if restaurar_plan_usuario(target_id):
        plan = obtener_plan_usuario(target_id)
        if plan == "free":
            await update.message.reply_text(f"✅ Plan FREE restaurado correctamente para el usuario {target_id}. Contadores reiniciados.")
        else:
            tiempo_restante = obtener_tiempo_restante(target_id)
            await update.message.reply_text(
                f"✅ Plan {plan.upper()} restaurado correctamente para el usuario {target_id}.\n"
                f"⏰ Tiempo restante: {tiempo_restante}\n"
                f"🔄 Contadores de uso reiniciados"
            )
    else:
        await update.message.reply_text(f"❌ El usuario {target_id} no existe en la base de datos.")

# === /miplan ===
async def miplan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not usuario_autorizado(user_id):
        await update.message.reply_text("🚫 No estás autorizado para usar este bot.")
        return

    plan = obtener_plan_usuario(user_id)
    limites = obtener_limites_usuario(user_id)
    tiempo_restante = obtener_tiempo_restante(user_id)
    
    respuesta = f"""
📋 *INFORMACIÓN DE TU PLAN:*

• Plan actual: *{plan.upper()}*
• Tarjetas por solicitud: *{limites['tarjetas_por_solicitud']}*
• Solicitudes por hora: *{limites['solicitudes_por_hora']}*
• Tiempo restante: *{tiempo_restante}*

💡 Para renovar o mejorar tu plan, contacta a un administrador.
"""
    await update.message.reply_text(respuesta, parse_mode="Markdown")

# === /users (solo admin) ===
# === /users (solo admin) ===
# === /users (solo admin) ===
async def users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id

    if not es_administrador(sender_id):
        await update.message.reply_text("🚫 Solo los administradores pueden usar este comando.")
        return

    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, username, plan, fecha_expiracion, solicitudes_realizadas FROM usuarios")
    usuarios = c.fetchall()
    conn.close()

    if not usuarios:
        await update.message.reply_text("📝 No hay usuarios registrados.")
        return

    # Crear una lista de mensajes en lugar de uno grande
    mensajes = []
    mensaje_actual = "👥 *USUARIOS REGISTRADOS - INFORMACIÓN DETALLADA:*\n\n"
    
    for usuario in usuarios:
        user_id, username, plan, fecha_expiracion, solicitudes_realizadas = usuario
        
        # Formatear el username de manera segura
        username_display = f"@{username}" if username else "Sin username"
        
        # Obtener límites del plan
        limites = PLAN_LIMITES.get(plan, PLAN_LIMITES["free"])
        
        # Calcular tiempo restante
        if plan == "free":
            tiempo_restante = "∞ (FREE)"
            estado = "🆓 FREE"
        elif fecha_expiracion and time.time() < fecha_expiracion:
            tiempo_restante_sec = fecha_expiracion - time.time()
            dias_restantes = int(tiempo_restante_sec // (24 * 3600))
            horas_restantes = int((tiempo_restante_sec % (24 * 3600)) // 3600)
            tiempo_restante = f"{dias_restantes}d {horas_restantes}h"
            estado = "✅ Activo"
        else:
            tiempo_restante = "❌ Expirado"
            estado = "❌ Expirado"
        
        # Obtener información de uso actual
        uso_actual = f"{solicitudes_realizadas}/{limites['solicitudes_por_hora']}"
        
        usuario_info = f"""
👤 *ID:* `{user_id}`
👥 *Username:* {username_display}
📋 *Plan:* {plan.upper()}
🔰 *Estado:* {estado}
⏰ *Tiempo restante:* {tiempo_restante}
🔍 *Límites:* {limites['tarjetas_por_solicitud']} tarjetas/solicitud
📊 *Solicitudes/hora:* {uso_actual}
────────────────────────────
"""

        # Si agregar esta información excede el límite, enviar el mensaje actual y empezar uno nuevo
        if len(mensaje_actual) + len(usuario_info) > 4000:
            mensajes.append(mensaje_actual)
            mensaje_actual = usuario_info
        else:
            mensaje_actual += usuario_info
    
    # Agregar el último mensaje
    if mensaje_actual:
        mensajes.append(mensaje_actual)
    
    # Enviar todos los mensajes
    for i, mensaje in enumerate(mensajes):
        try:
            # Usar parse_mode=None para evitar problemas con Markdown
            await update.message.reply_text(mensaje, parse_mode=None)
        except Exception as e:
            # Si falla, intentar enviar sin formato
            try:
                await update.message.reply_text(f"Parte {i+1}/{len(mensajes)}:\n{mensaje}")
            except Exception as e2:
                print(f"Error al enviar parte {i+1}: {e2}")
    
    await update.message.reply_text(f"📊 Total de usuarios: {len(usuarios)}")

# === INICIO DEL BOT ===
def main():
    # Inicializar base de datos
    init_db()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("bin", bin_handler))
    app.add_handler(CommandHandler("binfecha", binfecha_handler))
    app.add_handler(CommandHandler("info", info_handler))
    app.add_handler(CommandHandler("register", register_handler))
    app.add_handler(CommandHandler("deleteplan", deleteplan_handler))
    app.add_handler(CommandHandler("restore", restore_handler))
    app.add_handler(CommandHandler("miplan", miplan_handler))
    app.add_handler(CommandHandler("users", users_handler))

    print("🤖 Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
