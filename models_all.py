from datetime import datetime
from flask_login import UserMixin
from app.extensions import db


class Rol(db.Model):
    """Roles del sistema.

    Personal interno: Gerente, Administrador, Empleado/Vendedor.
    Clientes externos: Cliente Publico, Cliente Minorista, Cliente Mayorista,
    Cliente Franquicia, Cliente Asesora Libre (estos últimos 4 requieren
    aprobación de Gerencia, igual que Minorista/Mayorista).
    Se usa una sola tabla de roles para simplificar `role_required` en ambos
    tipos de usuario (autenticación unificada vía Flask-Login).
    """
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    es_personal_interno = db.Column(db.Boolean, default=False, nullable=False)

    usuarios = db.relationship("Usuario", backref="rol", lazy=True)

    def __repr__(self):
        return f"<Rol {self.nombre}>"


class Usuario(db.Model, UserMixin):
    """Usuario unificado: personal interno (login con contraseña) y clientes
    externos (login sin contraseña vía OTP). El campo `password` es NULL
    para clientes externos.
    """
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=True)  # NULL para clientes externos (OTP)
    telefono = db.Column(db.String(30), nullable=True)
    google_id = db.Column(db.String(150), unique=True, nullable=True)

    rol_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Datos B2B (solo aplican a Cliente Minorista / Cliente Mayorista)
    nit_ci = db.Column(db.String(30), nullable=True)
    razon_social = db.Column(db.String(150), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)
    nivel_b2b_solicitado = db.Column(db.String(20), nullable=True)  # Minorista | Mayorista
    estado_aprobacion_b2b = db.Column(db.String(20), nullable=True)  # Pendiente | Aprobado | Rechazado

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def tiene_rol(self, *nombres_rol):
        return self.rol is not None and self.rol.nombre in nombres_rol

    def es_cliente_externo(self):
        return self.rol is not None and not self.rol.es_personal_interno

    def __repr__(self):
        return f"<Usuario {self.correo}>"


class TokenOTP(db.Model):
    """Código de un solo uso enviado por correo para el login sin
    contraseña de los clientes externos.
    """
    __tablename__ = "tokens_otp"

    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(150), nullable=False, index=True)
    codigo = db.Column(db.String(6), nullable=False)
    expira_en = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ---------------------------------------------------------------------------
# Categorías y Subcategorías (Fase 3)
# ---------------------------------------------------------------------------
class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    imagen = db.Column(db.String(255), nullable=True)  # ruta relativa dentro de app/static/

    subcategorias = db.relationship("Subcategoria", backref="categoria", lazy=True)
    productos = db.relationship("Producto", backref="categoria", lazy=True)

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


class Subcategoria(db.Model):
    __tablename__ = "subcategorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    productos = db.relationship("Producto", backref="subcategoria", lazy=True)

    __table_args__ = (db.UniqueConstraint("nombre", "categoria_id", name="uq_subcategoria_por_categoria"),)

    def __repr__(self):
        return f"<Subcategoria {self.nombre}>"


# ---------------------------------------------------------------------------
# Productos, stock y galería de fotos (Fase 3 — sin tallas: se venden
# productos variados, no solo calzado)
# ---------------------------------------------------------------------------
DIAS_PRODUCTO_NUEVO = 30  # cuántos días después de creado un producto se considera "Nuevo"


NIVELES_PRECIO = ["Minorista", "Mayorista", "Franquicia", "Asesora Libre"]  # de más caro a más barato


class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)  # se genera solo, no lo escribe el usuario
    descripcion = db.Column(db.Text, nullable=True)

    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    subcategoria_id = db.Column(db.Integer, db.ForeignKey("subcategorias.id"), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colores.id"), nullable=True)  # opcional

    # TODO funciona internamente en USD; el Bs. se calcula al vuelo con el
    # tipo de cambio del día (ConfiguracionEmpresa.tipo_cambio_usd). El
    # Gerente puede escribir en USD o en Bs. desde el formulario — el otro
    # guarda en la base de datos siempre es el monto en USD.
    precio_compra_usd = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # SOLO Gerente/Administrador
    tipo_cambio_al_comprar = db.Column(db.Numeric(10, 4), nullable=True)  # tipo de cambio vigente cuando se fijó el costo
    fecha_actualizacion_compra = db.Column(db.DateTime, nullable=True)

    # Matriz de 4 precios de venta en USD (de más caro a más barato):
    # Minorista, Mayorista, Franquicia, Asesora Libre.
    precio_minorista_usd = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    precio_mayorista_usd = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    precio_franquicia_usd = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    precio_asesora_libre_usd = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Cada nivel se puede habilitar/deshabilitar por producto (ej. un
    # producto que no se vende al detalle, solo por mayor).
    minorista_habilitado = db.Column(db.Boolean, default=True, nullable=False)
    mayorista_habilitado = db.Column(db.Boolean, default=True, nullable=False)
    franquicia_habilitado = db.Column(db.Boolean, default=True, nullable=False)
    asesora_libre_habilitado = db.Column(db.Boolean, default=True, nullable=False)

    # Stock único del producto (ya no se desglosa por talla)
    stock = db.Column(db.Integer, default=0, nullable=False)

    # Visibilidad: Activo lo ven todos los clientes; Inactivo solo el
    # personal interno (Gerente/Administrador/Empleado) lo ve, marcado
    # como "Inactivo", en el panel.
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Banderas de estado combinables (un producto puede ser Nuevo Y estar
    # en oferta al mismo tiempo, por ejemplo).
    # "Nuevo" NO se guarda: se calcula solo por fecha_creacion (ver
    # DIAS_PRODUCTO_NUEVO más abajo) — no hay casilla en el formulario.
    es_destacado = db.Column(db.Boolean, default=False, nullable=False)  # antes "Sección WOW"
    en_oferta = db.Column(db.Boolean, default=False, nullable=False)
    porcentaje_descuento = db.Column(db.Numeric(5, 2), nullable=True)  # ej. 20.00 = 20%
    # "Más vendido" NO se guarda aquí: se calcula en vivo a partir de las
    # ventas reales (ver app/productos/utils_mas_vendidos.py), tal como
    # se pidió expresamente.

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    creado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    imagenes = db.relationship(
        "ProductoImagen", backref="producto", lazy=True, cascade="all, delete-orphan",
        order_by="ProductoImagen.orden",
    )
    color = db.relationship("Color", lazy=True)

    @property
    def es_nuevo(self):
        """Un producto es "Nuevo" automáticamente durante los primeros
        DIAS_PRODUCTO_NUEVO días desde su creación; después pasa a
        aparecer solo en su categoría, sin intervención manual."""
        return (datetime.utcnow() - self.fecha_creacion).days < DIAS_PRODUCTO_NUEVO

    @property
    def imagen_principal(self):
        for img in self.imagenes:
            if img.es_principal:
                return img
        return self.imagenes[0] if self.imagenes else None

    def precio_usd_por_nivel(self, nivel):
        valor = {
            "Minorista": self.precio_minorista_usd,
            "Mayorista": self.precio_mayorista_usd,
            "Franquicia": self.precio_franquicia_usd,
            "Asesora Libre": self.precio_asesora_libre_usd,
        }[nivel]
        return float(valor)

    def nivel_habilitado(self, nivel):
        return {
            "Minorista": self.minorista_habilitado,
            "Mayorista": self.mayorista_habilitado,
            "Franquicia": self.franquicia_habilitado,
            "Asesora Libre": self.asesora_libre_habilitado,
        }[nivel]

    def _aplicar_oferta_usd(self, precio_usd):
        if self.en_oferta and self.porcentaje_descuento:
            factor = (100 - float(self.porcentaje_descuento)) / 100
            return round(float(precio_usd) * factor, 2)
        return float(precio_usd)

    def precio_final_usd(self, nivel):
        return self._aplicar_oferta_usd(self.precio_usd_por_nivel(nivel))

    def __repr__(self):
        return f"<Producto {self.sku} - {self.nombre}>"


class Color(db.Model):
    """Catálogo de colores/variantes que el Gerente/Empleado define una
    vez y reutiliza al crear productos (evita duplicados como "Rojo" /
    "rojo" / "Colorado" escritos a mano)."""
    __tablename__ = "colores"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<Color {self.nombre}>"


class ProductoImagen(db.Model):
    """Foto del producto; se permite carga múltiple con orden y una imagen
    marcada como principal (portada de la tarjeta/PDP)."""
    __tablename__ = "producto_imagenes"

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    ruta_archivo = db.Column(db.String(255), nullable=False)
    orden = db.Column(db.Integer, default=0, nullable=False)
    es_principal = db.Column(db.Boolean, default=False, nullable=False)


# ---------------------------------------------------------------------------
# Configuración de pago QR institucional (Fase 4)
# ---------------------------------------------------------------------------
class ConfiguracionPagoQR(db.Model):
    """Fila única con el QR institucional vigente para transferencias."""
    __tablename__ = "configuracion_pago_qr"

    id = db.Column(db.Integer, primary_key=True)
    ruta_imagen_qr = db.Column(db.String(255), nullable=True)
    nombre_beneficiario = db.Column(db.String(150), nullable=True)
    numero_cuenta = db.Column(db.String(50), nullable=True)
    banco = db.Column(db.String(100), nullable=True)


# ---------------------------------------------------------------------------
# Pedidos y checkout (Fase 4)
# ---------------------------------------------------------------------------
# NIVELES_PRECIO ya está definido junto a la clase Producto (más arriba)
ESTADOS_PEDIDO = ["Pendiente", "Pagado", "Despachado", "En Tránsito", "Entregado", "Rechazado"]
ENTREGAS = ["Envio", "Retiro en tienda"]


class ConfiguracionEmpresa(db.Model):
    """Datos institucionales usados en el encabezado de la Nota de Venta
    (formato AUDY): nombre comercial, dirección, NIT y celular. También
    guarda la configuración financiera: márgenes de ganancia por defecto
    (para autocompletar precios al crear un producto) y el tipo de cambio
    del dólar del día."""
    __tablename__ = "configuracion_empresa"

    id = db.Column(db.Integer, primary_key=True)
    nombre_comercial = db.Column(db.String(100), default="NAHARA", nullable=False)
    direccion = db.Column(db.String(255), nullable=True)
    nit = db.Column(db.String(30), nullable=True)
    celular = db.Column(db.String(30), nullable=True)
    ciudad = db.Column(db.String(100), nullable=True)

    # Márgenes por defecto para autocompletar precios de venta a partir
    # del Precio de Compra al crear un producto (editable por producto).
    
    # ###########################################################----------------------------------
    # margen_ganancia_unidad = db.Column(db.Numeric(10, 2), default=55, nullable=False)

    # Cambia esto temporalmente para permitir la migración suave:
    margen_ganancia_unidad = db.Column(db.Numeric(10, 2), nullable=False, default=0.00, server_default="0.00")
    
    margen_ganancia_mayorista = db.Column(db.Numeric(10, 2), default=12.5, nullable=False)

    # Tipo de cambio del dólar del día (referencia; ver nota en el panel
    # de configuración sobre cómo se usa exactamente).
    tipo_cambio_usd = db.Column(db.Numeric(10, 4), nullable=True)
    tipo_cambio_actualizado = db.Column(db.DateTime, nullable=True)


class MetodoEnvio(db.Model):
    """Métodos de envío a nivel nacional (terrestre, aéreo, etc.) con su
    costo, definidos por el Gerente/Administrador. El costo se actualiza
    manualmente según lo que cobren las empresas de transporte."""
    __tablename__ = "metodos_envio"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)  # "Envío a Terminal"
    costo = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<MetodoEnvio {self.nombre} - Bs.{self.costo}>"


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    nivel_precio = db.Column(db.String(20), nullable=False)  # Minorista | Mayorista | Franquicia | Asesora Libre
    tipo_entrega = db.Column(db.String(20), nullable=False, default="Retiro en tienda")
    direccion_envio = db.Column(db.String(255), nullable=True)  # texto libre (ciudad/dirección escrita)
    metodo_envio_nombre = db.Column(db.String(100), nullable=True)  # copia histórica del método elegido
    costo_envio = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    nota = db.Column(db.Text, nullable=True)

    # Tipo de cambio USD->Bs. vigente al momento de la venta (para que el
    # historial de Reportes/Nota de Venta quede fijo aunque el tipo de
    # cambio cambie después).
    tipo_cambio_aplicado = db.Column(db.Numeric(10, 4), nullable=True)

    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)  # subtotal + costo_envio

    comprobante_pago = db.Column(db.String(255), nullable=True)
    metodo_pago = db.Column(db.String(30), default="QR/Transferencia", nullable=False)
    estado = db.Column(db.String(30), default="Pendiente", nullable=False)

    # Datos de tracking y envío interdepartamental
    empresa_transporte = db.Column(db.String(100), nullable=True)
    numero_guia = db.Column(db.String(100), nullable=True)
    numero_guia_foto_url = db.Column(db.String(255), nullable=True)

    numero_nota = db.Column(db.Integer, unique=True, nullable=True)
    verificado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    fecha_verificacion = db.Column(db.DateTime, nullable=True)

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    usuario = db.relationship("Usuario", foreign_keys=[usuario_id], backref="pedidos", lazy=True)
    verificado_por = db.relationship("Usuario", foreign_keys=[verificado_por_id], lazy=True)
    items = db.relationship("ItemPedido", backref="pedido", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Pedido #{self.id} - {self.estado}>"


class ItemPedido(db.Model):
    __tablename__ = "items_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)

    nombre_producto = db.Column(db.String(150), nullable=False)  # copia histórica
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)  # en Bs., ya convertido
    precio_unitario_usd = db.Column(db.Numeric(10, 2), nullable=True)  # copia histórica en USD
    precio_compra_unitario_usd = db.Column(db.Numeric(10, 2), nullable=True)  # copia histórica del costo en USD (para reportes de ganancia)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    nivel_precio = db.Column(db.String(20), nullable=False, default="Minorista")  # Minorista | Mayorista | Franquicia | Asesora Libre

    producto = db.relationship("Producto", lazy=True)
    
    
# ================================================================
# BANNERS PARA EL CARRUSEL PRINCIPAL
# ================================================================
class Banner(db.Model):
    """Banners del carrusel principal de la tienda."""
    __tablename__ = "banners"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    subtitulo = db.Column(db.String(200), nullable=True)
    texto = db.Column(db.String(300), nullable=True)
    boton_texto = db.Column(db.String(50), nullable=True)
    boton_enlace = db.Column(db.String(255), nullable=True)
    imagen = db.Column(db.String(255), nullable=False)
    orden = db.Column(db.Integer, default=0, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    creado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    creado_por = db.relationship("Usuario", lazy=True)

    def __repr__(self):
        return f"<Banner {self.titulo}>"
