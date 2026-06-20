"""OTP + JWT authentication per docs/09_API_Specification.md."""
import os
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import jsonify, request, session

from db import execute, query

JWT_SECRET = os.environ.get('JWT_SECRET', 'govqueue-jwt-secret-2024')
JWT_ALGORITHM = 'HS256'
JWT_HOURS = 24
DEMO_OTP = '123456'
OTP_MINUTES = 10


def now_iso():
    return datetime.now().isoformat()


def request_otp(phone_number):
    phone_number = phone_number.strip()
    expires = (datetime.now() + timedelta(minutes=OTP_MINUTES)).isoformat()
    execute(
        "INSERT INTO otp_session(phone_number, code, expires_at) VALUES(?,?,?)",
        (phone_number, DEMO_OTP, expires),
    )
    print(f'[OTP] {phone_number} -> {DEMO_OTP}')
    return {'message': 'OTP sent successfully'}


def verify_otp(phone_number, otp, full_name=None):
    phone_number = phone_number.strip()
    row = query(
        """SELECT * FROM otp_session
           WHERE phone_number=? AND code=? AND used=0
           ORDER BY id DESC LIMIT 1""",
        (phone_number, otp.strip()),
        one=True,
    )
    if not row:
        raise ValueError('Invalid OTP')
    if row['expires_at'] < now_iso():
        raise ValueError('OTP expired')

    execute("UPDATE otp_session SET used=1 WHERE id=?", (row['id'],))

    user = query("SELECT * FROM user WHERE phone_number=?", (phone_number,), one=True)
    if not user:
        if not full_name:
            full_name = 'Citizen'
        ts = now_iso()
        uid = execute(
            """INSERT INTO user(full_name, phone_number, preferred_language, is_active, created_at, updated_at)
               VALUES(?,?,?,?,?,?)""",
            (full_name, phone_number, 'en', 1, ts, ts),
        )
        citizen_role = query("SELECT id FROM role WHERE name='Citizen'", one=True)
        if citizen_role:
            execute("INSERT OR IGNORE INTO user_role(user_id, role_id) VALUES(?,?)", (uid, citizen_role['id']))
        user = query("SELECT * FROM user WHERE id=?", (uid,), one=True)
    elif not user['is_active']:
        raise ValueError('Account inactive')

    token = create_token(user['id'])
    return token, user


def get_user_roles(user_id):
    rows = query(
        """SELECT r.name FROM role r
           JOIN user_role ur ON ur.role_id = r.id
           WHERE ur.user_id=?""",
        (user_id,),
    )
    return [r['name'] for r in rows]


def user_to_dict(user):
    return {
        'id': user['id'],
        'fullName': user['full_name'],
        'phoneNumber': user['phone_number'],
        'preferredLanguage': user['preferred_language'],
        'roles': get_user_roles(user['id']),
    }


def create_token(user_id):
    payload = {
        'sub': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def set_session(user):
    session['user_id'] = user['id']
    session['name'] = user['full_name']
    session['roles'] = get_user_roles(user['id'])
    session['branch_id'] = user['branch_id']


def get_token_from_request():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:]
    return None


def get_current_user_id():
    token = get_token_from_request()
    if token:
        try:
            data = decode_token(token)
            return data['sub']
        except jwt.PyJWTError:
            return None
    return session.get('user_id')


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        uid = get_current_user_id()
        if not uid:
            return jsonify({'success': False, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 401
        user = query("SELECT * FROM user WHERE id=? AND is_active=1", (uid,), one=True)
        if not user:
            return jsonify({'success': False, 'message': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 401
        request.current_user = user
        request.user_roles = get_user_roles(uid)
        return f(*args, **kwargs)
    return decorated


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated(*args, **kwargs):
            if not any(r in request.user_roles for r in roles):
                return jsonify({'success': False, 'message': 'Forbidden', 'code': 'FORBIDDEN'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def api_error(message, code, status=400):
    return jsonify({'success': False, 'message': message, 'code': code}), status
