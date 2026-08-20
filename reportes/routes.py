from datetime import datetime, timedelta
from flask import render_template, request, Response
from flask_login import login_required

from app.reportes import reportes_bp
from app.reportes.utils_consulta import consultar_ventas, calcular_resumen
from app.reportes.exportar_pdf import exportar_reporte_pdf
from app.reportes.exportar_excel import exportar_reporte_excel
from app.models_all import Producto, Categoria, NIVELES_PRECIO
from app.utilidades import requiere_rol

ROLES_GESTION = ("Gerente", "Administrador", "Empleado")


def _leer_filtros():
    fecha_desde_str = request.args.get("fecha_desde")
    fecha_hasta_str = request.args.get("fecha_hasta")

    fecha_desde = datetime.strptime(fecha_desde_str, "%Y-%m-%d") if fecha_desde_str else None
    fecha_hasta = (
        datetime.strptime(fecha_hasta_str, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        if fecha_hasta_str else None
    )

    return {
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "fecha_desde_str": fecha_desde_str or "",
        "fecha_hasta_str": fecha_hasta_str or "",
        "producto_id": request.args.get("producto_id", type=int),
        "categoria_id": request.args.get("categoria_id", type=int),
        "canal": request.args.get("canal") or None,
    }


def _texto_filtros(filtros):
    partes = []
    if filtros["fecha_desde_str"]:
        partes.append(f"Desde {filtros['fecha_desde_str']}")
    if filtros["fecha_hasta_str"]:
        partes.append(f"Hasta {filtros['fecha_hasta_str']}")
    if filtros["canal"]:
        partes.append(f"Canal: {filtros['canal']}")
    return " · ".join(partes) if partes else "Todas las ventas verificadas"


@reportes_bp.route("/")
@login_required
@requiere_rol(*ROLES_GESTION)
def index():
    filtros = _leer_filtros()
    filas = consultar_ventas(
        fecha_desde=filtros["fecha_desde"], fecha_hasta=filtros["fecha_hasta"],
        producto_id=filtros["producto_id"], categoria_id=filtros["categoria_id"], canal=filtros["canal"],
    )
    resumen = calcular_resumen(filas)

    productos = Producto.query.order_by(Producto.nombre).all()
    categorias = Categoria.query.order_by(Categoria.nombre).all()

    return render_template(
        "reportes/index.html", filas=filas, resumen=resumen, filtros=filtros,
        productos=productos, categorias=categorias, canales=NIVELES_PRECIO,
    )


@reportes_bp.route("/exportar/pdf")
@login_required
@requiere_rol(*ROLES_GESTION)
def exportar_pdf():
    filtros = _leer_filtros()
    filas = consultar_ventas(
        fecha_desde=filtros["fecha_desde"], fecha_hasta=filtros["fecha_hasta"],
        producto_id=filtros["producto_id"], categoria_id=filtros["categoria_id"], canal=filtros["canal"],
    )
    resumen = calcular_resumen(filas)
    pdf_bytes = exportar_reporte_pdf(filas, resumen, _texto_filtros(filtros))
    nombre_archivo = f"Reporte_Ventas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        pdf_bytes, mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={nombre_archivo}"},
    )


@reportes_bp.route("/exportar/excel")
@login_required
@requiere_rol(*ROLES_GESTION)
def exportar_excel():
    filtros = _leer_filtros()
    filas = consultar_ventas(
        fecha_desde=filtros["fecha_desde"], fecha_hasta=filtros["fecha_hasta"],
        producto_id=filtros["producto_id"], categoria_id=filtros["categoria_id"], canal=filtros["canal"],
    )
    resumen = calcular_resumen(filas)
    excel_bytes = exportar_reporte_excel(filas, resumen)
    nombre_archivo = f"Reporte_Ventas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return Response(
        excel_bytes, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )
