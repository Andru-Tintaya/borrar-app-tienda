from flask import current_app
from app.models_all import NIVELES_PRECIO
from app.tienda.utils_moneda import obtener_tipo_cambio, convertir_a_bob


def _nivel_base_cliente(usuario):
    """Nivel de precio de partida según el tipo de cuenta del cliente.
    Público / no autenticado / cuenta B2B aún no aprobada -> Minorista
    (el nivel "de entrada", equivalente al antiguo precio al público)."""
    if (
        usuario is not None
        and usuario.is_authenticated
        and usuario.es_cliente_externo()
        and usuario.nivel_b2b_solicitado in NIVELES_PRECIO
        and usuario.estado_aprobacion_b2b == "Aprobado"
    ):
        return usuario.nivel_b2b_solicitado
    return "Minorista"


def calcular_precio_unitario(producto, usuario, cantidad_en_carrito_del_producto):
    """Determina el precio unitario en Bs. y el nivel aplicado para
    `producto`, combinando dos reglas (confirmadas explícitamente):

      1. El nivel de la CUENTA del cliente decide el precio base
         (Minorista/Mayorista/Franquicia/Asesora Libre).
      2. Comprar `UMBRAL_PRECIO_MAYORISTA` unidades o más del MISMO
         producto baja un nivel más (ej. un Mayorista comprando en
         cantidad obtiene precio Franquicia). Nunca baja más allá de
         Asesora Libre.

    Si el nivel resultante está deshabilitado para ese producto en
    particular, se usa el nivel habilitado más cercano hacia arriba (más
    caro) — nunca se le da a alguien un precio que no le corresponde.

    Los precios se guardan en USD; se devuelven ya convertidos a Bs. con
    el tipo de cambio del día.
    """
    idx = NIVELES_PRECIO.index(_nivel_base_cliente(usuario))

    umbral = current_app.config["UMBRAL_PRECIO_MAYORISTA"]
    if cantidad_en_carrito_del_producto >= umbral:
        idx = min(idx + 1, len(NIVELES_PRECIO) - 1)

    # Si el nivel resultante no está habilitado para este producto,
    # retrocede hacia niveles más caros hasta encontrar uno habilitado.
    while idx > 0 and not producto.nivel_habilitado(NIVELES_PRECIO[idx]):
        idx -= 1

    nivel_final = NIVELES_PRECIO[idx]
    precio_usd = producto.precio_final_usd(nivel_final)
    tipo_cambio = obtener_tipo_cambio()
    precio_bob = convertir_a_bob(precio_usd, tipo_cambio)

    return precio_bob, nivel_final
