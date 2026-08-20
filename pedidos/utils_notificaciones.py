def notificar_cambio_estado(pedido):
    """Notifica al cliente que el estado de su pedido cambió.

    NOTA (pendiente de aprobación, igual que el envío de OTP): todavía no
    hay un canal real conectado (correo/WhatsApp). Mientras tanto, en modo
    desarrollo, el aviso se registra en el log del servidor para poder
    probar el flujo completo. Cuando definas el canal lo conectamos aquí.
    """
    print(
        f"[NAHARA][NOTIFICACION-DEV] Pedido #{pedido.id} de {pedido.usuario.correo} "
        f"cambió a estado: {pedido.estado}"
    )
