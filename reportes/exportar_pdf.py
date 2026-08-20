import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def exportar_reporte_pdf(filas, resumen, filtros_texto):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15 * mm, bottomMargin=15 * mm)
    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph("NAHARA — Reporte de Ventas e Ingresos", estilos["Title"]),
        Paragraph(filtros_texto, estilos["Normal"]),
        Spacer(1, 10),
    ]

    datos = [["Fecha", "Pedido", "Producto", "Categoría", "Canal", "Cant.", "P. Unit.", "Subtotal"]]
    for f in filas:
        datos.append([
            f["fecha"].strftime("%Y-%m-%d"),
            f"#{f['pedido_id']}",
            f["producto"],
            f["categoria"],
            f["canal"],
            str(f["cantidad"]),
            f"{float(f['precio_unitario']):.2f}",
            f"{float(f['subtotal']):.2f}",
        ])

    tabla = Table(datos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#f4ca00")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (5, 1), (-1, -1), "RIGHT"),
    ]))
    elementos.append(tabla)
    elementos.append(Spacer(1, 14))

    resumen_texto = (
        f"Total unidades vendidas: {resumen['total_unidades']} &nbsp;&nbsp; "
        f"Total ingresos: Bs. {float(resumen['total_ingresos']):.2f}<br/>"
        + " &nbsp;&nbsp; ".join(
            f"{canal}: {datos_canal['unidades']} u. / Bs. {float(datos_canal['ingresos']):.2f}"
            for canal, datos_canal in resumen["por_canal"].items()
        )
    )
    elementos.append(Paragraph(resumen_texto, estilos["Normal"]))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
