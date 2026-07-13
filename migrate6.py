from run import app, db, User

with app.app_context():
    # Approve all existing students and faculty
    updated = User.query.filter(
        User.role.in_(['student', 'faculty']),
        User.is_approved == False
    ).all()
    for u in updated:
        u.is_approved = True
    db.session.commit()
    print(f'✅ Approved {len(updated)} existing accounts')