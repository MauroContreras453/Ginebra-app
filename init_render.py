"""
Script de inicialización para Render.
Crea las tablas y el usuario master automáticamente.
"""
import os
from sqlalchemy import text
from Ginebra import app, db, Usuario

def init_database():
    with app.app_context():
        # Si existe la variable RESET_DB, eliminar todo y recrear
        if os.environ.get('RESET_DB') == 'true':
            print("⚠ RESET_DB activado - Eliminando todas las tablas...")
            db.drop_all()
            
            # Eliminar los tipos ENUM huérfanos de PostgreSQL
            try:
                db.session.execute(text("DROP TYPE IF EXISTS estado_postventa_viaje CASCADE;"))
                db.session.execute(text("DROP TYPE IF EXISTS estado_postventa_resultado CASCADE;"))
                db.session.commit()
                print("✓ Tipos ENUM eliminados")
            except Exception as e:
                print(f"• No se pudieron eliminar ENUMs: {e}")
                db.session.rollback()
        
        # Crear todas las tablas
        db.create_all()
        print("✓ Tablas de base de datos creadas")
        
        # Crear usuario master si no existe
        if not Usuario.query.filter_by(username='mcontreras').first():
            master = Usuario(
                username='mcontreras',
                nombre='Mauro',
                apellidos='Contreras Palma',
                correo='mauro.contreraspalma@gmail.com',
                comision=0,
                rol='master',
                empresa_id=None
            )
            master.password = 'Program3312'
            db.session.add(master)
            db.session.commit()
            print("✓ Usuario master 'mcontreras' creado")
        else:
            print("• Usuario master ya existe")

if __name__ == '__main__':
    init_database()
    print("✓ Inicialización completada")
