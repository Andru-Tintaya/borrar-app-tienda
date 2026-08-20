import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from app.notas_venta.utils_monto_letras import monto_a_letras_bolivianos

ANCHO, ALTO = A4
MARGEN = 15 * mm


def _tipo_venta_legible(nivel_precio):
    return nivel_precio.upper()


def generar_pdf_nota_venta(pedido, empresa):
    """Genera la Nota de Venta en PDF (formato AUDY) para `pedido` y
    devuelve los bytes del archivo. `empresa` es un ConfiguracionEmpresa
    (puede tener campos vacíos si Gerencia aún no los configuró)."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    y = ALTO - MARGEN

    # --- Encabezado: nombre comercial grande + datos de la empresa ---
    c.setFont("Helvetica-Bold", 34)
    c.drawString(MARGEN, y - 20, empresa.nombre_comercial or "NAHARA")

    x_datos_empresa = MARGEN + 70 * mm
    y_datos = y
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_datos_empresa, y_datos, "Dirección:")
    c.setFont("Helvetica", 8)
    direccion_empresa = (empresa.direccion or "-")
    if len(direccion_empresa) > 28:
        direccion_empresa = direccion_empresa[:27] + "…"
    c.drawString(x_datos_empresa + 45, y_datos, direccion_empresa)
    y_datos -= 10
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_datos_empresa, y_datos, "NIT:")
    c.setFont("Helvetica", 8)
    c.drawString(x_datos_empresa + 45, y_datos, empresa.nit or "-")
    y_datos -= 10
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_datos_empresa, y_datos, "Celular:")
    c.setFont("Helvetica", 8)
    c.drawString(x_datos_empresa + 45, y_datos, empresa.celular or "-")
    y_datos -= 10
    c.setFont("Helvetica", 8)
    c.drawString(x_datos_empresa, y_datos, empresa.ciudad or "-")

    # --- Bloque derecho: tipo de documento y datos del pedido ---
    x_derecha = ANCHO - MARGEN
    y_der = y
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(x_derecha, y_der, "NOTA DE VENTA")
    y_der -= 16
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(x_derecha, y_der, f"NRO.: {pedido.numero_nota}")
    y_der -= 12
    c.setFont("Helvetica", 8)
    c.drawRightString(x_derecha, y_der, f"Tipo: {_tipo_venta_legible(pedido.nivel_precio)}")
    y_der -= 12
    c.drawRightString(x_derecha, y_der, f"Pago: {pedido.metodo_pago.upper()}")
    y_der -= 12
    fecha_texto = pedido.fecha_verificacion.strftime("%Y-%m-%d") if pedido.fecha_verificacion else pedido.fecha_creacion.strftime("%Y-%m-%d")
    c.drawRightString(x_derecha, y_der, f"Fecha: {fecha_texto}")
    y_der -= 12
    usuario_cajero = pedido.verificado_por.nombre if pedido.verificado_por else "-"
    c.drawRightString(x_derecha, y_der, f"Cajero: {usuario_cajero}")
    y_der -= 12
    if pedido.tipo_cambio_aplicado:
        c.drawRightString(x_derecha, y_der, f"T. Cambio: {float(pedido.tipo_cambio_aplicado):.4f} Bs./USD")

    y -= 72

    c.line(MARGEN, y, ANCHO - MARGEN, y)
    y -= 14

    # --- Datos del cliente ---
    cliente = pedido.usuario
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGEN, y, "Cliente:")
    c.setFont("Helvetica", 9)
    c.drawString(MARGEN + 45, y, cliente.nombre.upper())

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_datos_empresa, y, "Celular:")
    c.setFont("Helvetica", 9)
    c.drawString(x_datos_empresa + 45, y, cliente.telefono or "-")
    y -= 12

    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGEN, y, "Razón Soc.:")
    c.setFont("Helvetica", 9)
    razon_social = cliente.razon_social or cliente.nombre.upper()
    c.drawString(MARGEN + 55, y, razon_social)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_datos_empresa, y, "Dirección:")
    c.setFont("Helvetica", 9)
    direccion_cliente = pedido.direccion_envio or ("Retiro en tienda" if pedido.tipo_entrega == "Retiro en tienda" else "-")
    c.drawString(x_datos_empresa + 50, y, direccion_cliente)
    y -= 14

    c.line(MARGEN, y, ANCHO - MARGEN, y)
    y -= 14

    # --- Tabla de artículos ---
    columnas_x = {
        "cant": MARGEN,
        "producto": MARGEN + 40,
        "precio": ANCHO - MARGEN - 150,
        "desc": ANCHO - MARGEN - 95,
        "subtotal": ANCHO - MARGEN - 45,
    }
    c.setFont("Helvetica-Bold", 8)
    c.drawString(columnas_x["cant"], y, "CANT.")
    c.drawString(columnas_x["producto"], y, "PRODUCTO")
    c.drawRightString(columnas_x["precio"] + 30, y, "PRECIO")
    c.drawRightString(columnas_x["desc"] + 25, y, "DESC.")
    c.drawRightString(columnas_x["subtotal"] + 40, y, "SUBTOTAL")
    y -= 10
    c.line(MARGEN, y, ANCHO - MARGEN, y)
    y -= 12

    c.setFont("Helvetica", 8)
    for item in pedido.items:
        c.drawString(columnas_x["cant"], y, f"{item.cantidad:.2f}")
        nombre_producto = item.nombre_producto[:55]
        c.drawString(columnas_x["producto"], y, nombre_producto)
        c.drawRightString(columnas_x["precio"] + 30, y, f"{float(item.precio_unitario):.2f}")
        c.drawRightString(columnas_x["desc"] + 25, y, "0.00")
        c.drawRightString(columnas_x["subtotal"] + 40, y, f"{float(item.subtotal):.2f}")
        y -= 12
        if y < 100:  # margen de seguridad ante pedidos muy largos
            c.showPage()
            y = ALTO - MARGEN

    y -= 6
    c.line(MARGEN, y, ANCHO - MARGEN, y)
    y -= 14

    # --- Totales ---
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(columnas_x["desc"] + 25, y, "SUBTOTAL:")
    c.drawRightString(columnas_x["subtotal"] + 40, y, f"{float(pedido.subtotal):.2f}")
    y -= 12
    c.drawRightString(columnas_x["desc"] + 25, y, "DESCUENTO:")
    c.drawRightString(columnas_x["subtotal"] + 40, y, "0.00")
    y -= 12
    if pedido.costo_envio and float(pedido.costo_envio) > 0:
        etiqueta_envio = f"ENVÍO ({pedido.metodo_envio_nombre}):" if pedido.metodo_envio_nombre else "ENVÍO:"
        c.drawRightString(columnas_x["desc"] + 25, y, etiqueta_envio)
        c.drawRightString(columnas_x["subtotal"] + 40, y, f"{float(pedido.costo_envio):.2f}")
        y -= 12

    c.setFont("Helvetica", 8)
    c.drawString(MARGEN, y, f"SON: {monto_a_letras_bolivianos(pedido.total)}")
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(columnas_x["desc"] + 25, y, "TOTAL:")
    c.drawRightString(columnas_x["subtotal"] + 40, y, f"{float(pedido.total):.2f}")
    y -= 12
    c.setFont("Helvetica", 8)
    c.drawRightString(columnas_x["desc"] + 25, y, "TRANSF:")
    c.drawRightString(columnas_x["subtotal"] + 40, y, f"{float(pedido.total):.2f}")

    y -= 40

    # --- Firmas de conformidad ---
    etiquetas = ["Entregué conforme", "Recibi conforme", "Encargo de almacén", "Vo. Bo."]
    ancho_col = (ANCHO - 2 * MARGEN) / 4
    c.setFont("Helvetica-Bold", 8)
    for i, etiqueta in enumerate(etiquetas):
        x_centro = MARGEN + ancho_col * i + ancho_col / 2
        c.line(MARGEN + ancho_col * i + 5, y + 10, MARGEN + ancho_col * (i + 1) - 5, y + 10)
        c.drawCentredString(x_centro, y - 2, etiqueta)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
