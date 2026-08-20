from flask import Flask
from flask_wtf import CSRFProtect
from config import Config
from app.extensions import db, bcrypt, login_manager, migrate # <-- Importar migrate

csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.portal"
    login_manager.login_message = "Debes iniciar sesión para acceder a esta página."
    login_manager.login_message_category = "warning"
    migrate.init_app(app, db)  # <-- IMPORTANTE: Esta línea activa el comando 'flask db'

    from app.models_all import Usuario

    @login_manager.user_loader
    def cargar_usuario(usuario_id):
        return db.session.get(Usuario, int(usuario_id))

    # Registro de Blueprints (se irán habilitando fase a fase).
    from app.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.usuarios import usuarios_bp
    app.register_blueprint(usuarios_bp)

    from app.categorias import categorias_bp
    app.register_blueprint(categorias_bp)

    from app.productos import productos_bp
    app.register_blueprint(productos_bp)

    from app.tienda import tienda_bp
    app.register_blueprint(tienda_bp)

    from app.pedidos import pedidos_bp
    app.register_blueprint(pedidos_bp)

    from app.notas_venta import notas_venta_bp
    app.register_blueprint(notas_venta_bp)

    from app.reportes import reportes_bp
    app.register_blueprint(reportes_bp)

    from app.api import api_bp
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    from app.tienda.utils_carrito import cantidad_total_items, calcular_resumen_carrito

    @app.context_processor
    def inyectar_carrito():
        return {
            "cantidad_carrito": cantidad_total_items,
            "resumen_carrito": lambda: calcular_resumen_carrito(current_user_seguro()),
        }

    @app.context_processor
    def inyectar_categorias_menu():
        from app.models_all import Categoria
        categorias = (
            Categoria.query.filter_by(activo=True)
            .order_by(Categoria.nombre)
            .all()
        )
        return {"categorias_menu": categorias}

    @app.context_processor
    def inyectar_empresa_config():
        from app.models_all import ConfiguracionEmpresa
        return {"empresa_config": ConfiguracionEmpresa.query.first()}

    @app.context_processor
    def inyectar_tipo_cambio():
        from app.tienda.utils_moneda import obtener_tipo_cambio
        return {"tipo_cambio_actual": obtener_tipo_cambio}

    def current_user_seguro():
        from flask_login import current_user
        return current_user

    return app


