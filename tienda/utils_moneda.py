from app.models_all import ConfiguracionEmpresa

TIPO_CAMBIO_RESPALDO = 1.0  # si el Gerente todavía no configuró ninguno (evita división/multiplicación por None)


def obtener_tipo_cambio():
    """Tipo de cambio USD -> Bs. vigente hoy, configurado por el Gerente.
    Si todavía no se configuró ninguno, devuelve 1.0 como respaldo (y el
    panel de configuración avisa que falta configurarlo)."""
    config = ConfiguracionEmpresa.query.first()
    if config is None or config.tipo_cambio_usd is None:
        return TIPO_CAMBIO_RESPALDO
    return float(config.tipo_cambio_usd)


def convertir_a_bob(monto_usd, tipo_cambio=None):
    if tipo_cambio is None:
        tipo_cambio = obtener_tipo_cambio()
    return round(float(monto_usd) * tipo_cambio, 2)


def convertir_a_usd(monto_bob, tipo_cambio=None):
    if tipo_cambio is None:
        tipo_cambio = obtener_tipo_cambio()
    if not tipo_cambio:
        return 0.0
    return round(float(monto_bob) / tipo_cambio, 2)
