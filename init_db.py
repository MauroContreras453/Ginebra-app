from app import db, Usuario, app

with app.app_context():
    db.drop_all()
    db.create_all()

    admin = Usuario(
        username='erobles',
        nombre='Erika',
        apellidos='Robles Sosa',
        correo='erika.robles@multidestinos.cl',
        comision='50',
        rol='admin',
        empresa_id=None
    )
    admin.password = 'Bianca453'  # usa el setter

    master = Usuario(
        username='mcontreras',
        nombre='Mauro',
        apellidos='Contreras Palma',
        correo='mauro.contreraspalma@gmail.com',
        comision='0',
        rol='master',
        empresa_id=None
    )
    master.password = 'Program3312'  # usa el setter

    db.session.add_all([admin, master])
    db.session.commit()

    print("Base de datos creada y usuarios iniciales agregados.")


