from run import app, db
from run import CampusConfig

with app.app_context():
    cfg = CampusConfig.query.first()
    if cfg:
        cfg.name      = 'My Location (Test)'
        cfg.latitude  = 28.622902
        cfg.longitude = 77.050226
        cfg.radius_m  = 500
    else:
        db.session.add(CampusConfig(
            name='My Location (Test)',
            latitude=28.622902,
            longitude=77.050226,
            radius_m=500
        ))
    db.session.commit()
    print('✅ Campus coordinates updated!')