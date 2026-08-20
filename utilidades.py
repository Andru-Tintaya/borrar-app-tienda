from functools import wraps
from flask import abort
from flask_login import current_user


def requiere_rol(*roles_permitidos):
    """Restringe una ruta a los roles indicados.

    Uso:
        @requiere_rol("Gerente", "Administrador")
    """
    def decorador(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.tiene_rol(*roles_permitidos):
                abort(403)
            return func(*args, **kwargs)
        return envoltura
    return decorador


def cliente_aprobado_b2b(func):
    """Restringe una ruta a clientes B2B (Minorista/Mayorista) cuya cuenta
    ya fue aprobada por Gerencia/Administración.
    """
    @wraps(func)
    def envoltura(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.es_cliente_externo():
            abort(403)
        if current_user.estado_aprobacion_b2b != "Aprobado":
            abort(403)
        return func(*args, **kwargs)
    return envoltura
