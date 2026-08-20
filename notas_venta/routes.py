from flask import Response, abort
from flask_login import login_required, current_user

from app.notas_venta import notas_venta_bp
from app.notas_venta.generar_pdf import generar_pdf_nota_venta
from app.models_all import Pedido, ConfiguracionEmpresa


@notas_venta_bp.route("/<int:pedido_id>")
@login_required
def descargar(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)

    es_staff = current_user.rol.es_personal_interno
    es_dueno = pedido.usuario_id == current_user.id
    if not (es_staff or es_dueno):
        abort(403)

    if pedido.numero_nota is None:
        abort(404, "Este pedido todavía no tiene una Nota de Venta generada (pago aún no verificado).")

    empresa = ConfiguracionEmpresa.query.first() or ConfiguracionEmpresa()
    pdf_bytes = generar_pdf_nota_venta(pedido, empresa)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=NotaVenta_{pedido.numero_nota}.pdf"},
    )
