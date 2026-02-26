import os
import secrets

# Auto-generate a dev SECRET_KEY if not set (development convenience only).
# In production, always set SECRET_KEY explicitly via environment variable.
if not os.environ.get('SECRET_KEY'):
    dev_key = secrets.token_hex(32)
    os.environ['SECRET_KEY'] = dev_key
    print(
        '\n[MGG_SYS] WARNING: SECRET_KEY not set — generated a temporary key.\n'
        '  This key will change on every restart (sessions will be invalidated).\n'
        f'  To persist sessions, run:  export SECRET_KEY={dev_key}\n'
    )

from app import create_app

app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5001)
