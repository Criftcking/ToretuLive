COMANDOS DE ADMINISTRADOR - BOT DE BÚSQUEDA DE TARJETAS

COMANDOS BÁSICOS:
/start - Muestra el mensaje de bienvenida e información del bot
/info - Muestra información detallada de la cuenta del usuario
/miplan - Muestra información del plan actual del usuario

COMANDOS DE BÚSQUEDA:
/bin <BIN> - Buscar por BIN (primeros dígitos)
/bin <BIN> <mes> - Buscar por BIN y mes de expiración
/bin <BIN> <año> - Buscar por BIN y año de expiración
/bin <BIN> <mes> <año> - Buscar por BIN, mes y año
/binfecha <BIN>|<mes>|<año> - Buscar por BIN y fecha específica

COMANDOS DE ADMINISTRACIÓN:
/register <user_id> [plan] - Registrar usuario con plan específico
   Planes disponibles: free, basico, premium, vip
   Ejemplo: /register 123456789 premium

/deleteplan <user_id> - Eliminar plan de usuario (cambia a FREE)
   Ejemplo: /deleteplan 123456789

/users - Listar todos los usuarios registrados con su estado

/restore - Restablece el plan actual de un usuario


PLANES DISPONIBLES:
🎁 FREE - $0 USD
   • 1 tarjeta por solicitud
   • 1 solicitud por hora

💎 BÁSICO - $10 USD (1 semana)
   • 5 tarjetas por solicitud
   • 10 solicitudes por hora

🌟 PREMIUM - $20 USD (1 semana)
   • 10 tarjetas por solicitud
   • 20 solicitudes por hora

👑 VIP - $30 USD (1 semana)
   • 15 tarjetas por solicitud
   • 35 solicitudes por hora

NOTAS:
- Los planes pagos duran exactamente 7 días
- Los usuarios con plan expirado se cambian automáticamente a FREE
- El comando /deleteplan cambia al usuario al plan FREE inmediatamente
- Solo los administradores pueden usar /register, /deleteplan , /users y /restore 