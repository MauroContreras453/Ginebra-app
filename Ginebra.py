# File: app.py
import os
import io
from datetime import datetime, timedelta
from decimal import Decimal
from flask import ( Flask, render_template, redirect, url_for, request, flash, send_file, send_from_directory, Response, session)
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from flask_sqlalchemy import SQLAlchemy
from flask_login import ( LoginManager, UserMixin, login_user, login_required, logout_user, current_user)
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from flask_migrate import Migrate

# =====================
# CONFIGURACIÓN INICIAL
# =====================
app = Flask(__name__, static_folder='statics')
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_segura')
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'usuarios.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'comprobantes')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# Configuración de itsdangerous
serializer = URLSafeTimedSerializer(app.secret_key)

# Configuración de SQLAlchemy y Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# =====================
# CONSTANTES
# =====================
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
PER_PAGE = 10 # Constante para el número de elementos por página
GESTION_OPTIONS = ('si', 'no')
PRODUCTOS_OPTIONS = ('si', 'no')
ROLES = ('master', 'admin', 'controling', 'ejecutivo', 'analista')
ESTADO_PAGO_OPTIONS = ('Pagado', 'No Pagado')
VENTA_COBRADA_OPTIONS = ('Cobrada', 'No Cobrada')
VENTA_EMITIDA_OPTIONS = ('Emitida', 'No Emitida')
ESTADO_OPTIONS = ('Activo', 'Inactivo')

# =====================
# MODELOS DE BASE DE DATOS
# =====================
class Empresa(db.Model):
    """Modelo para empresas registradas en el sistema."""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    representante = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    razon_social = db.Column(db.String(100))    
    tiene_gestion = db.Column(db.Enum(*GESTION_OPTIONS, name='gestion_options'), default='no')
    tiene_productos = db.Column(db.Enum(*PRODUCTOS_OPTIONS, name='productos_options'), default='no')

class SoftDeleteMixin:
    """Mixin para implementar borrado lógico en modelos."""
    activo = db.Column(db.Boolean, default=True)

    def delete(self):
        """Marca el registro como inactivo (borrado lógico)."""
        self.activo = False

    def restore(self):
        """Restaura el registro marcado como inactivo."""
        self.activo = True

    def hard_delete(self):
        """Elimina el registro de la base de datos de forma permanente."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def activos(cls):
        """Devuelve solo los registros activos."""
        return cls.query.filter_by(activo=True)

class Usuario(UserMixin, db.Model):
    """Modelo para usuarios del sistema."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nombre = db.Column(db.String(150), index=True)
    apellidos = db.Column(db.String(150), index=True)
    rut = db.Column(db.String(12), unique=True, nullable=True, index=True)
    fecha_nacimiento = db.Column(db.Date, index=True)
    fecha_ingreso = db.Column(db.Date, index=True)
    telefono = db.Column(db.String(20), index=True)
    correo_personal = db.Column(db.String(150), index=True)
    correo = db.Column(db.String(150), unique=True, nullable=False, index=True)
    direccion = db.Column(db.String(250), index=True)
    comision = db.Column(db.Numeric(12,2), default=Decimal('0'), index=True)
    sueldo = db.Column(db.Numeric(12,2), default=Decimal('0'), index=True)
    estado = db.Column(db.Enum(*ESTADO_OPTIONS, name='estado_usuario'), default='Activo')
    rol = db.Column(db.Enum(*ROLES, name='roles'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=True)
    empresa = db.relationship('Empresa', backref=db.backref('usuarios', lazy=True))

    @property
    def password(self):
        """No permite leer la contraseña directamente."""
        raise AttributeError('No se puede leer la contraseña')

    @password.setter
    def password(self, password_plain):
        """Establece el hash de la contraseña."""
        self.password_hash = generate_password_hash(password_plain)

    def check_password(self, password_plain):
        """Verifica la contraseña ingresada."""
        return check_password_hash(self.password_hash, password_plain)

class Reserva(db.Model):
    """Modelo para reservas realizadas por usuarios."""
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha_viaje = db.Column(db.Date, nullable=True, index=True)
    fecha_venta = db.Column(db.Date, nullable=True, index=True) 
    producto = db.Column(db.String(100), index=True) 
    modalidad_pago = db.Column(db.String(100), index=True)
    nombre_pasajero = db.Column(db.String(100), index=True)
    telefono_pasajero = db.Column(db.String(100), index=True)
    mail_pasajero = db.Column(db.String(100), index=True)
    precio_venta_total = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    precio_venta_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    hotel_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    vuelo_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    traslado_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    seguro_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    circuito_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    crucero_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    excursion_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    paquete_neto = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    ganancia_total =  db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    comision_ejecutivo = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    comision_agencia = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    bonos = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    localizadores = db.Column(db.Text, nullable=True)
    nombre_ejecutivo = db.Column(db.String(100), index=True)
    correo_ejecutivo = db.Column(db.String(100), index=True)
    destino = db.Column(db.String(100))
    comentarios = db.Column(db.Text, nullable=True)  
    comprobante_venta = db.Column(db.String(200))
    comprobante_pdf = db.Column(db.LargeBinary)
    estado_pago = db.Column(db.Enum(*ESTADO_PAGO_OPTIONS, name='estado_pago_reserva'), default='No Pagado')
    venta_cobrada = db.Column(db.Enum(*VENTA_COBRADA_OPTIONS, name='venta_cobrada_options'), default='No Cobrada')
    venta_emitida = db.Column(db.Enum(*VENTA_EMITIDA_OPTIONS, name='venta_emitida_options'), default='No Emitida')
    usuario = db.relationship('Usuario', backref=db.backref('reservas', lazy=True))
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=True)
    empresa = db.relationship('Empresa', backref=db.backref('reservas', lazy=True))

class Proveedor(SoftDeleteMixin, db.Model):
    """Modelo para productos ofrecidos por la empresa."""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, index=True)
    pais_ciudad = db.Column(db.String(100), nullable=True, index=True)
    direccion = db.Column(db.String(200), nullable=True, index=True)
    tipo_proveedor = db.Column(db.String(100), nullable=True, index=True)
    servicio = db.Column(db.Text, nullable=True, index=True)
    contacto_principal_nombre = db.Column(db.String(100), nullable=True, index=True)
    contacto_principal_email = db.Column(db.String(100), nullable=True, index=True)
    contacto_principal_telefono = db.Column(db.String(100), nullable=True, index=True)
    condiciones_comerciales = db.Column(db.Text, nullable=True, index=True)
    donde_opera = db.Column(db.String(100), nullable=True, index=True)
    ultima_negociacion = db.Column(db.Date, nullable=True, index=True)
    fecha_vigencia = db.Column(db.Date, nullable=True, index=True)
    estado = db.Column(db.Enum(*ESTADO_OPTIONS, name='estado_proveedor'), default='Activo')
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref=db.backref('proveedores', lazy=True))

class Contrato(SoftDeleteMixin, db.Model):
    """Modelo para contratos asociados a proveedor."""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=True, index=True)
    fecha_inicio = db.Column(db.Date, nullable=True, index=True)
    fecha_fin = db.Column(db.Date, nullable=True, index=True)
    estado = db.Column(db.Enum(*ESTADO_OPTIONS, name='estado_contrato'), default='Activo')
    condiciones = db.Column(db.Text, nullable=True, index=True)
    comprobante_venta = db.Column(db.String(200))
    comprobante_pdf = db.Column(db.LargeBinary)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedor.id'), nullable=False)
    proveedor = db.relationship('Proveedor', backref=db.backref('contratos', lazy=True))

class Catalogo(SoftDeleteMixin, db.Model):
    """Modelo para catálogos de proveedor."""
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=True, index=True)
    fecha_inicio = db.Column(db.Date, nullable=True, index=True)
    fecha_fin = db.Column(db.Date, nullable=True, index=True)
    estado = db.Column(db.Enum(*ESTADO_OPTIONS, name='estado_catalogo'), default='Activo')
    costo_base = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), index=True)
    precio_venta_sugerido = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), index=True)
    comision_estimada = db.Column(db.Numeric(12,2), default=Decimal('0.00'), index=True)
    que_incluye = db.Column(db.Text, nullable=True, index=True)
    comprobante_venta = db.Column(db.String(200))
    comprobante_pdf = db.Column(db.LargeBinary)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedor.id'), nullable=False)
    proveedor = db.relationship('Proveedor', backref=db.backref('catalogos', lazy=True))

class Factura(db.Model):
    """Modelo para facturas mensuales de empresas."""
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'), nullable=False)
    empresa = db.relationship('Empresa', backref=db.backref('facturas', lazy=True))
    mes = db.Column(db.Date, nullable=True, index=True)
    monto = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), index=True)
    estado = db.Column(db.Enum(*ESTADO_PAGO_OPTIONS, name='estado_pago_factura'), default='No Pagado')
    fecha_pago = db.Column(db.Date, nullable=True, index=True)
    metodo_pago = db.Column(db.String(50), nullable=True, index=True)
    observaciones = db.Column(db.Text, nullable=True, index=True)

# =====================
# LOGIN MANAGER Y DECORADORES
# =====================
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

@app.context_processor
def inject_global_functions():
    """Hace funciones disponibles en todas las plantillas"""
    return dict(ruta_inicio_por_rol=ruta_inicio_por_rol)

def rol_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.rol not in roles:
                flash('Acceso denegado.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

def empresa_tiene_gestion_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.rol not in ('admin', 'master'):
            empresa = current_user.empresa
            if not empresa or empresa.tiene_gestion != 'si':
                flash('Tu empresa no tiene gestión habilitada. No puedes acceder a reservas.', 'danger')
                return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def empresa_tiene_productos_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.rol not in ('admin', 'master'):
            empresa = current_user.empresa
            if not empresa or empresa.tiene_productos != 'si':
                flash('Tu empresa no tiene productos habilitados. No puedes acceder a productos, contratos ni catálogos.', 'danger')
                return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# =====================
# FUNCIONES AUXILIARES
# =====================
def obtener_nombre_mes(numero_mes):
    """Convierte número de mes a nombre en español"""
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    return meses.get(numero_mes, 'Mes desconocido')

def puede_editar_reserva(reserva):
    return current_user.rol in ('master', 'admin', 'controling') or reserva.usuario_id == current_user.id

def puede_crear_usuario(rol_actual, rol_nuevo):
    jerarquia = ['master', 'admin', 'controling', 'ejecutivo', 'analista']
    if rol_actual not in jerarquia or rol_nuevo not in jerarquia:
        return False
    if rol_actual == 'master' and rol_nuevo == 'master':
        return False
    if rol_actual == 'admin' and rol_nuevo in ['admin', 'master']:
        return False
    if rol_actual == 'controling' and rol_nuevo not in ['ejecutivo', 'analista']:
        return False
    if rol_actual in ['ejecutivo', 'analista']:
        return False
    return jerarquia.index(rol_actual) < jerarquia.index(rol_nuevo)

def puede_asignar_empresa(usuario_actual, empresa_id_objetivo):
    """
    Verifica si el usuario actual puede asignar una empresa específica a un usuario.
    
    Args:
        usuario_actual: El usuario que está realizando la acción
        empresa_id_objetivo: ID de la empresa que se quiere asignar (puede ser None)
    
    Returns:
        bool: True si puede asignar la empresa, False si no
    """
    # Master y admin pueden asignar cualquier empresa
    if usuario_actual.rol in ['master', 'admin']:
        return True
    
    # Controling solo puede asignar usuarios a su propia empresa
    if usuario_actual.rol == 'controling':
        # Si no quiere asignar empresa (None), está permitido
        if empresa_id_objetivo is None:
            return True
        # Solo puede asignar su propia empresa
        return usuario_actual.empresa_id == empresa_id_objetivo
    
    # Otros roles no pueden asignar empresas
    return False

def crear_usuario(form, usuario_actual):
    username = form['username'].strip()
    rol_nuevo = form['rol'].strip()
    empresa_id = int(form.get('empresa_id', 0)) if form.get('empresa_id') else None

    if not puede_crear_usuario(usuario_actual.rol, rol_nuevo):
        return False, "No tienes permiso para crear usuarios con ese rol."

    if not puede_asignar_empresa(usuario_actual, empresa_id):
        return False, "No puedes asignar usuarios a otra empresa."

    if Usuario.query.filter_by(username=username).first():
        return False, "El usuario ya existe."

    if form.get('rut') and Usuario.query.filter_by(rut=form.get('rut').strip()).first():
        return False, "El RUT ya está registrado."

    try:
        comision = float(form.get('comision', '0').strip())
    except ValueError:
        return False, "La comisión debe ser un número válido."

    fecha_nacimiento = None
    if form.get('fecha_nacimiento'):
        try:
            fecha_nacimiento = datetime.strptime(form['fecha_nacimiento'], '%Y-%m-%d').date()
        except ValueError:
            return False, "Formato de fecha inválido."

    fecha_ingreso = None
    if form.get('fecha_ingreso'):
        try:
            fecha_ingreso = datetime.strptime(form['fecha_ingreso'], '%Y-%m-%d').date()
        except ValueError:
            return False, "Formato de fecha de ingreso inválido."
    else:
        fecha_ingreso = datetime.now().date()

    nuevo = Usuario(
        username=username,
        nombre=form['nombre'].strip(),
        apellidos=form['apellidos'].strip(),
        rut=form.get('rut', '').strip(),
        fecha_nacimiento= fecha_nacimiento,
        fecha_ingreso= fecha_ingreso,
        telefono=form.get('telefono', '').strip(),
        correo_personal=form.get('correo_personal', '').strip(),
        correo=form['correo'].strip(),
        direccion=form.get('direccion', '').strip(),
        comision=comision,
        sueldo = safe_decimal(form.get('sueldo', '0').strip()),
        estado=form.get('estado', 'Activo').strip(),
        rol=rol_nuevo,
        empresa_id=empresa_id
    )
    nuevo.password = form['password'].strip()
    db.session.add(nuevo)
    db.session.commit()
    return True, "Usuario creado correctamente."

def editar_usuario_existente(usuario, form, usuario_actual):
    rol_nuevo = form['rol'].strip()
    empresa_id = int(form.get('empresa_id', 0)) if form.get('empresa_id') else None
    
    if not puede_crear_usuario(usuario_actual.rol, rol_nuevo):
        return False, "No tienes permiso para asignar ese rol."
    
    if not puede_asignar_empresa(usuario_actual, empresa_id):
        return False, "No puedes asignar usuarios a otra empresa."
    
    # Validar comisión
    try:
        comision = float(form.get('comision', '0').strip())
    except ValueError:
        return False, "La comisión debe ser un número válido."
    
    # Validar fecha de nacimiento
    fecha_nacimiento = None
    if form.get('fecha_nacimiento'):
        try:
            fecha_nacimiento = datetime.strptime(form['fecha_nacimiento'], '%Y-%m-%d').date()
        except ValueError:
            return False, "Formato de fecha inválido."
    
    # Validar fecha de ingreso
    fecha_ingreso = None
    if form.get('fecha_ingreso'):
        try:
            fecha_ingreso = datetime.strptime(form['fecha_ingreso'], '%Y-%m-%d').date()
        except ValueError:
            return False, "Formato de fecha de ingreso inválido."
    else:
        fecha_ingreso = datetime.now().date()
    
    usuario.username = form['username'].strip()
    password = form['password'].strip()
    if password:
        usuario.password = password
    usuario.nombre = form['nombre'].strip()
    usuario.apellidos = form['apellidos'].strip()
    usuario.rut = form.get('rut', '').strip()
    usuario.fecha_nacimiento = fecha_nacimiento
    usuario.fecha_ingreso = fecha_ingreso
    usuario.telefono = form.get('telefono', '').strip()
    usuario.correo_personal = form.get('correo_personal', '').strip()
    usuario.correo = form['correo'].strip()
    usuario.direccion = form.get('direccion', '').strip()
    usuario.comision = comision
    usuario.sueldo = safe_decimal(form.get('sueldo', '0').strip())
    usuario.rol = rol_nuevo
    usuario.estado = form.get('estado', 'Activo').strip()
    usuario.empresa_id = empresa_id
    db.session.commit()
    return True, "Usuario modificado correctamente."

def puede_eliminar_usuario(usuario):
    # Nadie puede eliminar a mcontreras
    if usuario.username == 'mcontreras':
        return False

    rol_actual = current_user.rol
    rol_objetivo = usuario.rol

    # Ejecutivos y analistas no pueden eliminar a nadie (ni siquiera a sí mismos)
    if rol_actual in ('ejecutivo', 'analista'):
        return False

    # Controling solo puede eliminar ejecutivo o analista de su empresa
    if rol_actual == 'controling':
        if rol_objetivo in ('ejecutivo', 'analista') and usuario.empresa_id == current_user.empresa_id:
            return True
        else:
            return False

    # Si el rol actual es más "alto" que el del usuario objetivo, puede eliminarlo
    if ROLES.index(rol_actual) < ROLES.index(rol_objetivo):
        return True

    # En todos los demás casos, no se puede eliminar
    return False

def formatear_fecha_es(fecha):
    """Formatea una fecha datetime a 'DD de mes YYYY' en español."""
    meses_es = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    if not fecha:
        return ""
    return f"{fecha.day} de {meses_es[fecha.month - 1]} {fecha.year}"

def _get_date_range(rango_fechas_str):
    today = datetime.now()
    if rango_fechas_str == 'ultimos_30_dias':
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        try:
            # Expected format: "Mes Año" (e.g., "Enero 2024")
            # Convertir nombre de mes en español a número
            meses_es = {
                "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
                "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
            }
            month_name, year_str = rango_fechas_str.lower().split(' ')
            month_num = meses_es.get(month_name, today.month)
            year = int(year_str)
            start_date = datetime(year, month_num, 1)
            if month_num == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
        except Exception:
            # Fallback a últimos 30 días si falla el parseo
            start_date = today - timedelta(days=30)
            end_date = today
    return start_date, end_date

def safe_decimal(val):
    if val is None:
        return Decimal('0.00')
    try:
        val = str(val).replace(',', '.').replace(' ', '').strip()
        return Decimal(val)
    except Exception:
        return Decimal('0.00')

def get_campos_por_tipo():
    """Devuelve los campos de Reserva agrupados por tipo."""
    float_types = (db.Float, db.Numeric)
    str_types = (db.String, db.Text, db.Enum)
    campos_float = []
    campos_str = []
    for col in Reserva.__table__.columns:
        if isinstance(col.type, float_types):
            campos_float.append(col.name)
        elif isinstance(col.type, str_types):
            campos_str.append(col.name)
    return campos_float, campos_str

def set_model_fields(obj, form, exclude=None, date_fields=None, handle_pdf=False):
    if exclude is None:
        exclude = set()
    if date_fields is None:
        date_fields = []

    # Detecta tipos de campos
    float_types = (db.Float, db.Numeric)
    str_types = (db.String, db.Text, db.Enum)
    campos_float = []
    campos_str = []
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        if isinstance(col.type, float_types):
            campos_float.append(col.name)
        elif isinstance(col.type, str_types):
            campos_str.append(col.name)

    for campo in campos_float:
        valor = safe_decimal(form.get(campo, 0))
        setattr(obj, campo, valor)

    for campo in campos_str:
        setattr(obj, campo, form.get(campo, '').strip())

    # Manejo especial para campos de fecha
    for campo_fecha in date_fields:
        fecha_val = form.get(campo_fecha, '').strip()
        fecha_date = None
        if fecha_val:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                try:
                    fecha_date = datetime.strptime(fecha_val, fmt).date()
                    break
                except Exception:
                    continue
        setattr(obj, campo_fecha, fecha_date)

def set_reserva_fields(reserva, form):
    # Cálculo de comisiones antes de setear campos
    if reserva.usuario:
        comision_ejecutivo, comision_agencia, ganancia_total, _, precio_venta_neto = calcular_comisiones(reserva, reserva.usuario)
        reserva.comision_ejecutivo = comision_ejecutivo
        reserva.comision_agencia = comision_agencia
        reserva.ganancia_total = ganancia_total
        reserva.precio_venta_neto = precio_venta_neto
    else:
        flash('Error: La reserva no tiene un usuario asociado.', 'danger')
        return
    set_model_fields(
        reserva,
        form,
        exclude={'empresa_id', 'usuario_id', 'usuario', 'comprobante_pdf'},
        date_fields=['fecha_venta', 'fecha_viaje'],
        handle_pdf=True
    )

def set_proveedor_fields(proveedor, form):
    set_model_fields(
        proveedor,
        form,
        exclude={'id', 'empresa_id', 'empresa'},
        date_fields=['fecha_venta']
    )

def set_contrato_fields(contrato, form):
    set_model_fields(
        contrato,
        form,
        exclude={'id', 'producto_id', 'producto', 'comprobante_pdf'},
        date_fields=['fecha_venta'],
        handle_pdf=True
    )

def set_catalogo_fields(catalogo, form):
    set_model_fields(
        catalogo,
        form,
        exclude={'id', 'producto_id', 'producto', 'comprobante_pdf'},
        date_fields=['fecha_venta', 'mes'],
        handle_pdf=True
    )

def set_factura_fields(factura, form):
    set_model_fields(
        factura,
        form,
        exclude={'id', 'empresa_id', 'empresa'},
        date_fields=['fecha_pago', 'mes']
    )

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida (actualmente solo PDF)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def guardar_comprobante(file, objeto):
    """
    Guarda el comprobante PDF para reserva, producto, contrato o catálogo.
    El nombre del archivo incluye el tipo y el id del objeto.
    """
    if file and file.filename:
        if not allowed_file(file.filename):
            return None, None, "Tipo de archivo no permitido. Solo se aceptan PDFs."

        # Validación de tamaño
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_CONTENT_LENGTH:
            return None, None, f"Archivo demasiado grande. Máximo: {MAX_CONTENT_LENGTH / (1024 * 1024):.0f} MB"

        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        tipo = objeto.__class__.__name__.lower()  # reserva, producto, contrato, catalogo
        nombre_final = f"{tipo}_{objeto.id}_{timestamp}_{filename}"
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], nombre_final)
        file.save(ruta)
        file.seek(0)
        contenido_binario = file.read()
        file.seek(0)
        return nombre_final, contenido_binario, None
    return None, None, None

def send_reset_email(user, reset_url):
    msg = Message("Restablecer contraseña", sender=app.config['MAIL_USERNAME'], recipients=[user.correo])
    msg.body = f'''Hola {user.username},

Para restablecer tu contraseña, haz clic en el siguiente enlace:

{reset_url}

Si no solicitaste este cambio, simplemente ignora este correo.

Saludos,
Equipo de Soporte
'''
    mail.send(msg)

def usuarios_de_empresa_actual():
    return Usuario.query.filter(Usuario.empresa_id == current_user.empresa_id).all()

def ruta_inicio_por_rol(usuario):
    if usuario.rol in ('master', 'admin'):
        return 'admin_panel'
    elif usuario.rol == 'controling':
        return 'controling_panel'
    elif usuario.rol == 'analista':
        return 'analista_panel'
    elif usuario.rol == 'ejecutivo':
        return 'ejecutivo_panel'
    else:
        return 'login'

def obtener_meses_anteriores(n=12, idioma='es'):
    meses = []
    today = datetime.now()
    for i in range(n):
        month = today.month - i
        year = today.year
        if month <= 0:
            month += 12
            year -= 1
        if idioma == 'es':
            meses_es = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            mes_nombre = meses_es[month - 1].capitalize()
        else:
            mes_nombre = datetime(year, month, 1).strftime('%B')
        meses.append(f"{mes_nombre} {year}")
    meses.reverse()
    return meses

def obtener_datos_reporte_detalle_ventas(selected_mes_str):
    meses_anteriores = obtener_meses_anteriores()
    try:
        month_name, year_str = selected_mes_str.split(' ')
        month_num = datetime.strptime(month_name, '%B').month
        year = int(year_str)
        start_date = datetime(year, month_num, 1)
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
    except Exception:
        today = datetime.now()
        start_date, end_date = today, today

    reservas_query = Reserva.query.join(Usuario).filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )

    reporte_data_dict = {}
    for reserva in reservas_query.all():
        ejecutivo_id = reserva.nombre_ejecutivo or ''
        correo_ejecutivo = reserva.correo_ejecutivo or ''
        rol_ejecutivo = reserva.usuario.rol
        comision_ejecutivo_porcentaje = safe_decimal(reserva.usuario.comision) / Decimal('100.0')
        total_neto = (
            reserva.hotel_neto +
            reserva.vuelo_neto +
            reserva.traslado_neto +
            reserva.seguro_neto +
            reserva.circuito_neto +
            reserva.crucero_neto +
            reserva.excursion_neto +
            reserva.paquete_neto
        )
        ganancia_bruta = reserva.precio_venta_total - total_neto
        comision_usuario = ganancia_bruta * comision_ejecutivo_porcentaje
        ganancia_neta = ganancia_bruta - comision_usuario
        bonos = reserva.bonos or 0.0

        if ejecutivo_id not in reporte_data_dict:
            reporte_data_dict[ejecutivo_id] = {
                'Ejecutivo': ejecutivo_id,
                'Correo Ejecutivo': correo_ejecutivo,
                'Rol Ejecutivo': rol_ejecutivo,
                'Total Ventas': 0.0,
                'Total Costos': 0.0,
                'Total Comisiones Ejecutivo': 0.0,
                'Total Bonos': 0.0,
                'Total Ganancia': 0.0,
                'N° de Ventas Realizadas': 0
            }
        reporte_data_dict[ejecutivo_id]['Total Ventas'] += reserva.precio_venta_total
        reporte_data_dict[ejecutivo_id]['Total Costos'] += total_neto
        reporte_data_dict[ejecutivo_id]['Total Comisiones Ejecutivo'] += comision_usuario
        reporte_data_dict[ejecutivo_id]['Total Bonos'] += bonos
        reporte_data_dict[ejecutivo_id]['Total Ganancia'] += ganancia_neta
        reporte_data_dict[ejecutivo_id]['N° de Ventas Realizadas'] += 1

    reporte_data = list(reporte_data_dict.values())

    totales = {
        'total_ventas_global': sum(r['Total Ventas'] for r in reporte_data),
        'total_costos_global': sum(r['Total Costos'] for r in reporte_data),
        'total_comisiones_global': sum(r['Total Comisiones Ejecutivo'] for r in reporte_data),
        'total_bonos_global': sum(r['Total Bonos'] for r in reporte_data),
        'total_ganancia_neta_global': sum(r['Total Ganancia'] for r in reporte_data),
        'total_ventas_realizadas_global': sum(r['N° de Ventas Realizadas'] for r in reporte_data)
    }

    return {
        'reporte_data': reporte_data,
        'totales': totales,
        'selected_mes_str': selected_mes_str,
        'meses_anteriores': meses_anteriores
    }

def obtener_datos_admin_reservas(search_query, page, per_page):
    reservas_query = Reserva.query

    if search_query:
        reservas_query = reservas_query.filter(
            db.or_(
                Reserva.producto.ilike(f'%{search_query}%'),
                Reserva.nombre_pasajero.ilike(f'%{search_query}%'),
                Reserva.destino.ilike(f'%{search_query}%'),
                Reserva.nombre_ejecutivo.ilike(f'%{search_query}%'),
                Reserva.usuario.has(Usuario.username.ilike(f'%{search_query}%')),  # Buscar por username
                Reserva.usuario.has(Usuario.empresa.has(Empresa.nombre.ilike(f'%{search_query}%')))  # Buscar por nombre de empresa
            )
        )

    reservas_paginated = reservas_query.paginate(page=page, per_page=per_page, error_out=False)
    reservas = reservas_paginated.items
    return {
        'reservas': reservas,
        'pagination': reservas_paginated,
        'search_query': search_query
    }

def obtener_datos_control_gestion_clientes(ejecutivo_id, rango_fechas_str):
    # Obtener ejecutivos (admin y usuario)
    ejecutivos = Usuario.query.filter(Usuario.rol.in_(['usuario', 'admin'])).order_by(Usuario.nombre).all()
    # Generar meses anteriores
    meses_anteriores = obtener_meses_anteriores()

    reservas_query = Reserva.query.join(Usuario)
    if ejecutivo_id:
        reservas_query = reservas_query.filter(Reserva.usuario_id == ejecutivo_id)
    start_date, end_date = _get_date_range(rango_fechas_str)
    reservas_query = reservas_query.filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )
    reservas = reservas_query.order_by(Reserva.fecha_venta.desc()).all()

    return {
        "reservas": reservas,
        "ejecutivo_id": ejecutivo_id,
        "rango_fechas_str": rango_fechas_str,
        "ejecutivos": ejecutivos,
        "meses_anteriores": meses_anteriores,
        "selected_ejecutivo_id": ejecutivo_id,
        "selected_rango_fechas": rango_fechas_str
    }

def obtener_datos_panel_comisiones(ejecutivo_id, rango_fechas_str):
    ejecutivos = Usuario.query.filter(Usuario.rol.in_(['usuario', 'admin'])).order_by(Usuario.nombre).all()
    meses_anteriores = obtener_meses_anteriores()

    reservas_query = Reserva.query.join(Usuario)
    if ejecutivo_id:
        reservas_query = reservas_query.filter(Reserva.usuario_id == ejecutivo_id)
    start_date, end_date = _get_date_range(rango_fechas_str)
    reservas_query = reservas_query.filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )
    reservas = reservas_query.order_by(Reserva.fecha_venta.desc()).all()

    datos_comisiones = []
    totales = {
        'precio_venta_total': 0.0,
        'hotel_neto': 0.0,
        'vuelo_neto': 0.0,
        'traslado_neto': 0.0,
        'seguro_neto': 0.0,
        'circuito_neto': 0.0,
        'crucero_neto': 0.0,
        'excursion_neto': 0.0,
        'paquete_neto': 0.0,
        'bonos': 0.0,
        'ganancia_total': 0.0,
        'comision_ejecutivo': 0.0,
        'comision_agencia': 0.0
    }

    for reserva in reservas:
        ejecutivo = reserva.nombre_ejecutivo or ''
        comision_ejecutivo, comision_agencia, ganancia_total, comision_ejecutivo_porcentaje, _ = calcular_comisiones(reserva, reserva.usuario)
        bonos = reserva.bonos or 0.0

        datos_comisiones.append({
            'reserva': reserva,
            'ejecutivo': ejecutivo,
            'precio_venta_total': reserva.precio_venta_total,
            'hotel_neto': reserva.hotel_neto,
            'vuelo_neto': reserva.vuelo_neto,
            'traslado_neto': reserva.traslado_neto,
            'seguro_neto': reserva.seguro_neto,
            'circuito_neto': reserva.circuito_neto,
            'crucero_neto': reserva.crucero_neto,
            'excursion_neto': reserva.excursion_neto,
            'paquete_neto': reserva.paquete_neto,
            'bonos': bonos,
            'ganancia_total': ganancia_total,
            'comision_ejecutivo': comision_ejecutivo,
            'comision_agencia': comision_agencia,
            'comision_ejecutivo_porcentaje': comision_ejecutivo_porcentaje * 100,
        })

        # Sumar a los totales
    totales['precio_venta_total'] += float(reserva.precio_venta_total or 0)
    totales['hotel_neto'] += float(reserva.hotel_neto or 0)
    totales['vuelo_neto'] += float(reserva.vuelo_neto or 0)
    totales['traslado_neto'] += float(reserva.traslado_neto or 0)
    totales['seguro_neto'] += float(reserva.seguro_neto or 0)
    totales['circuito_neto'] += float(reserva.circuito_neto or 0)
    totales['crucero_neto'] += float(reserva.crucero_neto or 0)
    totales['excursion_neto'] += float(reserva.excursion_neto or 0)
    totales['paquete_neto'] += float(reserva.paquete_neto or 0)
    totales['bonos'] += float(bonos or 0)
    totales['ganancia_total'] += float(ganancia_total or 0)
    totales['comision_ejecutivo'] += float(comision_ejecutivo or 0)
    totales['comision_agencia'] += float(comision_agencia or 0)

    return {
        'datos_comisiones': datos_comisiones,
        'totales': totales,
        'ejecutivo_id': ejecutivo_id,
        'rango_fechas_str': rango_fechas_str,
        'ejecutivos': ejecutivos,
        'meses_anteriores': meses_anteriores,
        'selected_ejecutivo_id': ejecutivo_id,
        'selected_rango_fechas': rango_fechas_str
    }

def obtener_datos_ranking_ejecutivos(selected_mes_str, selected_empresa_id, empresas):
    meses_anteriores = obtener_meses_anteriores()

    # Si no se especifica mes, usar el actual en formato YYYY-MM
    if not selected_mes_str:
        today = datetime.now()
        selected_mes_str = today.strftime('%Y-%m')
    # Parsear año y mes
    try:
        year, month = map(int, selected_mes_str.split('-'))
    except Exception:
        today = datetime.now()
        year, month = today.year, today.month
        selected_mes_str = today.strftime('%Y-%m')
    # Filtrar reservas por empresa y mes
    reservas_query = Reserva.query.join(Usuario)
    reservas_query = reservas_query.filter(
        db.extract('year', Reserva.fecha_venta) == year,
        db.extract('month', Reserva.fecha_venta) == month,
        Usuario.rol.in_(['ejecutivo', 'analista', 'controling'])
    )
    if selected_empresa_id and current_user.rol in ['master', 'admin']:
        reservas_query = reservas_query.filter(Usuario.empresa_id == int(selected_empresa_id))
    reservas = reservas_query.all()

    ranking_data = {}
    for reserva in reservas:
        ejecutivo = reserva.nombre_ejecutivo or (reserva.usuario.username if reserva.usuario else 'N/A')
        comision_ejecutivo, comision_agencia, ganancia_total, comision_ejecutivo_porcentaje, _ = calcular_comisiones(reserva, reserva.usuario)
        bonos = reserva.bonos or 0.0
        total_neto = (
            reserva.hotel_neto + reserva.vuelo_neto + reserva.traslado_neto + reserva.seguro_neto +
            reserva.circuito_neto + reserva.crucero_neto + reserva.excursion_neto + reserva.paquete_neto
        )
        comision_usuario = comision_ejecutivo
        ganancia_neta = ganancia_total - comision_usuario
        if ejecutivo not in ranking_data:
            ranking_data[ejecutivo] = {
                'num_ventas': 0,
                'ganancia_bruta': 0.0
            }
        ranking_data[ejecutivo]['num_ventas'] += 1
        ranking_data[ejecutivo]['ganancia_bruta'] += float(ganancia_neta or 0)

    # Convertir ranking_data a lista ordenada por ganancia_bruta
    ranking_data_list = [
        {'ejecutivo': k, 'num_ventas': v['num_ventas'], 'ganancia_bruta': v['ganancia_bruta']} for k, v in ranking_data.items()
    ]
    ranking_data_list.sort(key=lambda x: x['ganancia_bruta'], reverse=True)
    return {
        'ranking_data': ranking_data_list,
        'selected_mes_str': selected_mes_str,
        'meses_anteriores': meses_anteriores,
        'empresas': empresas,
        'selected_empresa_id': selected_empresa_id
    }
    reservas_query = reservas_query.filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )
    reservas = reservas_query.order_by(Reserva.fecha_venta.desc()).all()

    reservas_marketing = [
        {
            'destino': r.destino,
            'fecha_venta': r.fecha_venta,
            'fecha_viaje': r.fecha_viaje,
            'nombre_pasajero': r.nombre_pasajero,
            'telefono_pasajero': r.telefono_pasajero,
            'mail_pasajero': r.mail_pasajero
        }
        for r in reservas
    ]

    return {
        'reservas': reservas_marketing,
        'ejecutivo_id': ejecutivo_id,
        'rango_fechas_str': rango_fechas_str,
        'ejecutivos': ejecutivos,
        'meses_anteriores': meses_anteriores,
        'selected_ejecutivo_id': ejecutivo_id,
        'selected_rango_fechas': rango_fechas_str
    }

def calcular_comisiones(reserva, usuario):
    comision_ejecutivo_porcentaje = safe_decimal(usuario.comision) / Decimal('100.0')
    precio_venta_neto = (
        reserva.hotel_neto +
        reserva.vuelo_neto +
        reserva.traslado_neto +
        reserva.seguro_neto +
        reserva.circuito_neto +
        reserva.crucero_neto +
        reserva.excursion_neto +
        reserva.paquete_neto
    )
    ganancia_total = reserva.precio_venta_total - precio_venta_neto
    comision_ejecutivo = ganancia_total * comision_ejecutivo_porcentaje
    comision_agencia = ganancia_total - comision_ejecutivo
    return comision_ejecutivo, comision_agencia, ganancia_total, comision_ejecutivo_porcentaje, precio_venta_neto

# =====================
# RUTAS DE FLASK
# =====================
@app.template_filter('formato_miles')
def formato_miles(value):
    try:
        value = round(float(value))
        return '{:,.0f}'.format(value).replace(',', '.')
    except:
        return '0'

@app.template_filter('safe_decimal')
def safe_decimal_filter(value):
    """Filtro para manejar valores Decimal de forma segura"""
    if value is None:
        return ''
    try:
        return str(value)
    except:
        return ''

@app.template_filter('safe_date')
def safe_date_filter(value, format='%Y-%m-%d'):
    """Filtro para manejar fechas de forma segura"""
    if value is None:
        return ''
    try:
        return value.strftime(format)
    except:
        return ''

@app.route('/')
def index():
    """Ruta raíz que redirige a home"""
    return redirect(url_for('home'))

# =====================
# PÁGINA PRINCIPAL
# =====================
@app.route('/home')
def home():
    """Página principal/inicio"""
    return render_template('Pagina_principal/home.html')

@app.route('/nuestra-empresa')
def nuestra_empresa():
    """Página sobre nuestra empresa"""
    return render_template('Pagina_principal/Nuestra_empresa.html')

@app.route('/servicios')
def servicios():
    """Página de servicios"""
    return render_template('Pagina_principal/Servicios.html')

@app.route('/clientes')
def clientes():
    """Página de clientes"""
    return render_template('Pagina_principal/Clientes.html')

@app.route('/contacto')
def contacto():
    """Página de contacto"""
    return render_template('Pagina_principal/Contacto.html')

@app.route('/soporte')
def soporte():
    """Página de soporte"""
    return render_template('Pagina_principal/Soporte.html')

# =====================
# LOGIN DE USUARIOS
# =====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for(ruta_inicio_por_rol(user)))
        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/login/admin')
@login_required
@rol_required('admin', 'master', 'controling', 'analista', 'ejecutivo')
def admin_panel():
    # Configurar datos según el rol
    if current_user.rol == 'master':
        usuarios = Usuario.query.all()
        empresas = Empresa.query.all()
    elif current_user.rol == 'admin':
        usuarios = Usuario.query.filter(Usuario.username != 'mcontreras').all()
        empresas = Empresa.query.all()
    elif current_user.rol == 'controling':
        usuarios = usuarios_de_empresa_actual()
        empresas = []  # Controling no ve lista de empresas
    else:  # analista, ejecutivo
        usuarios = usuarios_de_empresa_actual()
        empresas = []
    
    # Manejar empresa seleccionada
    empresa_seleccionada = None
    if current_user.rol in ['master', 'admin']:
        empresa_id = session.get('empresa_id_seleccionada')
        if empresa_id:
            empresa_seleccionada = Empresa.query.get(empresa_id)
    elif current_user.rol in ['controling', 'analista', 'ejecutivo']:
        # Para estos roles, la empresa seleccionada es automáticamente su empresa
        empresa_seleccionada = current_user.empresa
    
    return render_template('admin_panel.html', 
                         usuarios=usuarios, 
                         empresas=empresas, 
                         empresa_seleccionada=empresa_seleccionada)

@app.route('/login/controling')
@login_required
@rol_required('controling')
def controling_panel():
    # Redirigir a admin_panel
    return redirect(url_for('admin_panel'))

@app.route('/login/analista')
@login_required
@empresa_tiene_productos_required
@rol_required('analista')
def analista_panel():
    # Redirigir a admin_panel
    return redirect(url_for('admin_panel'))

@app.route('/login/ejecutivo')
@login_required
@empresa_tiene_gestion_required
@rol_required('ejecutivo')
def ejecutivo_panel():
    # Redirigir a admin_panel
    return redirect(url_for('admin_panel'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        user = Usuario.query.filter_by(correo=email).first()
        if user:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password', token=token, _external=True)
            send_reset_email(user, reset_url)
            flash('Se ha enviado un correo electrónico con instrucciones para restablecer tu contraseña.', 'info')
        else:
            flash('No se encontró una cuenta con ese correo electrónico.', 'danger')
    return render_template('reset_password_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except:
        flash('El enlace de restablecimiento de contraseña es inválido o ha expirado.', 'danger')
        return redirect(url_for('reset_password_request'))

    if request.method == 'POST':
        password = request.form['password']
        user = Usuario.query.filter_by(correo=email).first()
        if user:
            user.password = password
            db.session.commit()
            flash('Tu contraseña ha sido actualizada.', 'success')
            return redirect(url_for('login'))
    return render_template('reset_password.html')

# =====================
# ADMIN / ADMINISTRACIÓN DE USUARIOS
# =====================
@app.route('/admin/usuarios/nuevo', methods=['GET', 'POST'])
@app.route('/admin/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling')
def usuario_form(id=None):
    usuario = Usuario.query.get(id) if id else None
    empresas = Empresa.query.all()
    
    if request.method == 'POST':
        if usuario:
            ok, msg = editar_usuario_existente(usuario, request.form, current_user)
        else:
            ok, msg = crear_usuario(request.form, current_user)
        if ok:
            flash(msg, 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash(msg, 'danger')
    
    return render_template('nuevo_usuario.html', usuario=usuario, empresas=empresas)

@app.route('/admin/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_required('admin', 'master','controling')
def eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if not puede_eliminar_usuario(usuario):
        flash('No autorizado para eliminar este usuario.', 'danger')
        return redirect(url_for('admin_panel'))
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('admin_panel'))

# =====================
# ADMIN / ADMINISTRACIÓN DE EMPRESAS
# =====================
@app.route('/admin/empresas/nueva', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master')
def nueva_empresa():
    if request.method == 'POST':
        nombre = request.form['nombre']
        tiene_gestion = request.form['tiene_gestion']
        tiene_productos = request.form['tiene_productos']
        representante = request.form['representante']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        razon_social = request.form['razon_social']
        correo = request.form['correo']
        empresa = Empresa(
            nombre=nombre,
            representante=representante,
            telefono=telefono,
            direccion=direccion,
            tiene_gestion=tiene_gestion,
            tiene_productos=tiene_productos,
            razon_social=razon_social,
            correo=correo
        )
        db.session.add(empresa)
        db.session.commit()
        flash('Empresa creada correctamente.', 'success')
        return redirect(url_for('admin_panel'))
    return render_template('nueva_empresa.html')

@app.route('/admin/empresas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master')
def editar_empresa(id):
    """Editar una empresa existente"""
    empresa = Empresa.query.get_or_404(id)
    if request.method == 'POST':
        empresa.nombre = request.form['nombre']
        empresa.representante = request.form['representante']
        empresa.telefono = request.form['telefono']
        empresa.correo = request.form['correo']
        empresa.direccion = request.form['direccion']
        empresa.razon_social = request.form['razon_social']
        empresa.tiene_gestion = request.form['tiene_gestion']
        empresa.tiene_productos = request.form['tiene_productos']
        
        db.session.commit()
        flash('Empresa actualizada correctamente.', 'success')
        return redirect(url_for('empresas_asociadas'))
    
    return render_template('nueva_empresa.html', empresa=empresa)

@app.route('/admin/empresas/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_required('admin', 'master')
def eliminar_empresa(id):
    """Eliminar una empresa"""
    empresa = Empresa.query.get_or_404(id)
    
    # Verificar si la empresa tiene usuarios asociados
    if empresa.usuarios:
        flash('No se puede eliminar la empresa porque tiene usuarios asociados.', 'danger')
        return redirect(url_for('empresas_asociadas'))
    
    # Verificar si la empresa tiene reservas asociadas
    if empresa.reservas:
        flash('No se puede eliminar la empresa porque tiene reservas asociadas.', 'danger')
        return redirect(url_for('empresas_asociadas'))
    
    db.session.delete(empresa)
    db.session.commit()
    flash('Empresa eliminada correctamente.', 'success')
    return redirect(url_for('empresas_asociadas'))

@app.route('/seleccionar_empresa', methods=['POST'])
@login_required
@rol_required('admin', 'master')
def seleccionar_empresa():
    empresa_id = request.form.get('empresa_id')
    if empresa_id:
        session['empresa_id_seleccionada'] = int(empresa_id)
        flash('Empresa seleccionada correctamente.', 'success')
    else:
        flash('Por favor selecciona una empresa.', 'danger')
    return redirect(url_for('admin_panel'))

@app.route('/admin/empresas')
@login_required
@rol_required('admin', 'master')
def empresas_asociadas():
    """Página para ver todas las empresas asociadas"""
    empresas = Empresa.query.all()
    return render_template('empresas_asociadas.html', empresas=empresas)

@app.route('/admin/contabilidad')
@login_required
@rol_required('admin', 'master')
def contabilidad_empresas():
    """Página para gestionar la contabilidad de empresas"""
    # Obtener parámetros de filtro
    mes_param = request.args.get('mes', '')
    empresa_param = request.args.get('empresa_id', '')
    
    # Obtener lista de meses anteriores (últimos 12 meses)
    fecha_actual = datetime.now()
    meses_anteriores = []
    for i in range(12):
        fecha_mes = fecha_actual - timedelta(days=30*i)
        mes_str = fecha_mes.strftime('%Y-%m')
        mes_nombre = obtener_nombre_mes(fecha_mes.month)
        meses_anteriores.append(f"{mes_str} ({mes_nombre})")
    
    # Construir consulta base
    query = Factura.query.join(Empresa)
    
    # Aplicar filtro por mes si se especifica
    selected_mes_str = mes_param
    if mes_param:
        # Extraer año y mes del parámetro
        año_mes = mes_param.split(' (')[0]
        año, mes = map(int, año_mes.split('-'))
        query = query.filter(
            db.extract('year', Factura.mes) == año,
            db.extract('month', Factura.mes) == mes
        )
    
    # Aplicar filtro por empresa si se especifica
    selected_empresa_id = empresa_param
    if empresa_param:
        query = query.filter(Factura.empresa_id == int(empresa_param))
    
    facturas = query.all()
    empresas = Empresa.query.all()
    
    return render_template('contabilidad_empresas.html', 
                         facturas=facturas, 
                         empresas=empresas,
                         meses_anteriores=meses_anteriores,
                         selected_mes_str=selected_mes_str,
                         selected_empresa_id=selected_empresa_id)

@app.route('/admin/facturas/nueva', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master')
def nueva_factura():
    """Crear una nueva factura"""
    if request.method == 'POST':
        empresa_id = request.form['empresa_id']
        mes_str = request.form['mes']  # formato YYYY-MM
        monto = safe_decimal(request.form['monto'])
        estado = request.form['estado']
        fecha_pago_str = request.form.get('fecha_pago', '').strip()
        metodo_pago = request.form.get('metodo_pago', '').strip()
        observaciones = request.form.get('observaciones', '').strip()
        
        # Convertir mes string a date (primer día del mes)
        try:
            mes_date = datetime.strptime(mes_str, '%Y-%m').date()
        except ValueError:
            flash('Formato de mes inválido.', 'danger')
            return redirect(url_for('nueva_factura'))
        
        # Convertir fecha de pago si se proporciona
        fecha_pago = None
        if fecha_pago_str:
            try:
                fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha de pago inválido.', 'danger')
                return redirect(url_for('nueva_factura'))
        
        factura = Factura(
            empresa_id=empresa_id,
            mes=mes_date,
            monto=monto,
            estado=estado,
            fecha_pago=fecha_pago,
            metodo_pago=metodo_pago,
            observaciones=observaciones
        )
        
        db.session.add(factura)
        db.session.commit()
        flash('Factura creada correctamente.', 'success')
        return redirect(url_for('contabilidad_empresas'))
    
    empresas = Empresa.query.all()
    return render_template('nueva_factura.html', empresas=empresas)

@app.route('/admin/facturas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master')
def editar_factura(id):
    """Editar una factura existente"""
    factura = Factura.query.get_or_404(id)
    
    if request.method == 'POST':
        factura.empresa_id = request.form['empresa_id']
        mes_str = request.form['mes']
        factura.monto = safe_decimal(request.form['monto'])
        factura.estado = request.form['estado']
        fecha_pago_str = request.form.get('fecha_pago', '').strip()
        factura.metodo_pago = request.form.get('metodo_pago', '').strip()
        factura.observaciones = request.form.get('observaciones', '').strip()
        
        # Convertir mes string a date
        try:
            factura.mes = datetime.strptime(mes_str, '%Y-%m').date()
        except ValueError:
            flash('Formato de mes inválido.', 'danger')
            return redirect(url_for('editar_factura', id=id))
        
        # Convertir fecha de pago si se proporciona
        if fecha_pago_str:
            try:
                factura.fecha_pago = datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha de pago inválido.', 'danger')
                return redirect(url_for('editar_factura', id=id))
        else:
            factura.fecha_pago = None
        
        db.session.commit()
        flash('Factura actualizada correctamente.', 'success')
        return redirect(url_for('contabilidad_empresas'))
    
    empresas = Empresa.query.all()
    return render_template('nueva_factura.html', factura=factura, empresas=empresas)

@app.route('/admin/facturas/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_required('admin', 'master')
def eliminar_factura(id):
    """Eliminar una factura"""
    factura = Factura.query.get_or_404(id)
    db.session.delete(factura)
    db.session.commit()
    flash('Factura eliminada correctamente.', 'success')
    return redirect(url_for('contabilidad_empresas'))

@app.route('/exportar_empresas')
@login_required
@rol_required('admin', 'master')
def exportar_empresas():
    """Exportar lista de empresas a Excel"""
    empresas = Empresa.query.all()
    
    data = [{
        'ID': e.id,
        'Nombre': e.nombre,
        'Representante': e.representante,
        'Teléfono': e.telefono,
        'Correo': e.correo,
        'Dirección': e.direccion,
        'Razón Social': e.razon_social,
        'Tiene Gestión': e.tiene_gestion,
        'Tiene Productos': e.tiene_productos,
        'Usuarios Asociados': len(e.usuarios),
        'Reservas': len(e.reservas)
    } for e in empresas]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Empresas', index=False)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'empresas_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/exportar_facturas')
@login_required
@rol_required('admin', 'master')
def exportar_facturas():
    """Exportar facturas de contabilidad a Excel con filtros aplicados"""
    mes_param = request.args.get('mes', '')
    empresa_param = request.args.get('empresa_id', '')
    
    # Construir consulta base igual que en contabilidad_empresas
    query = Factura.query.join(Empresa)
    
    # Aplicar filtro por mes si se especifica
    if mes_param and mes_param.strip():
        # Extraer año y mes del parámetro
        año_mes = mes_param.split(' (')[0]
        año, mes = map(int, año_mes.split('-'))
        query = query.filter(
            db.extract('year', Factura.mes) == año,
            db.extract('month', Factura.mes) == mes
        )
    
    # Aplicar filtro por empresa si se especifica
    if empresa_param and empresa_param.strip():
        query = query.filter(Factura.empresa_id == int(empresa_param))
    
    facturas = query.all()
    
    # Preparar datos para Excel
    data = [{
        'ID': f.id,
        'Empresa': f.empresa.nombre,
        'Mes': f.mes.strftime('%Y-%m') if f.mes else '',
        'Monto': float(f.monto) if f.monto else 0,
        'Fecha Factura': f.mes.strftime('%Y-%m-%d') if f.mes else '',
        'Estado': f.estado or '',
        'Fecha Pago': f.fecha_pago.strftime('%Y-%m-%d') if f.fecha_pago else '',
        'Método Pago': f.metodo_pago or '',
        'Observaciones': f.observaciones or ''
    } for f in facturas]
    
    # Crear archivo Excel
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Facturas', index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['Facturas']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Crear nombre de archivo descriptivo basado en filtros
    filename_parts = ['facturas']
    if mes_param and mes_param.strip():
        mes_clean = mes_param.split(' (')[0].replace('-', '_')
        filename_parts.append(f'mes_{mes_clean}')
    if empresa_param and empresa_param.strip():
        filename_parts.append(f'empresa_{empresa_param}')
    filename_parts.append(timestamp)
    filename = '_'.join(filename_parts) + '.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/exportar_reservas_admin')
@login_required
@rol_required('admin', 'master', 'controling', 'ejecutivo', 'analista')
def exportar_reservas_admin():
    """Exportar reservas con filtros aplicados desde admin_reservas"""
    empresa_param = request.args.get('empresa_id', '')
    usuario_param = request.args.get('usuario_id', '')
    fecha_venta_param = request.args.get('fecha_venta', '')
    fecha_viaje_param = request.args.get('fecha_viaje', '')
    
    # Construir consulta base igual que en admin_reservas
    query = Reserva.query.join(Usuario)
    
    # Aplicar filtros basados en el rol del usuario
    if current_user.rol in ['ejecutivo', 'analista']:
        query = query.filter(Reserva.usuario_id == current_user.id)
    elif current_user.rol == 'controling':
        query = query.filter(Usuario.empresa_id == current_user.empresa_id)
    
    # Aplicar filtros adicionales
    if empresa_param and empresa_param.strip() and current_user.rol in ['master', 'admin']:
        query = query.filter(Usuario.empresa_id == int(empresa_param))
    
    if usuario_param and usuario_param.strip() and current_user.rol in ['master', 'admin', 'controling']:
        query = query.filter(Reserva.usuario_id == int(usuario_param))
    
    if fecha_venta_param and fecha_venta_param.strip():
        query = query.filter(db.func.date(Reserva.fecha_venta) == fecha_venta_param)
    
    if fecha_viaje_param and fecha_viaje_param.strip():
        query = query.filter(db.func.date(Reserva.fecha_viaje) == fecha_viaje_param)
    
    reservas = query.order_by(Reserva.fecha_venta.desc()).all()
    
    # Preparar datos para Excel
    data = [{
        'ID': r.id,
        'Usuario': f"{r.usuario.nombre} {r.usuario.apellidos}" if r.usuario else 'Sin usuario',
        'Empresa': r.usuario.empresa.nombre if r.usuario and r.usuario.empresa else 'Sin empresa',
        'Fecha Venta': r.fecha_venta.strftime('%Y-%m-%d') if r.fecha_venta else '',
        'Fecha Viaje': r.fecha_viaje.strftime('%Y-%m-%d') if r.fecha_viaje else '',
        'Producto': r.producto or '',
        'Nombre Pasajero': r.nombre_pasajero or '',
        'Teléfono': r.telefono_pasajero or '',
        'Email': r.mail_pasajero or '',
        'Localizadores': r.localizadores or '',
        'Destino': r.destino or '',
        'Estado Pago': r.estado_pago or '',
        'Venta Cobrada': r.venta_cobrada or '',
        'Venta Emitida': r.venta_emitida or '',
        'Precio Total': float(r.precio_venta_total) if r.precio_venta_total else 0
    } for r in reservas]
    
    # Crear archivo Excel
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Reservas', index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets['Reservas']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Crear nombre de archivo descriptivo basado en filtros
    filename_parts = ['reservas']
    if empresa_param and empresa_param.strip():
        filename_parts.append(f'empresa_{empresa_param}')
    if usuario_param and usuario_param.strip():
        filename_parts.append(f'usuario_{usuario_param}')
    if fecha_venta_param and fecha_venta_param.strip():
        filename_parts.append(f'venta_{fecha_venta_param.replace("-", "_")}')
    if fecha_viaje_param and fecha_viaje_param.strip():
        filename_parts.append(f'viaje_{fecha_viaje_param.replace("-", "_")}')
    filename_parts.append(timestamp)
    filename = '_'.join(filename_parts) + '.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# =====================
# ADMIN / RESERVAS
# =====================
@app.route('/admin/reservas')
@login_required
@rol_required('admin', 'master', 'controling', 'ejecutivo', 'analista')
def admin_reservas():
    # Obtener parámetros de filtro
    empresa_param = request.args.get('empresa_id', '')
    usuario_param = request.args.get('usuario_id', '')
    fecha_venta_param = request.args.get('fecha_venta', '')
    fecha_viaje_param = request.args.get('fecha_viaje', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Construir consulta base
    query = Reserva.query.join(Usuario)
    
    # Aplicar filtros basados en el rol del usuario
    if current_user.rol in ['ejecutivo', 'analista']:
        # Solo ver sus propias reservas
        query = query.filter(Reserva.usuario_id == current_user.id)
    elif current_user.rol == 'controling':
        # Solo ver reservas de su empresa
        query = query.filter(Usuario.empresa_id == current_user.empresa_id)
    
    # Aplicar filtros adicionales
    selected_empresa_id = empresa_param
    if empresa_param and current_user.rol in ['master', 'admin']:
        query = query.filter(Usuario.empresa_id == int(empresa_param))
    
    selected_usuario_id = usuario_param
    if usuario_param and current_user.rol in ['master', 'admin', 'controling']:
        query = query.filter(Reserva.usuario_id == int(usuario_param))
    
    selected_fecha_venta = fecha_venta_param
    if fecha_venta_param:
        # fecha_venta_param viene como 'YYYY-MM' del input type=month
        year, month = map(int, fecha_venta_param.split('-'))
        query = query.filter(db.extract('year', Reserva.fecha_venta) == year,
                             db.extract('month', Reserva.fecha_venta) == month)

    selected_fecha_viaje = fecha_viaje_param
    if fecha_viaje_param:
        # fecha_viaje_param viene como 'YYYY-MM' del input type=month
        year, month = map(int, fecha_viaje_param.split('-'))
        query = query.filter(db.extract('year', Reserva.fecha_viaje) == year,
                             db.extract('month', Reserva.fecha_viaje) == month)
    
    # Obtener datos para los filtros
    empresas = []
    usuarios = []
    
    if current_user.rol in ['master', 'admin']:
        empresas = Empresa.query.all()
        usuarios = Usuario.query.order_by(Usuario.nombre, Usuario.apellidos).all()
    elif current_user.rol == 'controling':
        usuarios = Usuario.query.filter(Usuario.empresa_id == current_user.empresa_id).order_by(Usuario.nombre, Usuario.apellidos).all()
    
    # Paginar resultados
    reservas = query.order_by(Reserva.fecha_venta.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin_reservas.html', 
                         reservas=reservas,
                         empresas=empresas,
                         usuarios=usuarios,
                         selected_empresa_id=selected_empresa_id,
                         selected_usuario_id=selected_usuario_id,
                         selected_fecha_venta=selected_fecha_venta,
                         selected_fecha_viaje=selected_fecha_viaje)

# =====================
# ADMIN / GESTION
# =====================
@app.route('/control_gestion_clientes')
@login_required
@rol_required('admin', 'master')
def control_gestion_clientes():
    ejecutivo_id = request.args.get('ejecutivo_id', type=int)
    rango_fechas_str = request.args.get('rango_fechas', 'ultimos_30_dias')
    contexto = obtener_datos_control_gestion_clientes(ejecutivo_id, rango_fechas_str)
    return render_template('control_gestion_clientes.html', **contexto)

@app.route('/panel_comisiones')
@login_required
@rol_required('admin', 'master')
def panel_comisiones():
    ejecutivo_id = request.args.get('ejecutivo_id', type=int)
    rango_fechas_str = request.args.get('rango_fechas', 'ultimos_30_dias')
    contexto = obtener_datos_panel_comisiones(ejecutivo_id, rango_fechas_str)
    return render_template('panel_comisiones.html', **contexto)

@app.route('/ranking_ejecutivos')
@login_required
@rol_required('admin', 'master')
def ranking_ejecutivos():
    selected_mes_str = request.args.get('mes', '')
    selected_empresa_id = request.args.get('empresa_id', '')
    empresas = Empresa.query.all()
    contexto = obtener_datos_ranking_ejecutivos(selected_mes_str, selected_empresa_id, empresas)
    return render_template('ranking_ejecutivos.html', **contexto)

@app.route('/reporte_detalle_ventas')
@login_required
@rol_required('admin', 'master', 'controling')
def reporte_detalle_ventas():
    selected_mes_str = request.args.get('mes', '')
    selected_empresa_id = request.args.get('empresa_id', '')
    empresas = Empresa.query.all()
    # Si no se especifica mes, usar el actual en formato YYYY-MM
    if not selected_mes_str:
        today = datetime.now()
        selected_mes_str = today.strftime('%Y-%m')
    # Parsear año y mes
    try:
        year, month = map(int, selected_mes_str.split('-'))
    except Exception:
        today = datetime.now()
        year, month = today.year, today.month
        selected_mes_str = today.strftime('%Y-%m')
    # Filtrar reservas por empresa y mes
    reservas_query = Reserva.query.join(Usuario)
    reservas_query = reservas_query.filter(
        db.extract('year', Reserva.fecha_venta) == year,
        db.extract('month', Reserva.fecha_venta) == month,
        Usuario.rol.in_(['ejecutivo', 'analista', 'controling'])
    )
    if selected_empresa_id and current_user.rol in ['master', 'admin']:
        reservas_query = reservas_query.filter(Usuario.empresa_id == int(selected_empresa_id))
    elif current_user.rol == 'controling':
        reservas_query = reservas_query.filter(Usuario.empresa_id == current_user.empresa_id)
    reservas = reservas_query.all()
    print(f"[DEBUG reporte_detalle_ventas] Total reservas filtradas: {len(reservas)}")
    for r in reservas:
        print(f"[DEBUG reporte_detalle_ventas] Reserva: id={r.id}, usuario_id={r.usuario_id}, nombre_ejecutivo={getattr(r, 'nombre_ejecutivo', None)}, username={(r.usuario.username if r.usuario else None)}, rol={(r.usuario.rol if r.usuario else None)}")

    # Agrupar por ejecutivo y sumar valores relevantes usando calcular_comisiones
    reporte_data_dict = {}
    for reserva in reservas:
        ejecutivo_id = reserva.nombre_ejecutivo or (reserva.usuario.username if reserva.usuario else 'N/A')
        correo_ejecutivo = reserva.correo_ejecutivo or (reserva.usuario.correo if reserva.usuario else '')
        rol_ejecutivo = reserva.usuario.rol if reserva.usuario else ''
        comision_ejecutivo, comision_agencia, ganancia_total, comision_ejecutivo_porcentaje, precio_venta_neto = calcular_comisiones(reserva, reserva.usuario)
        bonos = reserva.bonos or 0.0
        if ejecutivo_id not in reporte_data_dict:
            reporte_data_dict[ejecutivo_id] = {
                'nombre_ejecutivo': ejecutivo_id,
                'correo_ejecutivo': correo_ejecutivo,
                'rol_ejecutivo': rol_ejecutivo,
                'total_ventas': 0.0,
                'total_costos': 0.0,
                'total_comisiones': 0.0,
                'total_bonos': 0.0,
                'ganancia_neta': 0.0,
                'num_ventas': 0
            }
        reporte_data_dict[ejecutivo_id]['total_ventas'] += float(reserva.precio_venta_total or 0)
        reporte_data_dict[ejecutivo_id]['total_costos'] += float(precio_venta_neto or 0)
        reporte_data_dict[ejecutivo_id]['total_comisiones'] += float(comision_ejecutivo or 0)
        reporte_data_dict[ejecutivo_id]['total_bonos'] += float(bonos or 0)
        reporte_data_dict[ejecutivo_id]['ganancia_neta'] += float(ganancia_total or 0)
        reporte_data_dict[ejecutivo_id]['num_ventas'] += 1
    reporte_data = list(reporte_data_dict.values())
    totales = {
        'total_ventas_global': sum(r['total_ventas'] for r in reporte_data),
        'total_costos_global': sum(r['total_costos'] for r in reporte_data),
        'total_comisiones_global': sum(r['total_comisiones'] for r in reporte_data),
        'total_bonos_global': sum(r['total_bonos'] for r in reporte_data),
        'total_ganancia_neta_global': sum(r['ganancia_neta'] for r in reporte_data),
        'total_ventas_realizadas_global': sum(r['num_ventas'] for r in reporte_data)
    }
    # Meses anteriores para el filtro (últimos 12 meses)
    fecha_actual = datetime.now()
    meses_anteriores = []
    for i in range(12):
        fecha_mes = fecha_actual - timedelta(days=30*i)
        mes_str = fecha_mes.strftime('%Y-%m')
        mes_nombre = obtener_nombre_mes(fecha_mes.month)
        meses_anteriores.append(f"{mes_str} ({mes_nombre})")
    return render_template('reporte_detalle_ventas.html',
        reporte_data=reporte_data,
        totales=totales,
        selected_mes_str=selected_mes_str,
        meses_anteriores=meses_anteriores,
        empresas=empresas,
        selected_empresa_id=selected_empresa_id
    )

@app.route('/reporte_ventas_general_mensual')
@login_required
@rol_required('admin', 'master')
def reporte_ventas_general_mensual():
    selected_mes_str = request.args.get('mes', '')
    selected_empresa_id = request.args.get('empresa_id', '')
    empresas = Empresa.query.all()
    contexto = obtener_datos_reporte_ventas_general_mensual(selected_mes_str, selected_empresa_id, empresas)
    return render_template('reporte_ventas_general_mensual.html', **contexto)
def obtener_datos_reporte_ventas_general_mensual(selected_mes_str, selected_empresa_id, empresas):
    meses_anteriores = obtener_meses_anteriores()

    try:
        month_name, year_str = selected_mes_str.split(' ')
        month_num = datetime.strptime(month_name, '%B').month
        year = int(year_str)
        start_date = datetime(year, month_num, 1)
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
    except Exception:
        return {
            'ranking_data': [],
            'selected_mes_str': selected_mes_str,
            'meses_anteriores': meses_anteriores
        }

    reservas = Reserva.query.join(Usuario).filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    ).all()
    datos_comisiones = []
    ranking_data = {}
    for reserva in reservas:
        ejecutivo = reserva.nombre_ejecutivo or ''
        comision_ejecutivo, comision_agencia, ganancia_total, comision_ejecutivo_porcentaje, _ = calcular_comisiones(reserva, reserva.usuario)
        bonos = reserva.bonos or 0.0
        total_neto = (
            reserva.hotel_neto + reserva.vuelo_neto + reserva.traslado_neto + reserva.seguro_neto +
            reserva.circuito_neto + reserva.crucero_neto + reserva.excursion_neto + reserva.paquete_neto
        )
        comision_usuario = comision_ejecutivo
        ganancia_neta = ganancia_total - comision_usuario
        datos_comisiones.append({
            'reserva': reserva,
            'ejecutivo': ejecutivo,
            'precio_venta_total': reserva.precio_venta_total,
            'hotel_neto': reserva.hotel_neto,
            'vuelo_neto': reserva.vuelo_neto,
            'traslado_neto': reserva.traslado_neto,
            'seguro_neto': reserva.seguro_neto,
            'circuito_neto': reserva.circuito_neto,
            'crucero_neto': reserva.crucero_neto,
            'excursion_neto': reserva.excursion_neto,
            'paquete_neto': reserva.paquete_neto,
            'bonos': bonos,
            'ganancia_total': ganancia_total,
            'comision_ejecutivo': comision_ejecutivo,
            'comision_agencia': comision_agencia,
            'comision_ejecutivo_porcentaje': comision_ejecutivo_porcentaje * 100,
        })
        # Sumar a los totales
        if ejecutivo not in ranking_data:
            ranking_data[ejecutivo] = {
                'total_ventas': 0.0,
                'total_costos': 0.0,
                'total_comisiones': 0.0,
                'total_bonos': 0.0,
                'ganancia_neta': 0.0,
                'num_ventas': 0
            }
        ranking_data[ejecutivo]['total_ventas'] += float(reserva.precio_venta_total or 0)
        ranking_data[ejecutivo]['total_costos'] += float(total_neto or 0)
        ranking_data[ejecutivo]['total_comisiones'] += float(comision_usuario or 0)
        ranking_data[ejecutivo]['total_bonos'] += float(bonos or 0)
        ranking_data[ejecutivo]['ganancia_neta'] += float(ganancia_neta or 0)
        ranking_data[ejecutivo]['num_ventas'] += 1

    return {
        'ranking_data': ranking_data,
        'selected_mes_str': selected_mes_str,
        'meses_anteriores': meses_anteriores
    }

    # Soportar input tipo YYYY-MM (input type="month")
    try:
        if selected_mes_str and '-' in selected_mes_str:
            year, month = map(int, selected_mes_str.split('-'))
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        else:
            month_name, year_str = selected_mes_str.split(' ')
            month_num = datetime.strptime(month_name, '%B').month
            year = int(year_str)
            start_date = datetime(year, month_num, 1)
            if month_num == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
    except Exception:
        return {
            'ganancia_total_mes': 0.0,
            'comision_total_ejecutivos': 0.0,
            'comision_total_agencia': 0.0,
            'selected_mes_str': selected_mes_str,
            'meses_anteriores': meses_anteriores,
            'datos_estado_pago': [0, 0],
            'datos_venta_cobrada': [0, 0],
            'datos_venta_emitida': [0, 0],
            'empresas': empresas,
            'selected_empresa_id': selected_empresa_id
        }

    reservas_query = Reserva.query.join(Usuario).filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )
    if selected_empresa_id:
        reservas_query = reservas_query.filter(Usuario.empresa_id == int(selected_empresa_id))

    total_ventas_mes = 0.0
    total_costos_mes = 0.0
    comision_total_ejecutivos = 0.0
    comision_total_agencia = 0.0
    pagado = 0
    no_pagado = 0
    cobrada = 0
    no_cobrada = 0
    emitida = 0
    no_emitida = 0

    for reserva in reservas_query.all():
        comision_ejecutivo, comision_agencia, ganancia_total, _, _ = calcular_comisiones(reserva, reserva.usuario)
        total_neto = (
            reserva.hotel_neto +
            reserva.vuelo_neto +
            reserva.traslado_neto +
            reserva.seguro_neto +
            reserva.circuito_neto +
            reserva.crucero_neto +
            reserva.excursion_neto +
            reserva.paquete_neto
        )
        comision_usuario = comision_ejecutivo
        ganancia_neta = ganancia_total - comision_usuario

        total_ventas_mes += float(reserva.precio_venta_total or 0)
        total_costos_mes += float(total_neto or 0)
        comision_total_ejecutivos += float(comision_usuario)
        comision_total_agencia += float(ganancia_neta)

        # Estado de pago
        if (reserva.estado_pago or '').strip().lower() == 'pagado':
            pagado += 1
        else:
            no_pagado += 1
        # Venta cobrada
        if (reserva.venta_cobrada or '').strip().lower() == 'cobrada':
            cobrada += 1
        else:
            no_cobrada += 1
        # Venta emitida
        if (reserva.venta_emitida or '').strip().lower() == 'emitida':
            emitida += 1
        else:
            no_emitida += 1

    ganancia_total_mes = total_ventas_mes - total_costos_mes

    datos_estado_pago = [pagado, no_pagado]
    datos_venta_cobrada = [cobrada, no_cobrada]
    datos_venta_emitida = [emitida, no_emitida]

    return {
        'ganancia_total_mes': ganancia_total_mes,
        'comision_total_ejecutivos': comision_total_ejecutivos,
        'comision_total_agencia': comision_total_agencia,
        'selected_mes_str': selected_mes_str,
        'meses_anteriores': meses_anteriores,
        'datos_estado_pago': datos_estado_pago,
        'datos_venta_cobrada': datos_venta_cobrada,
        'datos_venta_emitida': datos_venta_emitida,
        'empresas': empresas,
        'selected_empresa_id': selected_empresa_id
    }

@app.route('/marketing')
@login_required
@rol_required('admin', 'master')
def marketing():
    ejecutivo_id = request.args.get('ejecutivo_id', type=int)
    rango_fechas_str = request.args.get('rango_fechas', 'ultimos_30_dias')
    contexto = obtener_datos_marketing(ejecutivo_id, rango_fechas_str)
    return render_template('marketing.html', **contexto)

@app.route('/estados_de_venta')
@login_required
@rol_required('admin', 'master')
def estados_de_venta():
    """Página para ver estados de venta filtrados por mes de fecha de viaje"""
    selected_mes_str = request.args.get('mes', '')
    selected_empresa_id = request.args.get('empresa_id', '')
    if not selected_mes_str:
        today = datetime.now()
        selected_mes_str = today.strftime('%Y-%m')

    # Parsear el mes seleccionado (espera formato YYYY-MM)
    try:
        year, month = map(int, selected_mes_str.split('-'))
    except Exception:
        today = datetime.now()
        year, month = today.year, today.month
        selected_mes_str = today.strftime('%Y-%m')

    # Filtrar reservas por fecha de venta (no fecha de viaje)
    reservas_query = Reserva.query.join(Usuario)
    reservas_query = reservas_query.filter(
        db.extract('year', Reserva.fecha_venta) == year,
        db.extract('month', Reserva.fecha_venta) == month
    )
    if selected_empresa_id and current_user.rol in ['master', 'admin']:
        reservas_query = reservas_query.filter(Usuario.empresa_id == int(selected_empresa_id))
    elif current_user.rol == 'controling':
        reservas_query = reservas_query.filter(Usuario.empresa_id == current_user.empresa_id)

    # Incluir ejecutivos, analistas y controling
    reservas_query = reservas_query.filter(Usuario.rol.in_(['ejecutivo', 'analista', 'controling']))

    reservas = reservas_query.all()
    print(f"[DEBUG estados_de_venta] Total reservas filtradas: {len(reservas)}")
    for r in reservas:
        print(f"[DEBUG estados_de_venta] Reserva: id={r.id}, usuario_id={r.usuario_id}, nombre_ejecutivo={getattr(r, 'nombre_ejecutivo', None)}, username={(r.usuario.username if r.usuario else None)}, rol={(r.usuario.rol if r.usuario else None)}")

    # Agrupar por ejecutivo
    resumen = {}
    for reserva in reservas:
        ejecutivo = reserva.nombre_ejecutivo or (reserva.usuario.username if reserva.usuario else 'N/A')
        comision_ejecutivo, comision_agencia, ganancia_total, _, precio_venta_neto = calcular_comisiones(reserva, reserva.usuario)
        if ejecutivo not in resumen:
            resumen[ejecutivo] = {
                'ejecutivo': ejecutivo,
                'precio_venta_total': 0.0,
                'precio_venta_neto': 0.0,
                'comision_ejecutivo': 0.0,
                'comision_agencia': 0.0,
                'num_ventas': 0
            }
        resumen[ejecutivo]['precio_venta_total'] += float(reserva.precio_venta_total or 0)
        resumen[ejecutivo]['precio_venta_neto'] += float(precio_venta_neto or 0)
        resumen[ejecutivo]['comision_ejecutivo'] += float(comision_ejecutivo or 0)
        resumen[ejecutivo]['comision_agencia'] += float(comision_agencia or 0)
        resumen[ejecutivo]['num_ventas'] += 1

    # Calcular promedio de ventas
    estados_data = []
    totales = {
        'precio_venta_total': 0.0,
        'precio_venta_neto': 0.0,
        'comision_ejecutivo': 0.0,
        'comision_agencia': 0.0,
        'num_ventas': 0
    }
    for ejecutivo, data in resumen.items():
        prom_ventas = data['precio_venta_total'] / data['num_ventas'] if data['num_ventas'] else 0
        estados_data.append({
            'ejecutivo': ejecutivo,
            'precio_venta_total': data['precio_venta_total'],
            'precio_venta_neto': data['precio_venta_neto'],
            'comision_ejecutivo': data['comision_ejecutivo'],
            'comision_agencia': data['comision_agencia'],
            'num_ventas': data['num_ventas'],
            'prom_ventas': prom_ventas
        })
        totales['precio_venta_total'] += data['precio_venta_total']
        totales['precio_venta_neto'] += data['precio_venta_neto']
        totales['comision_ejecutivo'] += data['comision_ejecutivo']
        totales['comision_agencia'] += data['comision_agencia']
        totales['num_ventas'] += data['num_ventas']

    empresas = Empresa.query.all()

    return render_template('estados_de_venta.html',
                         estados_data=estados_data,
                         totales=totales,
                         selected_mes_str=selected_mes_str,
                         empresas=empresas,
                         selected_empresa_id=selected_empresa_id)


# NUEVO ENDPOINT AGRUPADO POR AÑO Y MESES
@app.route('/balance_mensual')
@login_required
@empresa_tiene_gestion_required
def balance_mensual():
    """Mostrar balance mensual agrupado por meses del año seleccionado"""
    anio_param = request.args.get('anio', '')
    selected_empresa_id = request.args.get('empresa_id', '')

    # Obtener años disponibles (de las reservas)
    anios_disponibles = db.session.query(db.extract('year', Reserva.fecha_venta)).distinct().order_by(db.extract('year', Reserva.fecha_venta).desc()).all()
    anios_disponibles = [int(a[0]) for a in anios_disponibles if a[0]]
    anio_actual = datetime.now().year
    selected_anio = int(anio_param) if anio_param and anio_param.isdigit() else anio_actual

    # Preparar datos por mes
    balance_data = []
    for mes in range(1, 13):
        # Query de reservas del mes y año
        query = Reserva.query.join(Usuario).filter(
            db.extract('year', Reserva.fecha_venta) == selected_anio,
            db.extract('month', Reserva.fecha_venta) == mes
        )
        if selected_empresa_id:
            query = query.filter(
                Usuario.empresa_id == int(selected_empresa_id),
                Usuario.rol.in_(['ejecutivo', 'controling', 'analista'])
            )
        reservas = query.all()


        # Ingresos por agentes = suma de comisión agencia
        ingresos_agentes = 0
        egresos_comision = 0
        for r in reservas:
            comision_ejecutivo, comision_agencia, _, _, _ = calcular_comisiones(r, r.usuario)
            ingresos_agentes += float(comision_agencia or 0)
            egresos_comision += float(comision_ejecutivo or 0)

        # Los siguientes campos pueden ser editables y persistidos en BD, pero aquí los dejamos en 0 por defecto
        ingresos_externos = 0
        egresos_administracion = 0
        otros_egresos = 0

        mes_nombre = obtener_nombre_mes(mes)
        balance_data.append({
            'numero': mes,
            'nombre': mes_nombre,
            'ingresos_agentes': ingresos_agentes,
            'ingresos_externos': ingresos_externos,
            'egresos_comision': egresos_comision,
            'egresos_administracion': egresos_administracion,
            'otros_egresos': otros_egresos
        })

    empresas = Empresa.query.all()
    return render_template('balance_mensual.html',
        balance_data=balance_data,
        anios_disponibles=anios_disponibles,
        selected_anio=selected_anio,
        empresas=empresas,
        selected_empresa_id=selected_empresa_id
    )

@app.route('/liquidaciones')
@login_required
@rol_required('admin', 'master')
def liquidaciones():
    """Mostrar liquidaciones filtradas por ejecutivo y fecha de venta"""
    # Obtener parámetros
    mes_param = request.args.get('mes', '')
    ejecutivo_param = request.args.get('ejecutivo', '')
    selected_empresa_id = request.args.get('empresa_id', '')
    
    # Obtener lista de meses anteriores
    fecha_actual = datetime.now()
    meses_anteriores = []
    for i in range(12):
        fecha_mes = fecha_actual - timedelta(days=30*i)
        mes_str = fecha_mes.strftime('%Y-%m')
        mes_nombre = obtener_nombre_mes(fecha_mes.month)
        meses_anteriores.append(f"{mes_str} ({mes_nombre})")
    
    # Si no se especifica mes, usar el actual
    selected_mes_str = mes_param if mes_param else meses_anteriores[0]
    
    # Extraer año y mes
    año_mes = selected_mes_str.split(' (')[0]
    año, mes = map(int, año_mes.split('-'))
    
    # Obtener ejecutivos disponibles (usuarios que han hecho reservas)
    ejecutivos_disponibles = db.session.query(
        Usuario.nombre, Usuario.apellidos
    ).join(Reserva).filter(
        Usuario.nombre.isnot(None),
        Usuario.apellidos.isnot(None)
    ).distinct().order_by(Usuario.nombre, Usuario.apellidos).all()
    
    ejecutivos_disponibles = [f"{ej[0]} {ej[1]}" for ej in ejecutivos_disponibles]
    
    # Construir consulta base
    query = Reserva.query.join(Usuario).filter(
        db.extract('year', Reserva.fecha_venta) == año,
        db.extract('month', Reserva.fecha_venta) == mes
    )
    # Filtro por empresa si se selecciona
    if selected_empresa_id:
        query = query.filter(
            Usuario.empresa_id == int(selected_empresa_id),
            Usuario.rol.in_(['ejecutivo', 'controling', 'analista'])
        )
    # Filtrar por ejecutivo si se especifica
    selected_ejecutivo = ejecutivo_param
    if selected_ejecutivo:
        partes_nombre = selected_ejecutivo.split(' ', 1)
        if len(partes_nombre) == 2:
            nombre, apellido = partes_nombre
            query = query.filter(
                Usuario.nombre == nombre,
                Usuario.apellidos == apellido
            )
    reservas = query.all()
    
    # Procesar datos
    # Agrupar reservas por ejecutivo y sumar valores relevantes
    ejecutivos_dict = {}
    totales = {
        'precio_venta_total': 0,
        'precio_venta_neto': 0,
        'comision_ejecutivo': 0,
        'comision_agencia': 0
    }
    for reserva in reservas:
        ejecutivo_nombre_completo = f"{reserva.usuario.nombre} {reserva.usuario.apellidos}"
        comision_ejecutivo, comision_agencia, ganancia_total, _, _ = calcular_comisiones(reserva, reserva.usuario)
        if ejecutivo_nombre_completo not in ejecutivos_dict:
            ejecutivos_dict[ejecutivo_nombre_completo] = {
                'ejecutivo': ejecutivo_nombre_completo,
                'precio_venta_total': 0,
                'precio_venta_neto': 0,
                'comision_ejecutivo': 0,
                'comision_agencia': 0,
                'porcentaje_comision': getattr(reserva.usuario, 'comision', 0),
                'sueldo': getattr(reserva.usuario, 'sueldo', 0),
                'estado_pago': reserva.estado_pago or 'No definido',
                'bonos': 0,
                'descuentos': 0,
                'total_pagar': 0
            }
        ejecutivos_dict[ejecutivo_nombre_completo]['precio_venta_total'] += reserva.precio_venta_total or 0
        ejecutivos_dict[ejecutivo_nombre_completo]['precio_venta_neto'] += reserva.precio_venta_neto or 0
        ejecutivos_dict[ejecutivo_nombre_completo]['comision_ejecutivo'] += comision_ejecutivo or 0
        ejecutivos_dict[ejecutivo_nombre_completo]['comision_agencia'] += comision_agencia or 0
        # Si quieres sumar bonos y descuentos, deberías tenerlos en la reserva o en otro lado
        # ejecutivos_dict[ejecutivo_nombre_completo]['bonos'] += reserva.bonos or 0
        # ejecutivos_dict[ejecutivo_nombre_completo]['descuentos'] += reserva.descuentos or 0
        # El estado de pago podría ser 'Pagado' si alguna reserva está pagada
        if reserva.estado_pago == 'Pagado':
            ejecutivos_dict[ejecutivo_nombre_completo]['estado_pago'] = 'Pagado'
    # Calcular total a pagar por ejecutivo
    for data in ejecutivos_dict.values():
        data['total_pagar'] = (
            (data['comision_ejecutivo'] or 0)
            + (data['bonos'] or 0)
            + (data['sueldo'] or 0)
            - (data['descuentos'] or 0)
        )
        totales['precio_venta_total'] += data['precio_venta_total']
        totales['precio_venta_neto'] += data['precio_venta_neto']
        totales['comision_ejecutivo'] += data['comision_ejecutivo']
        totales['comision_agencia'] += data['comision_agencia']
    liquidaciones_data = list(ejecutivos_dict.values())
    
    empresas = Empresa.query.all()
    return render_template('liquidaciones.html', 
                         estados_data=liquidaciones_data,
                         totales=totales,
                         selected_mes_str=selected_mes_str,
                         selected_ejecutivo=selected_ejecutivo,
                         meses_anteriores=meses_anteriores,
                         ejecutivos_disponibles=ejecutivos_disponibles,
                         # ejecutivos_resumen eliminado porque ya no se usa
                         empresas=empresas,
                         selected_empresa_id=selected_empresa_id)

# =====================
# RESERVAS
# =====================
@app.route('/reservas', methods=['GET', 'POST'])
@login_required
def gestionar_reservas():
    if request.method == 'POST':
        reserva_id = request.form.get('reserva_id')
        file = request.files.get('archivo_pdf')

        if reserva_id:
            reserva = Reserva.query.get(reserva_id)
            if not reserva or not puede_editar_reserva(reserva):
                flash('No autorizado.', 'danger')
                return redirect(url_for('gestionar_reservas'))

            set_reserva_fields(reserva, request.form)

            nombre_archivo, contenido_pdf, error_mensaje = guardar_comprobante(file, reserva)
            if error_mensaje:
                flash(error_mensaje, 'danger')
            elif nombre_archivo:
                reserva.comprobante_venta = nombre_archivo
                reserva.comprobante_pdf = contenido_pdf
            # Si no se subió un nuevo archivo, mantener los valores actuales
            elif not file or not file.filename:
                # No hacer nada, se mantienen los valores actuales
                pass

        else:
            nueva_reserva = Reserva(
                usuario_id=current_user.id
            )
            db.session.add(nueva_reserva)
            db.session.flush()  # Asegura que nueva_reserva tenga un ID asignado
            set_reserva_fields(nueva_reserva, request.form)

            nombre_archivo, contenido_pdf, error_mensaje = guardar_comprobante(file, nueva_reserva)
            if error_mensaje:
                flash(error_mensaje, 'danger')
            elif nombre_archivo and contenido_pdf:
                nueva_reserva.comprobante_venta = nombre_archivo
                nueva_reserva.comprobante_pdf = contenido_pdf

        db.session.commit()
        flash('Reserva guardada.', 'success')
        return redirect(url_for('gestionar_reservas'))

    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de elementos por página

    reservas_query = Reserva.query

    if current_user.rol not in ('admin', 'master'):
        reservas_query = reservas_query.filter_by(usuario_id=current_user.id)

    if search_query:
        reservas_query = reservas_query.filter(
            db.or_(
                Reserva.producto.ilike(f'%{search_query}%'),
                Reserva.nombre_pasajero.ilike(f'%{search_query}%'),
                Reserva.destino.ilike(f'%{search_query}%'),
                Reserva.nombre_ejecutivo.ilike(f'%{search_query}%')
            )
        )

    reservas_paginated = reservas_query.paginate(page=page, per_page=per_page, error_out=False)
    reservas = reservas_paginated.items

    editar_id = request.args.get('editar')
    editar_reserva = None
    if editar_id:
        reserva_a_editar = Reserva.query.get(int(editar_id))
        if reserva_a_editar and puede_editar_reserva(reserva_a_editar):
            # Recalcular y asignar valores calculados antes de mostrar el formulario
            if reserva_a_editar.usuario:
                comision_ejecutivo, comision_agencia, ganancia_total, _, precio_venta_neto = calcular_comisiones(reserva_a_editar, reserva_a_editar.usuario)
                reserva_a_editar.precio_venta_neto = precio_venta_neto
                reserva_a_editar.comision_ejecutivo = comision_ejecutivo
                reserva_a_editar.comision_agencia = comision_agencia
                reserva_a_editar.ganancia_total = ganancia_total
            editar_reserva = reserva_a_editar

    return render_template(
        'reservas.html',
        reservas=reservas,
        editar_reserva=editar_reserva,
        pagination=reservas_paginated,
        search_query=search_query
    )

@app.route('/pdf/<int:reserva_id>')
@login_required
def ver_pdf_db(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    if not puede_editar_reserva(reserva):
        flash('No autorizado.', 'danger')
        return redirect(url_for('gestionar_reservas'))
    if reserva.comprobante_pdf:
        return send_file(
            io.BytesIO(reserva.comprobante_pdf),
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f"{reserva.id}_comprobante.pdf"
        )
    else:
        flash('No hay comprobante PDF guardado en la base de datos.', 'warning')
        return redirect(url_for('gestionar_reservas'))

@app.route('/comprobante/<int:reserva_id>')
@login_required
def descargar_comprobante(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)

    # Verifica permisos: solo admin/master o dueño de la reserva
    if current_user.rol not in ('admin', 'master') and reserva.usuario_id != current_user.id:
        flash('No autorizado para ver este comprobante.', 'danger')
        return redirect(url_for('gestionar_reservas'))

    if not reserva.comprobante_pdf:
        flash('No hay comprobante para esta reserva.', 'warning')
        return redirect(url_for('gestionar_reservas'))

    return Response(
        reserva.comprobante_pdf,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"inline; filename=comprobante_{reserva.id}.pdf"}
    )

@app.route('/reservas/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_reserva(id):
    reserva = Reserva.query.get_or_404(id)
    if not puede_editar_reserva(reserva):
        flash('No autorizado.', 'danger')
        return redirect(url_for('gestionar_reservas'))

    # Eliminar el archivo de comprobante si existe
    if reserva.comprobante_venta:
        ruta_comprobante = os.path.join(app.config['UPLOAD_FOLDER'], reserva.comprobante_venta)
        if os.path.exists(ruta_comprobante):
            os.remove(ruta_comprobante)
            flash(f'Comprobante {reserva.comprobante_venta} eliminado del servidor.', 'info')

    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva eliminada.', 'success')
    return redirect(url_for('admin_reservas'))

@app.route('/reservas_usuarios')
@login_required
def reservas_usuarios():
    # Generar lista de meses anteriores (12 meses)
    meses_anteriores = obtener_meses_anteriores()

    # Obtener mes seleccionado
    selected_mes_str = request.args.get('mes', meses_anteriores[-1] if meses_anteriores else '')
    today = datetime.now()
    try:
        start_date, end_date = _get_date_range(selected_mes_str)
    except Exception:
        start_date, end_date = today, today

    # Filtrar reservas por usuario y mes
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de elementos por página

    reservas_query = Reserva.query.filter(
        Reserva.usuario_id == current_user.id,
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )

    reservas_paginated = reservas_query.paginate(page=page, per_page=per_page, error_out=False)
    reservas = reservas_paginated.items

    # Calcular totales
    total_ventas = sum(r.precio_venta_total or 0 for r in reservas)
    total_comision_ejecutivo = sum(r.comision_ejecutivo or 0 for r in reservas)

    return render_template(
        'reservas_usuarios.html',
        reservas=reservas,
        meses_anteriores=meses_anteriores,
        selected_mes_str=selected_mes_str,
        total_ventas=total_ventas,
        total_comision_ejecutivo=total_comision_ejecutivo,
        pagination=reservas_paginated
    )
# =====================
# PROVEEDORES
# =====================
@app.route('/proveedores')
@login_required
@rol_required('admin', 'master', 'controling')
@empresa_tiene_productos_required
def proveedores():
    """Página para ver todos los proveedores"""
    if current_user.rol == 'controling':
        # Controling solo ve proveedores de su empresa
        proveedores = Proveedor.query.filter_by(empresa_id=current_user.empresa_id).all()
    else:
        # Admin y master ven todos los proveedores
        proveedores = Proveedor.query.all()
    
    return render_template('proveedores.html', proveedores=proveedores)

@app.route('/proveedores/nuevo', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling')
@empresa_tiene_productos_required
def nuevo_proveedor():
    """Crear un nuevo proveedor"""
    if request.method == 'POST':
        # Determinar empresa_id según el rol
        if current_user.rol == 'controling':
            empresa_id = current_user.empresa_id
        else:
            empresa_id = request.form.get('empresa_id')
            if not empresa_id:
                flash('Debe seleccionar una empresa.', 'danger')
                return redirect(url_for('nuevo_proveedor'))
        
        proveedor = Proveedor(
            nombre=request.form['nombre'].strip(),
            pais_ciudad=request.form.get('pais_ciudad', '').strip(),
            direccion=request.form.get('direccion', '').strip(),
            tipo_proveedor=request.form.get('tipo_proveedor', '').strip(),
            servicio=request.form.get('servicio', '').strip(),
            contacto_principal_nombre=request.form.get('contacto_principal_nombre', '').strip(),
            contacto_principal_email=request.form.get('contacto_principal_email', '').strip(),
            contacto_principal_telefono=request.form.get('contacto_principal_telefono', '').strip(),
            condiciones_comerciales=request.form.get('condiciones_comerciales', '').strip(),
            donde_opera=request.form.get('donde_opera', '').strip(),
            estado=request.form.get('estado', 'Activo').strip(),
            empresa_id=empresa_id
        )
        
        # Procesar fechas
        if request.form.get('ultima_negociacion'):
            try:
                proveedor.ultima_negociacion = datetime.strptime(
                    request.form['ultima_negociacion'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de última negociación inválido.', 'danger')
                return redirect(url_for('nuevo_proveedor'))
        
        if request.form.get('fecha_vigencia'):
            try:
                proveedor.fecha_vigencia = datetime.strptime(
                    request.form['fecha_vigencia'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de vigencia inválido.', 'danger')
                return redirect(url_for('nuevo_proveedor'))
        
        db.session.add(proveedor)
        db.session.commit()
        flash('Proveedor creado correctamente.', 'success')
        return redirect(url_for('proveedores'))
    
    # Para GET request
    empresas = []
    if current_user.rol in ['admin', 'master']:
        empresas = Empresa.query.filter_by(tiene_productos=True).all()
    
    return render_template('nuevo_proveedor.html', empresas=empresas)

@app.route('/proveedores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling')
@empresa_tiene_productos_required
def editar_proveedor(id):
    """Editar un proveedor existente"""
    proveedor = Proveedor.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para editar este proveedor.', 'danger')
        return redirect(url_for('proveedores'))
    
    if request.method == 'POST':
        proveedor.nombre = request.form['nombre'].strip()
        proveedor.pais_ciudad = request.form.get('pais_ciudad', '').strip()
        proveedor.direccion = request.form.get('direccion', '').strip()
        proveedor.tipo_proveedor = request.form.get('tipo_proveedor', '').strip()
        proveedor.servicio = request.form.get('servicio', '').strip()
        proveedor.contacto_principal_nombre = request.form.get('contacto_principal_nombre', '').strip()
        proveedor.contacto_principal_email = request.form.get('contacto_principal_email', '').strip()
        proveedor.contacto_principal_telefono = request.form.get('contacto_principal_telefono', '').strip()
        proveedor.condiciones_comerciales = request.form.get('condiciones_comerciales', '').strip()
        proveedor.donde_opera = request.form.get('donde_opera', '').strip()
        proveedor.estado = request.form.get('estado', 'Activo').strip()
        
        # Solo admin y master pueden cambiar la empresa
        if current_user.rol in ['admin', 'master']:
            empresa_id = request.form.get('empresa_id')
            if empresa_id:
                proveedor.empresa_id = empresa_id
        
        # Procesar fechas
        if request.form.get('ultima_negociacion'):
            try:
                proveedor.ultima_negociacion = datetime.strptime(
                    request.form['ultima_negociacion'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de última negociación inválido.', 'danger')
                return redirect(url_for('editar_proveedor', id=id))
        else:
            proveedor.ultima_negociacion = None
        
        if request.form.get('fecha_vigencia'):
            try:
                proveedor.fecha_vigencia = datetime.strptime(
                    request.form['fecha_vigencia'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de vigencia inválido.', 'danger')
                return redirect(url_for('editar_proveedor', id=id))
        else:
            proveedor.fecha_vigencia = None
        
        db.session.commit()
        flash('Proveedor actualizado correctamente.', 'success')
        return redirect(url_for('proveedores'))
    
    # Para GET request
    empresas = []
    if current_user.rol in ['admin', 'master']:
        empresas = Empresa.query.filter_by(tiene_productos=True).all()
    
    return render_template('nuevo_proveedor.html', proveedor=proveedor, empresas=empresas)

@app.route('/proveedores/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_required('admin', 'master', 'controling')
@empresa_tiene_productos_required
def eliminar_proveedor(id):
    """Eliminar un proveedor"""
    proveedor = Proveedor.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para eliminar este proveedor.', 'danger')
        return redirect(url_for('proveedores'))
    
    # Verificar si el proveedor tiene contratos asociados
    if hasattr(proveedor, 'contratos') and proveedor.contratos:
        flash('No se puede eliminar el proveedor porque tiene contratos asociados.', 'danger')
        return redirect(url_for('proveedores'))
    
    # Verificar si el proveedor tiene catálogos asociados
    if hasattr(proveedor, 'catalogos') and proveedor.catalogos:
        flash('No se puede eliminar el proveedor porque tiene catálogos asociados.', 'danger')
        return redirect(url_for('proveedores'))
    
    db.session.delete(proveedor)
    db.session.commit()
    flash('Proveedor eliminado correctamente.', 'success')
    return redirect(url_for('proveedores'))

@app.route('/exportar_proveedores')
@login_required
@rol_required('admin', 'master', 'controling')
@empresa_tiene_productos_required
def exportar_proveedores():
    """Exportar lista de proveedores a Excel"""
    if current_user.rol == 'controling':
        # Controling solo exporta proveedores de su empresa
        proveedores = Proveedor.query.filter_by(empresa_id=current_user.empresa_id).all()
    else:
        # Admin y master exportan todos los proveedores
        proveedores = Proveedor.query.all()
    
    data = [{
        'ID': p.id,
        'Nombre': p.nombre,
        'País/Ciudad': p.pais_ciudad,
        'Dirección': p.direccion,
        'Tipo de Proveedor': p.tipo_proveedor,
        'Servicio': p.servicio,
        'Contacto Principal': p.contacto_principal_nombre,
        'Email Contacto': p.contacto_principal_email,
        'Teléfono Contacto': p.contacto_principal_telefono,
        'Condiciones Comerciales': p.condiciones_comerciales,
        'Donde Opera': p.donde_opera,
        'Última Negociación': p.ultima_negociacion.strftime('%Y-%m-%d') if p.ultima_negociacion else '',
        'Fecha Vigencia': p.fecha_vigencia.strftime('%Y-%m-%d') if p.fecha_vigencia else '',
        'Estado': p.estado,
        'Empresa': p.empresa.nombre if p.empresa else 'N/A'
    } for p in proveedores]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Proveedores', index=False)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'proveedores_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# =====================
# CONTRATOS
# =====================
@app.route('/contratos')
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def contratos():
    """Página para ver todos los contratos"""
    if current_user.rol == 'controling':
        # Controling solo ve contratos de proveedores de su empresa
        contratos = Contrato.query.join(Proveedor).filter(Proveedor.empresa_id == current_user.empresa_id).all()
    else:
        # Admin, master y analista ven todos los contratos
        contratos = Contrato.query.all()
    
    return render_template('contratos.html', contratos=contratos)

@app.route('/contratos/nuevo', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def nuevo_contrato():
    """Crear un nuevo contrato"""
    if request.method == 'POST':
        proveedor_id = request.form.get('proveedor_id')
        if not proveedor_id:
            flash('Debe seleccionar un proveedor.', 'danger')
            return redirect(url_for('nuevo_contrato'))
        
        # Verificar que el proveedor pertenece a la empresa del usuario (para controling)
        proveedor = Proveedor.query.get(proveedor_id)
        if not proveedor:
            flash('Proveedor no encontrado.', 'danger')
            return redirect(url_for('nuevo_contrato'))
        
        if current_user.rol == 'controling' and proveedor.empresa_id != current_user.empresa_id:
            flash('No autorizado para crear contratos con este proveedor.', 'danger')
            return redirect(url_for('nuevo_contrato'))
        
        contrato = Contrato(
            nombre=request.form['nombre'].strip(),
            descripcion=request.form.get('descripcion', '').strip(),
            estado=request.form.get('estado', 'Activo').strip(),
            condiciones=request.form.get('condiciones', '').strip(),
            proveedor_id=proveedor_id
        )
        
        # Procesar fechas
        if request.form.get('fecha_inicio'):
            try:
                contrato.fecha_inicio = datetime.strptime(
                    request.form['fecha_inicio'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de inicio inválido.', 'danger')
                return redirect(url_for('nuevo_contrato'))
        
        if request.form.get('fecha_fin'):
            try:
                contrato.fecha_fin = datetime.strptime(
                    request.form['fecha_fin'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de fin inválido.', 'danger')
                return redirect(url_for('nuevo_contrato'))
        
        db.session.add(contrato)
        db.session.flush()  # Para obtener el ID
        
        # Manejar archivo PDF
        file = request.files.get('archivo_pdf')
        if file and file.filename:
            nombre_archivo, contenido_pdf, error_mensaje = guardar_comprobante(file, contrato)
            if error_mensaje:
                flash(error_mensaje, 'danger')
                return redirect(url_for('nuevo_contrato'))
            elif nombre_archivo:
                contrato.comprobante_venta = nombre_archivo
                contrato.comprobante_pdf = contenido_pdf
        
        db.session.commit()
        flash('Contrato creado correctamente.', 'success')
        return redirect(url_for('contratos'))
    
    # Para GET request - obtener proveedores disponibles
    if current_user.rol == 'controling':
        proveedores = Proveedor.query.filter_by(empresa_id=current_user.empresa_id).all()
    else:
        proveedores = Proveedor.query.all()
    
    return render_template('nuevo_contrato.html', proveedores=proveedores)

@app.route('/contratos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def editar_contrato(id):
    """Editar un contrato existente"""
    contrato = Contrato.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and contrato.proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para editar este contrato.', 'danger')
        return redirect(url_for('contratos'))
    
    if request.method == 'POST':
        proveedor_id = request.form.get('proveedor_id')
        if not proveedor_id:
            flash('Debe seleccionar un proveedor.', 'danger')
            return redirect(url_for('editar_contrato', id=id))
        
        # Verificar que el proveedor pertenece a la empresa del usuario (para controling)
        proveedor = Proveedor.query.get(proveedor_id)
        if current_user.rol == 'controling' and proveedor.empresa_id != current_user.empresa_id:
            flash('No autorizado para asignar este proveedor.', 'danger')
            return redirect(url_for('editar_contrato', id=id))
        
        contrato.nombre = request.form['nombre'].strip()
        contrato.descripcion = request.form.get('descripcion', '').strip()
        contrato.estado = request.form.get('estado', 'Activo').strip()
        contrato.condiciones = request.form.get('condiciones', '').strip()
        contrato.proveedor_id = proveedor_id
        
        # Procesar fechas
        if request.form.get('fecha_inicio'):
            try:
                contrato.fecha_inicio = datetime.strptime(
                    request.form['fecha_inicio'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de inicio inválido.', 'danger')
                return redirect(url_for('editar_contrato', id=id))
        else:
            contrato.fecha_inicio = None
        
        if request.form.get('fecha_fin'):
            try:
                contrato.fecha_fin = datetime.strptime(
                    request.form['fecha_fin'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de fin inválido.', 'danger')
                return redirect(url_for('editar_contrato', id=id))
        else:
            contrato.fecha_fin = None
        
        # Manejar archivo PDF
        file = request.files.get('archivo_pdf')
        if file and file.filename:
            nombre_archivo, contenido_pdf, error_mensaje = guardar_comprobante(file, contrato)
            if error_mensaje:
                flash(error_mensaje, 'danger')
                return redirect(url_for('editar_contrato', id=id))
            elif nombre_archivo:
                contrato.comprobante_venta = nombre_archivo
                contrato.comprobante_pdf = contenido_pdf
        
        db.session.commit()
        flash('Contrato actualizado correctamente.', 'success')
        return redirect(url_for('contratos'))
    
    # Para GET request - obtener proveedores disponibles
    if current_user.rol == 'controling':
        proveedores = Proveedor.query.filter_by(empresa_id=current_user.empresa_id).all()
    else:
        proveedores = Proveedor.query.all()
    
    return render_template('nuevo_contrato.html', contrato=contrato, proveedores=proveedores)

@app.route('/contratos/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def eliminar_contrato(id):
    """Eliminar un contrato"""
    contrato = Contrato.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and contrato.proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para eliminar este contrato.', 'danger')
        return redirect(url_for('contratos'))
    
    # Eliminar el archivo de comprobante si existe
    if contrato.comprobante_venta:
        ruta_comprobante = os.path.join(app.config['UPLOAD_FOLDER'], contrato.comprobante_venta)
        if os.path.exists(ruta_comprobante):
            try:
                os.remove(ruta_comprobante)
            except Exception as e:
                print(f"Error al eliminar archivo: {e}")
    
    db.session.delete(contrato)
    db.session.commit()
    flash('Contrato eliminado correctamente.', 'success')
    return redirect(url_for('contratos'))

@app.route('/exportar_contratos')
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def exportar_contratos():
    """Exportar lista de contratos a Excel"""
    if current_user.rol == 'controling':
        contratos = Contrato.query.join(Proveedor).filter(Proveedor.empresa_id == current_user.empresa_id).all()
    else:
        contratos = Contrato.query.all()
    
    data = [{
        'ID': c.id,
        'Nombre': c.nombre,
        'Descripción': c.descripcion,
        'Fecha Inicio': c.fecha_inicio.strftime('%Y-%m-%d') if c.fecha_inicio else '',
        'Fecha Fin': c.fecha_fin.strftime('%Y-%m-%d') if c.fecha_fin else '',
        'Estado': c.estado,
        'Condiciones': c.condiciones,
        'Proveedor': c.proveedor.nombre if c.proveedor else 'N/A',
        'Empresa': c.proveedor.empresa.nombre if c.proveedor and c.proveedor.empresa else 'N/A',
        'Tiene Comprobante': 'Sí' if c.comprobante_pdf else 'No'
    } for c in contratos]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Contratos', index=False)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'contratos_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# =====================
# CATALOGOS
# =====================
@app.route('/catalogos')
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def catalogos():
    """Página para ver todos los catálogos"""
    if current_user.rol == 'controling':
        # Controling solo ve catálogos de proveedores de su empresa
        catalogos = Catalogo.query.join(Proveedor).filter(Proveedor.empresa_id == current_user.empresa_id).all()
    else:
        # Admin, master y analista ven todos los catálogos
        catalogos = Catalogo.query.all()
    
    return render_template('catalogos.html', catalogos=catalogos)

@app.route('/catalogos/nuevo', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def nuevo_catalogo():
    """Crear un nuevo catálogo"""
    if request.method == 'POST':
        proveedor_id = request.form.get('proveedor_id')
        if not proveedor_id:
            flash('Debe seleccionar un proveedor.', 'danger')
            return redirect(url_for('nuevo_catalogo'))
        
        # Verificar que el proveedor pertenece a la empresa del usuario (para controling)
        proveedor = Proveedor.query.get(proveedor_id)
        if not proveedor:
            flash('Proveedor no encontrado.', 'danger')
            return redirect(url_for('nuevo_catalogo'))
        
        if current_user.rol == 'controling' and proveedor.empresa_id != current_user.empresa_id:
            flash('No autorizado para crear catálogos con este proveedor.', 'danger')
            return redirect(url_for('nuevo_catalogo'))
        
        catalogo = Catalogo(
            nombre=request.form['nombre'].strip(),
            descripcion=request.form.get('descripcion', '').strip(),
            estado=request.form.get('estado', 'Activo').strip(),
            costo_base=safe_decimal(request.form.get('costo_base', '0')),
            precio_venta_sugerido=safe_decimal(request.form.get('precio_venta_sugerido', '0')),
            comision_estimada=safe_decimal(request.form.get('comision_estimada', '0')),
            que_incluye=request.form.get('que_incluye', '').strip(),
            proveedor_id=proveedor_id
        )
        
        # Procesar fechas
        if request.form.get('fecha_inicio'):
            try:
                catalogo.fecha_inicio = datetime.strptime(
                    request.form['fecha_inicio'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de inicio inválido.', 'danger')
                return redirect(url_for('nuevo_catalogo'))
        
        if request.form.get('fecha_fin'):
            try:
                catalogo.fecha_fin = datetime.strptime(
                    request.form['fecha_fin'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de fin inválido.', 'danger')
                return redirect(url_for('nuevo_catalogo'))
        
        db.session.add(catalogo)
        db.session.flush()  # Para obtener el ID
        
        # Manejar archivo PDF
        file = request.files.get('archivo_pdf')
        if file and file.filename:
            nombre_archivo, contenido_pdf, error_mensaje = guardar_comprobante(file, catalogo)
            if error_mensaje:
                flash(error_mensaje, 'danger')
                return redirect(url_for('nuevo_catalogo'))
            elif nombre_archivo:
                catalogo.comprobante_venta = nombre_archivo
                catalogo.comprobante_pdf = contenido_pdf
        
        db.session.commit()
        flash('Catálogo creado correctamente.', 'success')
        return redirect(url_for('catalogos'))
    
    # Para GET request - obtener proveedores disponibles
    if current_user.rol == 'controling':
        proveedores = Proveedor.query.filter_by(empresa_id=current_user.empresa_id).all()
    else:
        proveedores = Proveedor.query.all()
    
    return render_template('nuevo_catalogo.html', proveedores=proveedores)

@app.route('/catalogos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def editar_catalogo(id):
    """Editar un catálogo existente"""
    catalogo = Catalogo.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and catalogo.proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para editar este catálogo.', 'danger')
        return redirect(url_for('catalogos'))
    
    if request.method == 'POST':
        proveedor_id = request.form.get('proveedor_id')
        if not proveedor_id:
            flash('Debe seleccionar un proveedor.', 'danger')
            return redirect(url_for('editar_catalogo', id=id))
        
        # Verificar que el proveedor pertenece a la empresa del usuario (para controling)
        proveedor = Proveedor.query.get(proveedor_id)
        if current_user.rol == 'controling' and proveedor.empresa_id != current_user.empresa_id:
            flash('No autorizado para asignar este proveedor.', 'danger')
            return redirect(url_for('editar_catalogo', id=id))
        
        catalogo.nombre = request.form['nombre'].strip()
        catalogo.descripcion = request.form.get('descripcion', '').strip()
        catalogo.estado = request.form.get('estado', 'Activo').strip()
        catalogo.costo_base = safe_decimal(request.form.get('costo_base', '0'))
        catalogo.precio_venta_sugerido = safe_decimal(request.form.get('precio_venta_sugerido', '0'))
        catalogo.comision_estimada = safe_decimal(request.form.get('comision_estimada', '0'))
        catalogo.que_incluye = request.form.get('que_incluye', '').strip()
        catalogo.proveedor_id = proveedor_id
        
        # Procesar fechas
        if request.form.get('fecha_inicio'):
            try:
                catalogo.fecha_inicio = datetime.strptime(
                    request.form['fecha_inicio'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de inicio inválido.', 'danger')
                return redirect(url_for('editar_catalogo', id=id))
        else:
            catalogo.fecha_inicio = None
        
        if request.form.get('fecha_fin'):
            try:
                catalogo.fecha_fin = datetime.strptime(
                    request.form['fecha_fin'], '%Y-%m-%d'
                ).date()
            except ValueError:
                flash('Formato de fecha de fin inválido.', 'danger')
                return redirect(url_for('editar_catalogo', id=id))
        else:
            catalogo.fecha_fin = None
        
        # Manejar archivo PDF
        file = request.files.get('archivo_pdf')
        if file and file.filename:
            nombre_archivo, contenido_pdf, error_mensaje = guardar_comprobante(file, catalogo)
            if error_mensaje:
                flash(error_mensaje, 'danger')
                return redirect(url_for('editar_catalogo', id=id))
            elif nombre_archivo:
                catalogo.comprobante_venta = nombre_archivo
                catalogo.comprobante_pdf = contenido_pdf
        
        db.session.commit()
        flash('Catálogo actualizado correctamente.', 'success')
        return redirect(url_for('catalogos'))
    
    # Para GET request - obtener proveedores disponibles
    if current_user.rol == 'controling':
        proveedores = Proveedor.query.filter_by(empresa_id=current_user.empresa_id).all()
    else:
        proveedores = Proveedor.query.all()
    
    return render_template('nuevo_catalogo.html', catalogo=catalogo, proveedores=proveedores)

@app.route('/catalogos/eliminar/<int:id>', methods=['POST'])
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def eliminar_catalogo(id):
    """Eliminar un catálogo"""
    catalogo = Catalogo.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and catalogo.proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para eliminar este catálogo.', 'danger')
        return redirect(url_for('catalogos'))
    
    # Eliminar el archivo de comprobante si existe
    if catalogo.comprobante_venta:
        ruta_comprobante = os.path.join(app.config['UPLOAD_FOLDER'], catalogo.comprobante_venta)
        if os.path.exists(ruta_comprobante):
            try:
                os.remove(ruta_comprobante)
            except Exception as e:
                print(f"Error al eliminar archivo: {e}")
    
    db.session.delete(catalogo)
    db.session.commit()
    flash('Catálogo eliminado correctamente.', 'success')
    return redirect(url_for('catalogos'))

@app.route('/exportar_catalogos')
@login_required
@rol_required('admin', 'master', 'controling', 'analista')
@empresa_tiene_productos_required
def exportar_catalogos():
    """Exportar lista de catálogos a Excel"""
    if current_user.rol == 'controling':
        catalogos = Catalogo.query.join(Proveedor).filter(Proveedor.empresa_id == current_user.empresa_id).all()
    else:
        catalogos = Catalogo.query.all()
    
    data = [{
        'ID': c.id,
        'Nombre': c.nombre,
        'Descripción': c.descripcion,
        'Fecha Inicio': c.fecha_inicio.strftime('%Y-%m-%d') if c.fecha_inicio else '',
        'Fecha Fin': c.fecha_fin.strftime('%Y-%m-%d') if c.fecha_fin else '',
        'Estado': c.estado,
        'Costo Base': float(c.costo_base),
        'Precio Venta Sugerido': float(c.precio_venta_sugerido),
        'Comisión Estimada': float(c.comision_estimada),
        'Qué Incluye': c.que_incluye,
        'Proveedor': c.proveedor.nombre if c.proveedor else 'N/A',
        'Empresa': c.proveedor.empresa.nombre if c.proveedor and c.proveedor.empresa else 'N/A',
        'Tiene Comprobante': 'Sí' if c.comprobante_pdf else 'No'
    } for c in catalogos]
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Catalogos', index=False)
    
    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'catalogos_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/comprobante_contrato/<int:id>')
@login_required
def ver_comprobante_contrato(id):
    """Ver comprobante PDF de un contrato"""
    contrato = Contrato.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and contrato.proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para ver este comprobante.', 'danger')
        return redirect(url_for('contratos'))
    
    if not contrato.comprobante_pdf:
        flash('No hay comprobante para este contrato.', 'warning')
        return redirect(url_for('contratos'))

    return Response(
        contrato.comprobante_pdf,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"inline; filename=comprobante_contrato_{contrato.id}.pdf"}
    )

@app.route('/comprobante_catalogo/<int:id>')
@login_required
def ver_comprobante_catalogo(id):
    """Ver comprobante PDF de un catálogo"""
    catalogo = Catalogo.query.get_or_404(id)
    
    # Verificar permisos
    if current_user.rol == 'controling' and catalogo.proveedor.empresa_id != current_user.empresa_id:
        flash('No autorizado para ver este comprobante.', 'danger')
        return redirect(url_for('catalogos'))
    
    if not catalogo.comprobante_pdf:
        flash('No hay comprobante para este catálogo.', 'warning')
        return redirect(url_for('catalogos'))

    return Response(
        catalogo.comprobante_pdf,
        mimetype='application/pdf',
        headers={"Content-Disposition": f"inline; filename=comprobante_catalogo_{catalogo.id}.pdf"}
    )

# =====================
# EXPORTACIONES A EXCEL
# =====================
@app.route('/exportar_usuarios')
@login_required
@rol_required('admin', 'master')
def exportar_usuarios():
    usuarios = Usuario.query.all() if current_user.rol == 'master' else Usuario.query.filter(Usuario.username != 'mcontreras').all()

    data = [{
        'ID': u.id,
        'Usuario': u.username,
        'Nombre': u.nombre + ' ' + u.apellidos,
        'rut': u.rut,
        'Fecha de nacimiento': u.fecha_nacimiento,
        'Fecha de ingreso': u.fecha_ingreso,
        'Teléfono': u.telefono,
        'Correo Personal': u.correo_personal,
        'Correo Corporativo': u.correo,
        'Dirección': u.direccion,
        'Comisión': u.comision,
        'Sueldo': u.sueldo,
        'Estado': u.estado,
        'Rol': u.rol,
        'Empresa': u.empresa.nombre if u.empresa else 'N/A',
    } for u in usuarios]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Usuarios')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='usuarios.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/exportar_reservas') 
@login_required
def exportar_reservas():
    reservas = Reserva.query.all() if current_user.rol in ('admin', 'master') else Reserva.query.filter_by(usuario_id=current_user.id).all()

    data = [{
        'Usuario': r.usuario.username,
        'Fecha de viaje': r.fecha_viaje,
        'Producto': r.producto,
        'Fecha de venta': r.fecha_venta,
        'Modalidad de pago': r.modalidad_pago,
        'Nombre de pasajero': r.nombre_pasajero,
        'Teléfono de pasajero': r.telefono_pasajero,
        'Mail Pasajero': r.mail_pasajero,
        'Precio venta total': r.precio_venta_total,
        'Hotel neto': r.hotel_neto,
        'Vuelo neto': r.vuelo_neto,
        'Traslado neto': r.traslado_neto,
        'Seguro neto': r.seguro_neto,
        'Circuito Neto': r.circuito_neto,
        'Crucero Neto': r.crucero_neto,
        'Excursion Neto': r.excursion_neto,
        'Paquete Neto': r.paquete_neto,
        'Ganancia Total': r.ganancia_total,
        'Comisión Ejecutivo': r.comision_ejecutivo,
        'Comisión Agencia': r.comision_agencia,
        'Bonos': r.bonos,
        'Comentarios': r.comentarios,
        'Localizadores': r.localizadores,
        'Nombre ejecutivo': r.nombre_ejecutivo,
        'Correo ejecutivo': r.correo_ejecutivo,
        'Destino': r.destino,  
        'comentarios' : r.comentarios,  # Comentarios de la reserva      
        'Estado de pago': r.estado_pago,           # Nuevo campo en exportación
        'Venta cobrada': r.venta_cobrada,          # Nuevo campo en exportación
        'Venta emitida': r.venta_emitida           # Nuevo campo en exportación
    } for r in reservas]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reservas')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='reservas.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/exportar_control_gestion_clientes')
@login_required
@rol_required('admin', 'master')
def exportar_control_gestion_clientes():
    ejecutivo_id = request.args.get('ejecutivo_id', type=int)
    rango_fechas_str = request.args.get('rango_fechas', 'ultimos_30_dias')

    reservas_query = Reserva.query.join(Usuario)
    if ejecutivo_id:
        reservas_query = reservas_query.filter(Reserva.usuario_id == ejecutivo_id)
    start_date, end_date = _get_date_range(rango_fechas_str)
    reservas_query = reservas_query.filter(Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
                                           Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d'))
    reservas = reservas_query.order_by(Reserva.fecha_venta.desc()).all()

    data = [
        {
            'Ejecutivo': f"{r.nombre_ejecutivo}\n{r.correo_ejecutivo}",
            'Estado de Pago': r.estado_pago,
            'Venta Cobrada': r.venta_cobrada,
            'Venta Emitida': r.venta_emitida,
            'Nombre Pasajero': r.nombre_pasajero,
            'Teléfono Pasajero': r.telefono_pasajero,
            'Mail Pasajero': r.mail_pasajero,
            'Destino': r.destino,
            'Producto': r.producto,
            'Fecha de Compra': r.fecha_venta,
            'Fecha de Viaje': r.fecha_viaje
        }
        for r in reservas
    ]

    output = io.BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Control Gestión Clientes')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='control_gestion_clientes.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/exportar_reporte_detalle_ventas')
@login_required
@rol_required('admin', 'master')
def exportar_reporte_detalle_ventas():
    selected_mes_str = request.args.get('mes', '')
    try:
        month_name, year_str = selected_mes_str.split(' ')
        month_num = datetime.strptime(month_name, '%B').month
        year = int(year_str)
        start_date = datetime(year, month_num, 1)
        if month_num == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
    except Exception:
        today = datetime.now()
        start_date, end_date = today, today

    reservas_query = Reserva.query.join(Usuario).filter(
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    )

    reporte_data_dict = {}
    for reserva in reservas_query.all():
        ejecutivo_id = reserva.nombre_ejecutivo or ''
        correo_ejecutivo = reserva.correo_ejecutivo or ''
        rol_ejecutivo = reserva.usuario.rol
        comision_ejecutivo_porcentaje = safe_decimal(reserva.usuario.comision) / Decimal('100.0')
        total_neto = (
            reserva.hotel_neto +
            reserva.vuelo_neto +
            reserva.traslado_neto +
            reserva.seguro_neto +
            reserva.circuito_neto +
            reserva.crucero_neto +
            reserva.excursion_neto +
            reserva.paquete_neto
        )
        ganancia_bruta = reserva.precio_venta_total - total_neto
        comision_usuario = ganancia_bruta * comision_ejecutivo_porcentaje
        ganancia_neta = ganancia_bruta - comision_usuario
        bonos = reserva.bonos or 0.0

        if ejecutivo_id not in reporte_data_dict:
            reporte_data_dict[ejecutivo_id] = {
                'Ejecutivo': ejecutivo_id,
                'Correo Ejecutivo': correo_ejecutivo,
                'Rol Ejecutivo': rol_ejecutivo,
                'Total Ventas': 0.0,
                'Total Costos': 0.0,
                'Total Comisiones Ejecutivo': 0.0,
                'Total Bonos': 0.0,
                'Total Ganancia': 0.0,
                'N° de Ventas Realizadas': 0
            }
        reporte_data_dict[ejecutivo_id]['Total Ventas'] += reserva.precio_venta_total
        reporte_data_dict[ejecutivo_id]['Total Costos'] += total_neto
        reporte_data_dict[ejecutivo_id]['Total Comisiones Ejecutivo'] += comision_usuario
        reporte_data_dict[ejecutivo_id]['Total Bonos'] += bonos
        reporte_data_dict[ejecutivo_id]['Total Ganancia'] += ganancia_neta
        reporte_data_dict[ejecutivo_id]['N° de Ventas Realizadas'] += 1

    reporte_data = list(reporte_data_dict.values())

    output = io.BytesIO()
    df = pd.DataFrame(reporte_data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Detalle Ventas')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='reporte_detalle_ventas.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/exportar_marketing')
@login_required
@rol_required('admin', 'master')
def exportar_marketing():
    ejecutivo_id = request.args.get('ejecutivo_id', type=int)
    rango_fechas_str = request.args.get('rango_fechas', 'ultimos_30_dias')

    reservas_query = Reserva.query.join(Usuario)
    if ejecutivo_id:
        reservas_query = reservas_query.filter(Reserva.usuario_id == ejecutivo_id)
    start_date, end_date = _get_date_range(rango_fechas_str)
    reservas_query = reservas_query.filter(Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
                                           Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d'))
    reservas = reservas_query.order_by(Reserva.fecha_venta.desc()).all()

    data = [
        {
            'Destino': r.destino,
            'Fecha de venta': r.fecha_venta,
            'Fecha de viaje': r.fecha_viaje,
            'Nombre pasajero': r.nombre_pasajero,
            'Teléfono pasajero': r.telefono_pasajero,
            'Mail pasajero': r.mail_pasajero
        }
        for r in reservas
    ]

    output = io.BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Marketing')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='marketing.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/exportar_reservas_usuario')
@login_required
def exportar_reservas_usuario():
    # Obtener mes seleccionado
    meses_anteriores = obtener_meses_anteriores()

    selected_mes_str = request.args.get('mes', meses_anteriores[-1] if meses_anteriores else '')
    today = datetime.now()
    try:
        start_date, end_date = _get_date_range(selected_mes_str)
    except Exception:
        start_date, end_date = today, today

    reservas = Reserva.query.filter(
        Reserva.usuario_id == current_user.id,
        Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
        Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d')
    ).all()

    data = [{
        'Fecha de venta': r.fecha_venta,
        'Fecha de viaje': r.fecha_viaje,
        'Producto': r.producto,
        'Modalidad de pago': r.modalidad_pago,
        'Nombre de pasajero': r.nombre_pasajero,
        'Teléfono de pasajero': r.telefono_pasajero,
        'Mail Pasajero': r.mail_pasajero,
        'Precio venta total': r.precio_venta_total,
        'Hotel neto': r.hotel_neto,
        'Vuelo neto': r.vuelo_neto,
        'Traslado neto': r.traslado_neto,
        'Seguro neto': r.seguro_neto,
        'Circuito Neto': r.circuito_neto,
        'Crucero Neto': r.crucero_neto,
        'Excursion Neto': r.excursion_neto,
        'Paquete Neto': r.paquete_neto,
        'Ganancia Total': r.ganancia_total,
        'Comisión Ejecutivo': r.comision_ejecutivo,
        'Comisión Agencia': r.comision_agencia,
        'Bonos': r.bonos,
        'Comentarios': r.comentarios,
        'Localizadores': r.localizadores,
        'Nombre ejecutivo': r.nombre_ejecutivo,
        'Correo ejecutivo': r.correo_ejecutivo,
        'Destino': r.destino,
        'Estado de pago': r.estado_pago,
        'Venta cobrada': r.venta_cobrada,
        'Venta emitida': r.venta_emitida
    } for r in reservas]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reservas')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='mis_reservas.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/exportar_panel_comisiones')
@login_required
@rol_required('admin', 'master')
def exportar_panel_comisiones():
    ejecutivo_id = request.args.get('ejecutivo_id', type=int)
    rango_fechas_str = request.args.get('rango_fechas', 'ultimos_30_dias')

    ejecutivos = Usuario.query.filter(Usuario.rol.in_(['usuario', 'admin'])).order_by(Usuario.nombre).all()
    reservas_query = Reserva.query.join(Usuario)
    if ejecutivo_id:
        reservas_query = reservas_query.filter(Reserva.usuario_id == ejecutivo_id)
    start_date, end_date = _get_date_range(rango_fechas_str)
    reservas_query = reservas_query.filter(Reserva.fecha_venta >= start_date.strftime('%Y-%m-%d'),
                                           Reserva.fecha_venta <= end_date.strftime('%Y-%m-%d'))
    reservas = reservas_query.order_by(Reserva.fecha_venta.desc()).all()

    data = []
    for reserva in reservas:
        comision_ejecutivo_porcentaje = safe_decimal(reserva.usuario.comision) / Decimal('100.0')
        total_neto = (
            reserva.hotel_neto +
            reserva.vuelo_neto +
            reserva.traslado_neto +
            reserva.seguro_neto +
            reserva.circuito_neto +
            reserva.crucero_neto +
            reserva.excursion_neto +
            reserva.paquete_neto
        )
        ganancia_total = reserva.precio_venta_total - total_neto
        comision_ejecutivo = ganancia_total * comision_ejecutivo_porcentaje
        comision_agencia = ganancia_total - comision_ejecutivo
        bonos = reserva.bonos or 0.0
        
        data.append({
            'Precio Venta Total': reserva.precio_venta_total,
            'Hotel Neto': reserva.hotel_neto,
            'Vuelo Neto': reserva.vuelo_neto,
            'Traslado Neto': reserva.traslado_neto,
            'Seguro Neto': reserva.seguro_neto,
            'Circuito Neto': reserva.circuito_neto,
            'Crucero Neto': reserva.crucero_neto,
            'Excursion Neto': reserva.excursion_neto,
            'Paquete Neto': reserva.paquete_neto,
            'Bonos': bonos,
            'Ganancia Total': ganancia_total,
            'Comision Ejecutivo': comision_ejecutivo,
            'Comision Agencia': comision_agencia
        })

    # Obtener nombre del ejecutivo para el archivo
    nombre_archivo = 'comisiones'
    if ejecutivo_id:
        ejecutivo = Usuario.query.get(ejecutivo_id)
        if ejecutivo:
            nombre_archivo = f"{ejecutivo.nombre.lower()}comision"
    
    output = io.BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Panel Comisiones')
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f'{nombre_archivo}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    app.run(debug=True)