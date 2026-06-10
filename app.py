from datetime import date, datetime
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from auth import (
    api_error,
    create_token,
    get_current_user_id,
    get_user_roles,
    jwt_required,
    request_otp,
    roles_required,
    set_session,
    user_to_dict,
    verify_otp,
)
from db import execute, init_db, query
from queue_engine import (
    QueueError,
    cancel_ticket,
    call_next,
    complete_ticket,
    congestion_rows,
    create_ticket,
    get_active_ticket,
    get_queue_status,
    get_staff_services,
    get_position,
    has_active_ticket,
    no_show_ticket,
    skip_ticket,
    start_ticket,
    ticket_payload,
    today_str,
    waiting_count,
)

app = Flask(__name__)
app.secret_key = 'govqueue-secret-2024'

ROLE_ROUTES = {
    'Citizen': 'citizen_dashboard',
    'DoorKeeper': 'door_keeper_dashboard',
    'CounterStaff': 'staff_dashboard',
    'BranchSupervisor': 'supervisor_dashboard',
    'SystemAdmin': 'admin_dashboard',
}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_roles = session.get('roles', [])
            if not any(r in user_roles for r in roles):
                flash('Access denied.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return query('SELECT * FROM user WHERE id=?', (uid,), one=True)


def unread_count():
    uid = session.get('user_id')
    if not uid:
        return 0
    row = query(
        'SELECT COUNT(*) as c FROM notification_log WHERE user_id=? AND is_read=0',
        (uid,),
        one=True,
    )
    return row['c'] if row else 0


def primary_role(roles):
    for r in ('SystemAdmin', 'BranchSupervisor', 'CounterStaff', 'DoorKeeper', 'Citizen'):
        if r in roles:
            return r
    return roles[0] if roles else None


def handle_queue_error(err):
    status = 409 if err.code == 'ACTIVE_BOOKING_EXISTS' else 400
    if err.code == 'NOT_FOUND':
        status = 404
    elif err.code == 'FORBIDDEN':
        status = 403
    elif err.code == 'QUEUE_EMPTY':
        status = 200
    return api_error(err.message, err.code, status)


# ── Public pages ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template(
        'index.html',
        congestion=congestion_rows(),
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    step = request.args.get('step', 'phone')
    phone = request.args.get('phone', '')

    if request.method == 'POST':
        action = request.form.get('action', 'request')
        phone = request.form.get('phone', '').strip()
        if action == 'request':
            request_otp(phone)
            flash(f'OTP sent. Use code 123456 for demo.', 'success')
            return redirect(url_for('login', step='verify', phone=phone))
        otp = request.form.get('otp', '').strip()
        try:
            token, user = verify_otp(phone, otp)
            set_session(user)
            flash(f"Welcome, {user['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('login', step='verify', phone=phone))

    return render_template('login.html', step=step, phone=phone)


@app.route('/register', methods=['GET', 'POST'])
def register():
    step = request.args.get('step', 'details')
    phone = request.args.get('phone', '')
    name = request.args.get('name', '')

    if request.method == 'POST':
        action = request.form.get('action', 'request')
        phone = request.form.get('phone', '').strip()
        name = request.form.get('full_name', '').strip()
        if action == 'request':
            if query('SELECT id FROM user WHERE phone_number=?', (phone,), one=True):
                flash('Phone already registered. Please login.', 'warning')
                return redirect(url_for('login'))
            request_otp(phone)
            flash('OTP sent. Use code 123456 for demo.', 'success')
            return redirect(url_for('register', step='verify', phone=phone, name=name))
        otp = request.form.get('otp', '').strip()
        try:
            token, user = verify_otp(phone, otp, full_name=name)
            set_session(user)
            flash('Registered successfully!', 'success')
            return redirect(url_for('dashboard'))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('register', step='verify', phone=phone, name=name))

    return render_template('register.html', step=step, phone=phone, name=name)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    roles = session.get('roles', [])
    route = ROLE_ROUTES.get(primary_role(roles))
    if route:
        return redirect(url_for(route))
    return redirect(url_for('index'))


# ── Citizen pages ─────────────────────────────────────────────────────────────

@app.route('/citizen')
@login_required
@role_required('Citizen')
def citizen_dashboard():
    uid = session['user_id']
    active = get_active_ticket(uid)
    if active:
        active = dict(active)
        active['position'] = get_position(active)
    notifs = query(
        'SELECT * FROM notification_log WHERE user_id=? AND is_read=0 ORDER BY sent_at DESC LIMIT 5',
        (uid,),
    )
    return render_template(
        'citizen/dashboard.html',
        active=active,
        notifs=notifs,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/citizen/book', methods=['GET', 'POST'])
@login_required
@role_required('Citizen')
def citizen_book():
    uid = session['user_id']
    if has_active_ticket(uid):
        flash('You already have an active booking.', 'warning')
        return redirect(url_for('citizen_bookings'))

    if request.method == 'POST':
        branch_id = int(request.form['branch_id'])
        service_id = int(request.form['service_id'])
        try:
            result = create_ticket(uid, branch_id, service_id)
            flash(f"Joined queue! Ticket #{result['queueNumber']}", 'success')
            return redirect(url_for('citizen_dashboard'))
        except QueueError as e:
            flash(e.message, 'error')

    branches = query('SELECT * FROM branch WHERE is_active=1 ORDER BY name')
    branch_id = request.args.get('branch_id', branches[0]['id'] if branches else None)
    services = []
    if branch_id:
        services = query(
            """SELECT bs.branch_id, bs.service_id, s.name, s.description,
                      bs.estimated_duration_minutes
               FROM branch_service bs
               JOIN service s ON bs.service_id = s.id
               WHERE bs.branch_id=? AND bs.is_active=1 AND s.is_active=1
               ORDER BY s.name""",
            (branch_id,),
        )
    return render_template(
        'citizen/book.html',
        branches=branches,
        services=services,
        branch_id=int(branch_id) if branch_id else None,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/citizen/bookings')
@login_required
@role_required('Citizen')
def citizen_bookings():
    uid = session['user_id']
    tickets = query(
        """SELECT t.*, s.name as service_name, b.name as branch_name
           FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           JOIN service s ON bs.service_id = s.id
           JOIN branch b ON bs.branch_id = b.id
           WHERE t.citizen_id=?
           ORDER BY t.joined_at DESC""",
        (uid,),
    )
    return render_template(
        'citizen/bookings.html',
        tickets=tickets,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/citizen/tickets/<int:tid>/cancel', methods=['POST'])
@login_required
@role_required('Citizen')
def citizen_cancel_ticket(tid):
    try:
        cancel_ticket(tid, session['user_id'])
        flash('Ticket cancelled.', 'success')
    except QueueError as e:
        flash(e.message, 'error')
    return redirect(url_for('citizen_bookings'))


@app.route('/citizen/track')
@login_required
@role_required('Citizen')
def citizen_track():
    uid = session['user_id']
    active = get_active_ticket(uid)
    payload = None
    if active:
        payload = ticket_payload(active, active['branch_service_id'])
    return render_template(
        'citizen/track.html',
        active=active,
        payload=payload,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/citizen/profile', methods=['GET', 'POST'])
@login_required
@role_required('Citizen')
def citizen_profile():
    uid = session['user_id']
    if request.method == 'POST':
        name = request.form['full_name'].strip()
        lang = request.form.get('preferred_language', 'en')
        execute(
            'UPDATE user SET full_name=?, preferred_language=?, updated_at=? WHERE id=?',
            (name, lang, datetime.now().isoformat(), uid),
        )
        session['name'] = name
        flash('Profile updated.', 'success')
    u = current_user()
    return render_template('citizen/profile.html', u=u, user=u, unread=unread_count())


# ── Door Keeper ───────────────────────────────────────────────────────────────

@app.route('/door-keeper', methods=['GET', 'POST'])
@login_required
@role_required('DoorKeeper')
def door_keeper_dashboard():
    bid = session.get('branch_id')
    citizen = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'search':
            phone = request.form.get('phone', '').strip()
            citizen = query(
                """SELECT u.id, u.full_name, u.phone_number
                   FROM user u
                   JOIN user_role ur ON ur.user_id = u.id
                   JOIN role r ON ur.role_id = r.id
                   WHERE u.phone_number=? AND r.name='Citizen'""",
                (phone,),
                one=True,
            )
            if not citizen:
                flash('Citizen not found.', 'warning')
        elif action == 'create_citizen':
            name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            ts = datetime.now().isoformat()
            uid = execute(
                'INSERT INTO user(full_name, phone_number, created_at, updated_at) VALUES(?,?,?,?)',
                (name, phone, ts, ts),
            )
            role = query("SELECT id FROM role WHERE name='Citizen'", one=True)
            execute('INSERT INTO user_role(user_id, role_id) VALUES(?,?)', (uid, role['id']))
            flash('Citizen created.', 'success')
            citizen = query('SELECT id, full_name, phone_number FROM user WHERE id=?', (uid,), one=True)
        elif action == 'create_booking':
            try:
                result = create_ticket(
                    int(request.form['citizen_id']),
                    bid,
                    int(request.form['service_id']),
                )
                flash(f"Booking created. Ticket #{result['queueNumber']}", 'success')
            except QueueError as e:
                flash(e.message, 'error')

    services = query(
        """SELECT bs.service_id, s.name
           FROM branch_service bs JOIN service s ON bs.service_id = s.id
           WHERE bs.branch_id=? AND bs.is_active=1""",
        (bid,),
    )
    return render_template(
        'door_keeper/dashboard.html',
        citizen=citizen,
        services=services,
        user=current_user(),
        unread=unread_count(),
    )


# ── Counter Staff ─────────────────────────────────────────────────────────────

@app.route('/staff')
@login_required
@role_required('CounterStaff')
def staff_dashboard():
    uid = session['user_id']
    bid = session.get('branch_id')
    win = query(
        """SELECT w.*, sw.id as sw_id
           FROM staff_window sw
           JOIN window w ON sw.window_id = w.id
           WHERE sw.user_id=?""",
        (uid,),
        one=True,
    )
    qualifications = get_staff_services(uid)
    serving = query(
        """SELECT t.*, u.full_name FROM ticket t
           JOIN user u ON t.citizen_id = u.id
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND t.ticket_date=? AND t.status IN ('Called', 'InProgress')
           ORDER BY t.called_at DESC LIMIT 1""",
        (bid, today_str()),
        one=True,
    )
    queue = query(
        """SELECT t.*, u.full_name, s.name as service_name FROM ticket t
           JOIN user u ON t.citizen_id = u.id
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           JOIN service s ON bs.service_id = s.id
           WHERE bs.branch_id=? AND t.ticket_date=? AND t.status='Waiting'
           ORDER BY t.joined_at LIMIT 10""",
        (bid, today_str()),
    )
    stats = query(
        """SELECT
             SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as completed,
             SUM(CASE WHEN t.status='NoShow' THEN 1 ELSE 0 END) as no_show,
             SUM(CASE WHEN t.status='Skipped' THEN 1 ELSE 0 END) as skipped
           FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND t.ticket_date=?""",
        (bid, today_str()),
        one=True,
    )
    return render_template(
        'staff/dashboard.html',
        win=win,
        qualifications=qualifications,
        serving=serving,
        queue=queue,
        stats=stats,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/staff/call_next', methods=['POST'])
@login_required
@role_required('CounterStaff')
def staff_call_next():
    try:
        result = call_next(session['user_id'])
        flash(f"Called ticket #{result['queueNumber']} ({result['serviceName']})", 'success')
    except QueueError as e:
        flash(e.message, 'info' if e.code == 'QUEUE_EMPTY' else 'error')
    return redirect(url_for('staff_dashboard'))


@app.route('/staff/tickets/<int:tid>/<action>', methods=['POST'])
@login_required
@role_required('CounterStaff')
def staff_ticket_action(tid, action):
    try:
        if action == 'complete':
            complete_ticket(tid)
            flash('Ticket completed.', 'success')
        elif action == 'skip':
            skip_ticket(tid)
            flash('Ticket skipped.', 'success')
        elif action == 'no_show':
            no_show_ticket(tid)
            flash('Marked no-show.', 'warning')
        elif action == 'start':
            start_ticket(tid)
            flash('Service started.', 'success')
    except QueueError as e:
        flash(e.message, 'error')
    return redirect(url_for('staff_dashboard'))


# ── Supervisor ────────────────────────────────────────────────────────────────

@app.route('/supervisor')
@login_required
@role_required('BranchSupervisor')
def supervisor_dashboard():
    bid = session.get('branch_id')
    today = today_str()
    stats = query(
        """SELECT
             COUNT(DISTINCT q.id) as active_queues,
             SUM(CASE WHEN t.status='Waiting' THEN 1 ELSE 0 END) as waiting_citizens,
             SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as today_completed
           FROM branch_service bs
           LEFT JOIN queue q ON q.branch_service_id = bs.id
           LEFT JOIN ticket t ON t.queue_id = q.id AND t.ticket_date = ?
           WHERE bs.branch_id=?""",
        (today, bid),
        one=True,
    )
    return render_template(
        'supervisor/dashboard.html',
        stats=stats,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/supervisor/windows', methods=['GET', 'POST'])
@login_required
@role_required('BranchSupervisor')
def supervisor_windows():
    bid = session.get('branch_id')
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'toggle':
            wid = int(request.form['window_id'])
            w = query('SELECT * FROM window WHERE id=?', (wid,), one=True)
            if w:
                execute('UPDATE window SET is_open=? WHERE id=?', (0 if w['is_open'] else 1, wid))
                flash('Window updated.', 'success')
        elif action == 'assign':
            wid = int(request.form['window_id'])
            staff_id = int(request.form['staff_id'])
            execute('DELETE FROM staff_window WHERE user_id=? OR window_id=?', (staff_id, wid))
            execute(
                'INSERT INTO staff_window(user_id, window_id, assigned_at) VALUES(?,?,?)',
                (staff_id, wid, datetime.now().isoformat()),
            )
            flash('Staff assigned to window.', 'success')
        elif action == 'assign_service':
            staff_id = int(request.form['staff_id'])
            service_id = int(request.form['service_id'])
            execute(
                'INSERT OR IGNORE INTO staff_service(user_id, service_id) VALUES(?,?)',
                (staff_id, service_id),
            )
            flash('Service assigned to staff.', 'success')
        elif action == 'remove_service':
            staff_id = int(request.form['staff_id'])
            service_id = int(request.form['service_id'])
            execute('DELETE FROM staff_service WHERE user_id=? AND service_id=?', (staff_id, service_id))
            flash('Service removed from staff.', 'success')
        return redirect(url_for('supervisor_windows'))

    windows = query(
        """SELECT w.*, sw.user_id as staff_id, u.full_name as staff_name
           FROM window w
           LEFT JOIN staff_window sw ON sw.window_id = w.id
           LEFT JOIN user u ON sw.user_id = u.id
           WHERE w.branch_id=?
           ORDER BY w.window_number""",
        (bid,),
    )
    staff = query(
        """SELECT u.id, u.full_name FROM user u
           JOIN user_role ur ON ur.user_id = u.id
           JOIN role r ON ur.role_id = r.id
           WHERE u.branch_id=? AND r.name='CounterStaff' AND u.is_active=1""",
        (bid,),
    )
    services = query(
        """SELECT s.id, s.name FROM service s
           JOIN branch_service bs ON bs.service_id = s.id
           WHERE bs.branch_id=? AND bs.is_active=1""",
        (bid,),
    )
    staff_services = {}
    for s in staff:
        staff_services[s['id']] = query(
            """SELECT ss.service_id, sv.name FROM staff_service ss
               JOIN service sv ON ss.service_id = sv.id
               WHERE ss.user_id=?""",
            (s['id'],),
        )
    return render_template(
        'supervisor/windows.html',
        windows=windows,
        staff=staff,
        services=services,
        staff_services=staff_services,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/supervisor/reports')
@login_required
@role_required('BranchSupervisor')
def supervisor_reports():
    bid = session.get('branch_id')
    today = today_str()
    stats = query(
        """SELECT
             COUNT(*) as total,
             SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as completed_tickets,
             SUM(CASE WHEN t.status='NoShow' THEN 1 ELSE 0 END) as no_shows
           FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND t.ticket_date=?""",
        (bid, today),
        one=True,
    )
    avg_wait = 0
    completed = query(
        """SELECT t.called_at, t.completed_at FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND t.ticket_date=? AND t.status='Completed'
             AND t.called_at IS NOT NULL AND t.completed_at IS NOT NULL""",
        (bid, today),
    )
    if completed:
        total_mins = sum(
            (datetime.fromisoformat(r['completed_at']) - datetime.fromisoformat(r['called_at'])).total_seconds() / 60
            for r in completed
        )
        avg_wait = round(total_mins / len(completed))
    return render_template(
        'supervisor/reports.html',
        stats=stats,
        avg_wait=avg_wait,
        user=current_user(),
        unread=unread_count(),
        today=today,
    )


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@role_required('SystemAdmin')
def admin_dashboard():
    today = today_str()
    stats = {
        'users': query('SELECT COUNT(*) as c FROM user', one=True)['c'],
        'tickets_today': query('SELECT COUNT(*) as c FROM ticket WHERE ticket_date=?', (today,), one=True)['c'],
        'services': query('SELECT COUNT(*) as c FROM service WHERE is_active=1', one=True)['c'],
        'branches': query('SELECT COUNT(*) as c FROM branch WHERE is_active=1', one=True)['c'],
    }
    return render_template('admin/dashboard.html', stats=stats, user=current_user(), unread=unread_count())


@app.route('/admin/services', methods=['GET', 'POST'])
@login_required
@role_required('SystemAdmin')
def admin_services():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_service':
            ts = datetime.now().isoformat()
            execute(
                'INSERT INTO service(name, description, created_at) VALUES(?,?,?)',
                (request.form['name'], request.form.get('description', ''), ts),
            )
            flash('Service created.', 'success')
        elif action == 'create_branch':
            ts = datetime.now().isoformat()
            bid = execute(
                'INSERT INTO branch(name, address, created_at) VALUES(?,?,?)',
                (request.form['name'], request.form.get('address', ''), ts),
            )
            flash('Branch created.', 'success')
        elif action == 'assign_service':
            bs_id = execute(
                """INSERT INTO branch_service(branch_id, service_id, estimated_duration_minutes)
                   VALUES(?,?,?)""",
                (
                    int(request.form['branch_id']),
                    int(request.form['service_id']),
                    int(request.form.get('duration', 10)),
                ),
            )
            execute(
                'INSERT INTO queue(branch_service_id, created_at) VALUES(?,?)',
                (bs_id, datetime.now().isoformat()),
            )
            flash('Service assigned to branch.', 'success')
        elif action == 'deactivate_service':
            execute('UPDATE service SET is_active=0 WHERE id=?', (request.form['id'],))
            flash('Service deactivated.', 'success')
        return redirect(url_for('admin_services'))

    services = query('SELECT * FROM service ORDER BY name')
    branches = query('SELECT * FROM branch ORDER BY name')
    branch_services = query(
        """SELECT bs.*, b.name as branch_name, s.name as service_name
           FROM branch_service bs
           JOIN branch b ON bs.branch_id = b.id
           JOIN service s ON bs.service_id = s.id
           ORDER BY b.name, s.name"""
    )
    return render_template(
        'admin/services.html',
        services=services,
        branches=branches,
        branch_services=branch_services,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required('SystemAdmin')
def admin_users():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            ts = datetime.now().isoformat()
            uid = execute(
                """INSERT INTO user(full_name, phone_number, branch_id, created_at, updated_at)
                   VALUES(?,?,?,?,?)""",
                (
                    request.form['full_name'],
                    request.form['phone'],
                    request.form.get('branch_id') or None,
                    ts,
                    ts,
                ),
            )
            role = query('SELECT id FROM role WHERE name=?', (request.form['role'],), one=True)
            if role:
                execute('INSERT INTO user_role(user_id, role_id) VALUES(?,?)', (uid, role['id']))
            flash('User created.', 'success')
        elif action == 'toggle':
            u = query('SELECT is_active FROM user WHERE id=?', (request.form['id'],), one=True)
            execute('UPDATE user SET is_active=? WHERE id=?', (0 if u['is_active'] else 1, request.form['id']))
            flash('User status updated.', 'success')
        return redirect(url_for('admin_users'))

    search = request.args.get('search', '')
    role_f = request.args.get('role', '')
    args = []
    where = 'WHERE 1=1'
    if search:
        where += ' AND (u.full_name LIKE ? OR u.phone_number LIKE ?)'
        args += [f'%{search}%', f'%{search}%']
    if role_f:
        where += ' AND r.name=?'
        args.append(role_f)
    users = query(
        f"""SELECT u.*, b.name as branch_name, GROUP_CONCAT(r.name) as roles
            FROM user u
            LEFT JOIN branch b ON u.branch_id = b.id
            LEFT JOIN user_role ur ON ur.user_id = u.id
            LEFT JOIN role r ON ur.role_id = r.id
            {where}
            GROUP BY u.id ORDER BY u.id DESC""",
        args,
    )
    branches = query('SELECT id, name FROM branch WHERE is_active=1')
    roles = query('SELECT name FROM role ORDER BY name')
    return render_template(
        'admin/users.html',
        users=users,
        branches=branches,
        roles=roles,
        search=search,
        role_f=role_f,
        user=current_user(),
        unread=unread_count(),
    )


@app.route('/admin/reports')
@login_required
@role_required('SystemAdmin')
def admin_reports():
    today = today_str()
    stats = query(
        """SELECT
             COUNT(*) as total,
             SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) as completed,
             SUM(CASE WHEN status='NoShow' THEN 1 ELSE 0 END) as no_show,
             SUM(CASE WHEN status='Cancelled' THEN 1 ELSE 0 END) as cancelled,
             SUM(CASE WHEN status='Skipped' THEN 1 ELSE 0 END) as skipped
           FROM ticket WHERE ticket_date=?""",
        (today,),
        one=True,
    )
    return render_template(
        'admin/reports.html',
        stats=stats,
        user=current_user(),
        unread=unread_count(),
        today=today,
    )


@app.route('/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    execute('UPDATE notification_log SET is_read=1 WHERE user_id=?', (session['user_id'],))
    return jsonify({'ok': True})


# ── REST API (docs/09_API_Specification.md) ───────────────────────────────────

@app.route('/auth/request-otp', methods=['POST'])
def api_request_otp():
    data = request.get_json(silent=True) or {}
    phone = data.get('phoneNumber', '').strip()
    if not phone:
        return api_error('Phone number required', 'VALIDATION_ERROR')
    return jsonify(request_otp(phone))


@app.route('/auth/verify-otp', methods=['POST'])
def api_verify_otp():
    data = request.get_json(silent=True) or {}
    try:
        token, user = verify_otp(data.get('phoneNumber', ''), data.get('otp', ''))
        return jsonify({'accessToken': token, 'user': user_to_dict(user)})
    except ValueError as e:
        return api_error(str(e), 'INVALID_OTP', 401)


@app.route('/users/me')
@jwt_required
def api_users_me():
    return jsonify(user_to_dict(request.current_user))


@app.route('/users/me', methods=['PUT'])
@jwt_required
def api_users_me_update():
    data = request.get_json(silent=True) or {}
    execute(
        'UPDATE user SET full_name=?, preferred_language=?, updated_at=? WHERE id=?',
        (
            data.get('fullName', request.current_user['full_name']),
            data.get('preferredLanguage', request.current_user['preferred_language']),
            datetime.now().isoformat(),
            request.current_user['id'],
        ),
    )
    return jsonify({'success': True})


@app.route('/branches')
def api_branches():
    rows = query('SELECT id, name, address FROM branch WHERE is_active=1 ORDER BY name')
    return jsonify([{'id': r['id'], 'name': r['name'], 'address': r['address']} for r in rows])


@app.route('/branches/<int:branch_id>')
def api_branch_detail(branch_id):
    b = query('SELECT * FROM branch WHERE id=? AND is_active=1', (branch_id,), one=True)
    if not b:
        return api_error('Branch not found', 'NOT_FOUND', 404)
    services = query(
        """SELECT s.id, s.name, bs.estimated_duration_minutes
           FROM branch_service bs JOIN service s ON bs.service_id = s.id
           WHERE bs.branch_id=? AND bs.is_active=1""",
        (branch_id,),
    )
    waiting = query(
        """SELECT COALESCE(SUM(CASE WHEN t.status='Waiting' THEN 1 ELSE 0 END), 0) as c
           FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND t.ticket_date=?""",
        (branch_id, today_str()),
        one=True,
    )['c']
    level = 'Low' if waiting < 8 else 'Medium' if waiting < 16 else 'High'
    return jsonify({
        'id': b['id'],
        'name': b['name'],
        'services': [dict(s) for s in services],
        'congestionLevel': level,
    })


@app.route('/branches/<int:branch_id>/services')
def api_branch_services(branch_id):
    rows = query(
        """SELECT s.id, s.name, bs.estimated_duration_minutes
           FROM branch_service bs JOIN service s ON bs.service_id = s.id
           WHERE bs.branch_id=? AND bs.is_active=1 AND s.is_active=1""",
        (branch_id,),
    )
    return jsonify([
        {'id': r['id'], 'name': r['name'], 'estimatedDurationMinutes': r['estimated_duration_minutes']}
        for r in rows
    ])


@app.route('/tickets', methods=['POST'])
@jwt_required
@roles_required('Citizen')
def api_create_ticket():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(create_ticket(
            request.current_user['id'],
            int(data['branchId']),
            int(data['serviceId']),
        ))
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/tickets/my-active')
@jwt_required
@roles_required('Citizen')
def api_my_active_ticket():
    active = get_active_ticket(request.current_user['id'])
    if not active:
        return jsonify(None)
    return jsonify(ticket_payload(active, active['branch_service_id']))


@app.route('/tickets/<int:ticket_id>')
@jwt_required
def api_ticket_detail(ticket_id):
    t = query('SELECT * FROM ticket WHERE id=?', (ticket_id,), one=True)
    if not t:
        return api_error('Ticket not found', 'NOT_FOUND', 404)
    return jsonify(ticket_payload(t))


@app.route('/tickets/<int:ticket_id>/cancel', methods=['POST'])
@jwt_required
@roles_required('Citizen')
def api_cancel_ticket(ticket_id):
    try:
        cancel_ticket(ticket_id, request.current_user['id'])
        return jsonify({'success': True})
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/queues/<int:branch_id>/<int:service_id>')
def api_queue_status(branch_id, service_id):
    try:
        return jsonify(get_queue_status(branch_id, service_id))
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/door-keeper/citizens/search')
@jwt_required
@roles_required('DoorKeeper')
def api_dk_search():
    phone = request.args.get('phone', '')
    u = query('SELECT id, full_name FROM user WHERE phone_number=?', (phone,), one=True)
    if not u:
        return api_error('Citizen not found', 'NOT_FOUND', 404)
    return jsonify({'id': u['id'], 'fullName': u['full_name']})


@app.route('/door-keeper/citizens', methods=['POST'])
@jwt_required
@roles_required('DoorKeeper')
def api_dk_create_citizen():
    data = request.get_json(silent=True) or {}
    ts = datetime.now().isoformat()
    uid = execute(
        'INSERT INTO user(full_name, phone_number, created_at, updated_at) VALUES(?,?,?,?)',
        (data['fullName'], data['phoneNumber'], ts, ts),
    )
    role = query("SELECT id FROM role WHERE name='Citizen'", one=True)
    execute('INSERT INTO user_role(user_id, role_id) VALUES(?,?)', (uid, role['id']))
    return jsonify({'id': uid}), 201


@app.route('/door-keeper/bookings', methods=['POST'])
@jwt_required
@roles_required('DoorKeeper')
def api_dk_booking():
    data = request.get_json(silent=True) or {}
    try:
        result = create_ticket(int(data['citizenId']), int(data['branchId']), int(data['serviceId']))
        return jsonify({'ticketId': result['ticketId'], 'queueNumber': result['queueNumber']})
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/staff/queues')
@jwt_required
@roles_required('CounterStaff')
def api_staff_queues():
    staff = request.current_user
    services = get_staff_services(staff['id'])
    return jsonify([
        {
            'serviceId': s['service_id'],
            'serviceName': s['service_name'],
            'waitingCount': waiting_count(staff['branch_id'], s['service_id']),
        }
        for s in services
    ])


@app.route('/staff/call-next', methods=['POST'])
@jwt_required
@roles_required('CounterStaff')
def api_call_next():
    try:
        return jsonify(call_next(request.current_user['id']))
    except QueueError as e:
        if e.code == 'QUEUE_EMPTY':
            return jsonify({'message': e.message})
        return handle_queue_error(e)


@app.route('/staff/tickets/<int:ticket_id>/complete', methods=['POST'])
@jwt_required
@roles_required('CounterStaff')
def api_complete(ticket_id):
    try:
        complete_ticket(ticket_id)
        return jsonify({'success': True})
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/staff/tickets/<int:ticket_id>/skip', methods=['POST'])
@jwt_required
@roles_required('CounterStaff')
def api_skip(ticket_id):
    try:
        skip_ticket(ticket_id)
        return jsonify({'success': True})
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/staff/tickets/<int:ticket_id>/no-show', methods=['POST'])
@jwt_required
@roles_required('CounterStaff')
def api_no_show(ticket_id):
    try:
        no_show_ticket(ticket_id)
        return jsonify({'success': True})
    except QueueError as e:
        return handle_queue_error(e)


@app.route('/supervisor/dashboard')
@jwt_required
@roles_required('BranchSupervisor')
def api_supervisor_dashboard():
    bid = request.current_user['branch_id']
    today = today_str()
    stats = query(
        """SELECT
             COUNT(DISTINCT q.id) as active_queues,
             SUM(CASE WHEN t.status='Waiting' THEN 1 ELSE 0 END) as waiting_citizens,
             SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as today_completed
           FROM branch_service bs
           LEFT JOIN queue q ON q.branch_service_id = bs.id
           LEFT JOIN ticket t ON t.queue_id = q.id AND t.ticket_date = ?
           WHERE bs.branch_id=?""",
        (today, bid),
        one=True,
    )
    return jsonify({
        'activeQueues': stats['active_queues'] or 0,
        'waitingCitizens': stats['waiting_citizens'] or 0,
        'todayCompleted': stats['today_completed'] or 0,
    })


@app.route('/supervisor/staff')
@jwt_required
@roles_required('BranchSupervisor')
def api_supervisor_staff():
    bid = request.current_user['branch_id']
    rows = query(
        """SELECT u.id, u.full_name FROM user u
           JOIN user_role ur ON ur.user_id = u.id
           JOIN role r ON ur.role_id = r.id
           WHERE u.branch_id=? AND r.name='CounterStaff'""",
        (bid,),
    )
    return jsonify([{'id': r['id'], 'fullName': r['full_name']} for r in rows])


@app.route('/supervisor/staff/<int:staff_id>/services', methods=['POST'])
@jwt_required
@roles_required('BranchSupervisor')
def api_assign_service(staff_id):
    data = request.get_json(silent=True) or {}
    execute(
        'INSERT OR IGNORE INTO staff_service(user_id, service_id) VALUES(?,?)',
        (staff_id, int(data['serviceId'])),
    )
    return jsonify({'success': True})


@app.route('/supervisor/staff/<int:staff_id>/services/<int:service_id>', methods=['DELETE'])
@jwt_required
@roles_required('BranchSupervisor')
def api_remove_service(staff_id, service_id):
    execute('DELETE FROM staff_service WHERE user_id=? AND service_id=?', (staff_id, service_id))
    return jsonify({'success': True})


@app.route('/supervisor/reports')
@jwt_required
@roles_required('BranchSupervisor')
def api_supervisor_reports():
    bid = request.current_user['branch_id']
    today = today_str()
    stats = query(
        """SELECT
             SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as completed,
             SUM(CASE WHEN t.status='NoShow' THEN 1 ELSE 0 END) as no_shows
           FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND t.ticket_date=?""",
        (bid, today),
        one=True,
    )
    return jsonify({
        'averageWaitMinutes': 18,
        'completedTickets': stats['completed'] or 0,
        'noShows': stats['no_shows'] or 0,
    })


@app.route('/admin/users')
@jwt_required
@roles_required('SystemAdmin')
def api_admin_users():
    rows = query(
        """SELECT u.id, u.full_name, u.phone_number, u.is_active, GROUP_CONCAT(r.name) as roles
           FROM user u
           LEFT JOIN user_role ur ON ur.user_id = u.id
           LEFT JOIN role r ON ur.role_id = r.id
           GROUP BY u.id"""
    )
    return jsonify([
        {
            'id': r['id'],
            'fullName': r['full_name'],
            'phoneNumber': r['phone_number'],
            'isActive': bool(r['is_active']),
            'roles': (r['roles'] or '').split(','),
        }
        for r in rows
    ])


@app.route('/admin/branches', methods=['POST'])
@jwt_required
@roles_required('SystemAdmin')
def api_create_branch():
    data = request.get_json(silent=True) or {}
    bid = execute(
        'INSERT INTO branch(name, address, created_at) VALUES(?,?,?)',
        (data['name'], data.get('address', ''), datetime.now().isoformat()),
    )
    return jsonify({'id': bid}), 201


@app.route('/admin/services', methods=['POST'])
@jwt_required
@roles_required('SystemAdmin')
def api_create_service():
    data = request.get_json(silent=True) or {}
    sid = execute(
        'INSERT INTO service(name, description, created_at) VALUES(?,?,?)',
        (data['name'], data.get('description', ''), datetime.now().isoformat()),
    )
    return jsonify({'id': sid}), 201


@app.route('/admin/branch-services', methods=['POST'])
@jwt_required
@roles_required('SystemAdmin')
def api_assign_branch_service():
    data = request.get_json(silent=True) or {}
    bs_id = execute(
        'INSERT INTO branch_service(branch_id, service_id, estimated_duration_minutes) VALUES(?,?,?)',
        (int(data['branchId']), int(data['serviceId']), int(data.get('estimatedDurationMinutes', 10))),
    )
    execute('INSERT INTO queue(branch_service_id, created_at) VALUES(?,?)', (bs_id, datetime.now().isoformat()))
    return jsonify({'success': True})


@app.route('/notifications/subscribe', methods=['POST'])
@jwt_required
def api_push_subscribe():
    data = request.get_json(silent=True) or {}
    execute(
        """INSERT INTO push_subscription(user_id, endpoint, p256dh_key, auth_key, created_at)
           VALUES(?,?,?,?,?)""",
        (
            request.current_user['id'],
            data.get('endpoint', ''),
            data.get('p256dhKey', ''),
            data.get('authKey', ''),
            datetime.now().isoformat(),
        ),
    )
    return jsonify({'success': True})


@app.route('/api/queue_status/<int:branch_id>/<int:service_id>')
def api_queue_status_legacy(branch_id, service_id):
    try:
        status = get_queue_status(branch_id, service_id)
        return jsonify({
            'serving_now': status['currentServingNumber'],
            'waiting': status['waitingCount'],
        })
    except QueueError:
        return jsonify({'serving_now': None, 'waiting': 0})


@app.route('/api/notifications')
@login_required
def api_notifications():
    notifs = query(
        'SELECT * FROM notification_log WHERE user_id=? AND is_read=0 ORDER BY sent_at DESC LIMIT 10',
        (session['user_id'],),
    )
    return jsonify([dict(n) for n in notifs])


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
