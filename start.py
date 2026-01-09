#!/usr/bin/env python
"""
Script de inicio para Render.
1. Inicializa la base de datos y crea usuario master
2. Inicia gunicorn
"""
import subprocess
import sys

def init_database():
    """Inicializa la base de datos"""
    print("=" * 50)
    print("Inicializando base de datos...")
    print("=" * 50)
    
    from Ginebra import app, db, Usuario
    
    with app.app_context():
        # Crear todas las tablas
        db.create_all()
        print("✓ Tablas creadas correctamente")
        
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
    
    print("=" * 50)
    print("Iniciando servidor...")
    print("=" * 50)

if __name__ == '__main__':
    # Primero inicializar BD
    init_database()
    
    # Luego iniciar gunicorn
    subprocess.run([
        sys.executable, '-m', 'gunicorn',
        '--bind', '0.0.0.0:10000',
        'Ginebra:app'
    ])
