from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime, timedelta
from functools import wraps
from db import init_db, query, execute
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "govqueue-secret-2024"

# ── Helpers ──────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash("Access denied.", "error")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def current_user():
    if 'user_id' not in session:
        return None
    return query("SELECT * FROM user WHERE id=?", (session['user_id'],), one=True)

def unread_count():
    if 'user_id' not in session:
        return 0
    r = query("SELECT COUNT(*) as c FROM notification WHERE user_id=? AND is_read=0", (session['user_id'],), one=True)
    return r['c'] if r else 0

@app.context_processor
def inject_globals():
    return {'unread': unread_count()}

def row_to_dict(row):
    return {k: row[k] for k in row.keys()}

def generate_queue_number(branch_service_id, slot_date):
    r = query("""SELECT COUNT(*) as c FROM booking b
                 JOIN time_slot ts ON b.time_slot_id=ts.id
                 WHERE ts.branch_service_id=? AND ts.slot_date=?
                 AND b.status NOT IN ('cancelled')""",
              (branch_service_id, slot_date), one=True)
    n = (r['c'] if r else 0) + 1
    return f"Q{n:03d}"

def provision_service_branches(service_id, duration_minutes):
    """Link a service to all active branches and create bookable time slots."""
    branches = query("SELECT id FROM branch WHERE is_active=1")
    for branch in branches:
        existing = query(
            "SELECT id FROM branch_service WHERE branch_id=? AND service_id=?",
            (branch['id'], service_id), one=True)
        bs_id = existing['id'] if existing else execute(
            "INSERT INTO branch_service(branch_id,service_id) VALUES(?,?)",
            (branch['id'], service_id))
        if query("SELECT id FROM time_slot WHERE branch_service_id=? LIMIT 1", (bs_id,), one=True):
            continue
        for d_off in range(3):
            slot_date = (date.today() + timedelta(days=d_off)).isoformat()
            for hour in range(8, 16):
                execute(
                    "INSERT INTO time_slot(branch_service_id,slot_date,start_time,end_time,max_capacity,booked_count) VALUES(?,?,?,?,?,?)",
                    (bs_id, slot_date, f"{hour:02d}:00", f"{hour:02d}:{duration_minutes:02d}", 5, 0))

def check_turn_notifications():
    """Create notifications for citizens who are 2 positions away."""
    bookings = query("""
        SELECT b.id, b.citizen_id, b.queue_number, b.time_slot_id,
               ts.branch_service_id, ts.slot_date
        FROM booking b
        JOIN time_slot ts ON b.time_slot_id=ts.id
        WHERE b.status='booked' AND ts.slot_date=?
    """, (date.today().isoformat(),))
    for bk in bookings:
        # count how many are before this booking in same service today
        ahead = query("""
            SELECT COUNT(*) as c FROM booking b2
            JOIN time_slot ts2 ON b2.time_slot_id=ts2.id
            WHERE ts2.branch_service_id=? AND ts2.slot_date=?
            AND b2.status IN ('arrived','serving')
            AND b2.queue_number < ?
        """, (bk['branch_service_id'], bk['slot_date'], bk['queue_number']), one=True)
        if ahead and ahead['c'] <= 2:
            existing = query("SELECT id FROM notification WHERE booking_id=? AND type='turn_approaching'",
                             (bk['id'],), one=True)
            if not existing:
                execute("INSERT INTO notification(user_id,booking_id,type,message,sent_at) VALUES(?,?,?,?,?)",
                        (bk['citizen_id'], bk['id'], 'turn_approaching',
                         f"Your turn is approaching! You are #{ahead['c']+1} in queue.",
                         datetime.now().isoformat()))

# ── Public / Auth ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    branches = query("SELECT b.*, o.name as org_name FROM branch b JOIN organization o ON b.organization_id=o.id WHERE b.is_active=1")
    services = query("SELECT * FROM service WHERE is_active=1")
    # congestion per branch_service
    today = date.today().isoformat()
    congestion = query("""
        SELECT bs.id, b.name as branch_name, s.name as service_name,
               s.estimated_duration_minutes,
               COALESCE(SUM(CASE WHEN bk.status IN ('booked','arrived') THEN 1 ELSE 0 END),0) as waiting
        FROM branch_service bs
        JOIN branch b ON bs.branch_id=b.id
        JOIN service s ON bs.service_id=s.id
        LEFT JOIN time_slot ts ON ts.branch_service_id=bs.id AND ts.slot_date=?
        LEFT JOIN booking bk ON bk.time_slot_id=ts.id
        WHERE bs.is_available=1 AND s.is_active=1
        GROUP BY bs.id
    """, (today,))
    return render_template('index.html', branches=branches, services=services,
                           congestion=congestion, user=current_user(), unread=unread_count())

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone'].strip()
        pwd = request.form['password']
        user = query("SELECT * FROM user WHERE phone=? AND is_active=1", (phone,), one=True)
        if user and check_password_hash(user['password_hash'], pwd):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['full_name']
            session['branch_id'] = user['branch_id']
            flash(f"Welcome, {user['full_name']}!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid phone or password.", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['full_name'].strip()
        phone = request.form['phone'].strip()
        national_id = request.form.get('national_id','').strip()
        pwd = request.form['password']
        cpwd = request.form['confirm_password']
        if pwd != cpwd:
            flash("Passwords do not match.", "error")
            return render_template('register.html')
        if query("SELECT id FROM user WHERE phone=?", (phone,), one=True):
            flash("Phone number already registered.", "error")
            return render_template('register.html')
        execute("INSERT INTO user(full_name,phone,password_hash,national_id,role) VALUES(?,?,?,?,?)",
                (name, phone, generate_password_hash(pwd), national_id, "citizen"))
        flash("Registered successfully! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'citizen':
        return redirect(url_for('citizen_dashboard'))
    elif role == 'staff':
        return redirect(url_for('staff_dashboard'))
    elif role == 'validation_staff':
        return redirect(url_for('validation_dashboard'))
    elif role == 'supervisor':
        return redirect(url_for('supervisor_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('index'))

# ── Citizen ───────────────────────────────────────────────────────────────────

@app.route('/citizen')
@login_required
@role_required('citizen')
def citizen_dashboard():
    uid = session['user_id']
    active = query("""SELECT bk.*, s.name as service_name, s.name_ar,
                             ts.slot_date, ts.start_time, b.name as branch_name
                      FROM booking bk
                      JOIN time_slot ts ON bk.time_slot_id=ts.id
                      JOIN branch_service bs ON bk.branch_service_id=bs.id
                      JOIN service s ON bs.service_id=s.id
                      JOIN branch b ON bs.branch_id=b.id
                      WHERE bk.citizen_id=? AND bk.status NOT IN ('completed','cancelled','no_show','skipped')
                      ORDER BY ts.slot_date, ts.start_time LIMIT 1""", (uid,), one=True)
    if active:
        position = query("""SELECT COUNT(*) as c FROM booking b2
                            JOIN time_slot ts2 ON b2.time_slot_id=ts2.id
                            WHERE ts2.branch_service_id=(
                                SELECT branch_service_id FROM time_slot WHERE id=?
                            ) AND ts2.slot_date=? AND b2.status IN ('booked','arrived')
                            AND b2.queue_number < ?""",
                         (active['time_slot_id'], active['slot_date'], active['queue_number']), one=True)
        active = dict(active)
        active['position'] = position['c'] + 1 if position else 1
    notifs = query("SELECT * FROM notification WHERE user_id=? AND is_read=0 ORDER BY sent_at DESC LIMIT 5", (uid,))
    return render_template('citizen/dashboard.html', active=active, notifs=notifs,
                           user=current_user(), unread=unread_count())

@app.route('/citizen/book', methods=['GET','POST'])
@login_required
@role_required('citizen')
def citizen_book():
    uid = session['user_id']
    # Check single active booking rule
    existing = query("""SELECT id FROM booking WHERE citizen_id=?
                        AND status NOT IN ('completed','cancelled','no_show','skipped')""", (uid,), one=True)
    if existing:
        flash("You already have an active booking. Complete or cancel it first.", "warning")
        return redirect(url_for('citizen_bookings'))

    if request.method == 'POST':
        bs_id = request.form['branch_service_id']
        slot_id = request.form['time_slot_id']
        today = date.today().isoformat()
        slot = query("SELECT * FROM time_slot WHERE id=? AND booked_count < max_capacity", (slot_id,), one=True)
        if not slot:
            flash("Slot no longer available.", "error")
            return redirect(url_for('citizen_book'))
        qnum = generate_queue_number(bs_id, slot['slot_date'])
        booking_id = execute("""INSERT INTO booking(citizen_id,time_slot_id,branch_service_id,
                                                     queue_number,status,booked_at) VALUES(?,?,?,?,?,?)""",
                             (uid, slot_id, bs_id, qnum, 'booked', datetime.now().isoformat()))
        execute("UPDATE time_slot SET booked_count=booked_count+1 WHERE id=?", (slot_id,))
        execute("INSERT INTO notification(user_id,booking_id,type,message,sent_at) VALUES(?,?,?,?,?)",
                (uid, booking_id, 'booking_confirmed',
                 f"Booking confirmed! Your queue number is {qnum}.",
                 datetime.now().isoformat()))
        flash(f"Booked! Your queue number is {qnum}.", "success")
        return redirect(url_for('citizen_dashboard'))

    branches = query("""SELECT DISTINCT b.id, b.name FROM branch b
                        JOIN branch_service bs ON bs.branch_id=b.id
                        WHERE bs.is_available=1 AND b.is_active=1""")
    branch_id = request.args.get('branch_id', branches[0]['id'] if branches else None)
    services = query("""SELECT bs.id as bs_id, s.id, s.name, s.name_ar, s.estimated_duration_minutes
                        FROM branch_service bs JOIN service s ON bs.service_id=s.id
                        WHERE bs.branch_id=? AND bs.is_available=1 AND s.is_active=1""", (branch_id,)) if branch_id else []
    sel_bs = request.args.get('bs_id', services[0]['bs_id'] if services else None)
    today = date.today().isoformat()
    slots = query("""SELECT ts.*, ts.max_capacity - ts.booked_count as available
                     FROM time_slot ts WHERE ts.branch_service_id=?
                     AND ts.slot_date >= ? AND ts.booked_count < ts.max_capacity
                     ORDER BY ts.slot_date, ts.start_time LIMIT 20""",
                  (sel_bs, today)) if sel_bs else []
    return render_template('citizen/book.html', branches=branches, services=services,
                           slots=slots, sel_bs=sel_bs, branch_id=branch_id,
                           user=current_user(), unread=unread_count())

@app.route('/citizen/bookings')
@login_required
@role_required('citizen')
def citizen_bookings():
    uid = session['user_id']
    bookings = query("""SELECT bk.*, s.name as service_name, ts.slot_date,
                               ts.start_time, b.name as branch_name
                        FROM booking bk
                        JOIN time_slot ts ON bk.time_slot_id=ts.id
                        JOIN branch_service bs ON bk.branch_service_id=bs.id
                        JOIN service s ON bs.service_id=s.id
                        JOIN branch b ON bs.branch_id=b.id
                        WHERE bk.citizen_id=?
                        ORDER BY bk.booked_at DESC""", (uid,))
    return render_template('citizen/bookings.html', bookings=bookings,
                           user=current_user(), unread=unread_count())

@app.route('/citizen/bookings/<int:bid>/cancel', methods=['POST'])
@login_required
@role_required('citizen')
def cancel_booking(bid):
    uid = session['user_id']
    bk = query("SELECT * FROM booking WHERE id=? AND citizen_id=?", (bid, uid), one=True)
    if bk and bk['status'] in ('booked',):
        execute("UPDATE booking SET status='cancelled' WHERE id=?", (bid,))
        execute("UPDATE time_slot SET booked_count=MAX(booked_count-1,0) WHERE id=?", (bk['time_slot_id'],))
        flash("Booking cancelled.", "success")
    else:
        flash("Cannot cancel this booking.", "error")
    return redirect(url_for('citizen_bookings'))

@app.route('/citizen/track')
@login_required
@role_required('citizen')
def citizen_track():
    uid = session['user_id']
    bk = query("""SELECT bk.*, s.name as service_name, s.estimated_duration_minutes,
                         ts.slot_date, ts.start_time, b.name as branch_name
                  FROM booking bk
                  JOIN time_slot ts ON bk.time_slot_id=ts.id
                  JOIN branch_service bs ON bk.branch_service_id=bs.id
                  JOIN service s ON bs.service_id=s.id
                  JOIN branch b ON bs.branch_id=b.id
                  WHERE bk.citizen_id=? AND bk.status NOT IN ('completed','cancelled','no_show','skipped')
                  ORDER BY ts.slot_date, ts.start_time LIMIT 1""", (uid,), one=True)
    serving_now = None
    position = None
    if bk:
        bs_id = bk['branch_service_id']
        serving = query("""SELECT bk2.queue_number FROM booking bk2
                           JOIN time_slot ts2 ON bk2.time_slot_id=ts2.id
                           WHERE ts2.branch_service_id=? AND ts2.slot_date=? AND bk2.status='serving'
                           ORDER BY bk2.queue_number LIMIT 1""",
                        (bs_id, bk['slot_date']), one=True)
        serving_now = serving['queue_number'] if serving else "—"
        ahead = query("""SELECT COUNT(*) as c FROM booking b2
                         JOIN time_slot ts2 ON b2.time_slot_id=ts2.id
                         WHERE ts2.branch_service_id=? AND ts2.slot_date=?
                         AND b2.status IN ('booked','arrived')
                         AND b2.queue_number < ?""",
                      (bs_id, bk['slot_date'], bk['queue_number']), one=True)
        position = (ahead['c'] if ahead else 0) + 1
    check_turn_notifications()
    return render_template('citizen/track.html', bk=bk, serving_now=serving_now,
                           position=position, user=current_user(), unread=unread_count())

@app.route('/citizen/profile', methods=['GET','POST'])
@login_required
@role_required('citizen')
def citizen_profile():
    uid = session['user_id']
    if request.method == 'POST':
        name = request.form['full_name'].strip()
        lang = request.form.get('preferred_language','en')
        execute("UPDATE user SET full_name=?, preferred_language=? WHERE id=?", (name, lang, uid))
        if request.form.get('new_password'):
            if check_password_hash(query("SELECT password_hash FROM user WHERE id=?", (uid,), one=True)['password_hash'],
                                   request.form['current_password']):
                execute("UPDATE user SET password_hash=? WHERE id=?",
                        (generate_password_hash(request.form['new_password']), uid))
                flash("Password updated.", "success")
            else:
                flash("Current password incorrect.", "error")
        session['name'] = name
        flash("Profile updated.", "success")
    u = current_user()
    return render_template('citizen/profile.html', u=u, user=u, unread=unread_count())

@app.route('/notifications/read', methods=['GET', 'POST'])
@login_required
def mark_notifications_read():
    execute("UPDATE notification SET is_read=1 WHERE user_id=?", (session['user_id'],))
    if request.accept_mimetypes.best == 'application/json':
        return jsonify({"ok": True})
    flash("Notifications marked as read.", "success")
    return redirect(request.referrer or url_for('dashboard'))

# ── Counter Staff ─────────────────────────────────────────────────────────────

@app.route('/staff')
@login_required
@role_required('staff')
def staff_dashboard():
    uid = session['user_id']
    bid = session.get('branch_id')
    today = date.today().isoformat()
    # Find assigned window
    win = query("""SELECT w.*, wa.id as wa_id, s.name as service_name
                   FROM window_assignment wa
                   JOIN window w ON wa.window_id=w.id
                   LEFT JOIN service s ON w.service_id=s.id
                   WHERE wa.staff_id=? AND wa.assigned_date=? AND wa.is_active=1 LIMIT 1""",
                (uid, today), one=True)
    serving = None
    queue = []
    if win:
        serving = query("""SELECT bk.*, u.full_name FROM booking bk
                           JOIN time_slot ts ON bk.time_slot_id=ts.id
                           JOIN user u ON bk.citizen_id=u.id
                           WHERE ts.branch_service_id IN (
                               SELECT bs.id FROM branch_service bs
                               WHERE bs.branch_id=? AND bs.service_id=?
                           ) AND ts.slot_date=? AND bk.status='serving'
                           ORDER BY bk.queue_number LIMIT 1""",
                        (bid, win['service_id'], today), one=True)
        queue = query("""SELECT bk.*, u.full_name FROM booking bk
                         JOIN time_slot ts ON bk.time_slot_id=ts.id
                         JOIN user u ON bk.citizen_id=u.id
                         WHERE ts.branch_service_id IN (
                             SELECT bs.id FROM branch_service bs
                             WHERE bs.branch_id=? AND bs.service_id=?
                         ) AND ts.slot_date=? AND bk.status='arrived'
                         ORDER BY bk.queue_number LIMIT 10""",
                      (bid, win['service_id'], today))
    stats = query("""SELECT
                        SUM(CASE WHEN bk.status='completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN bk.status='no_show' THEN 1 ELSE 0 END) as no_show,
                        SUM(CASE WHEN bk.status='skipped' THEN 1 ELSE 0 END) as skipped
                     FROM booking bk JOIN time_slot ts ON bk.time_slot_id=ts.id
                     WHERE ts.branch_service_id IN (
                         SELECT bs.id FROM branch_service bs WHERE bs.branch_id=?
                     ) AND ts.slot_date=?""", (bid, today), one=True)
    return render_template('staff/dashboard.html', win=win, serving=serving,
                           queue=queue, stats=stats, user=current_user(), unread=unread_count())

@app.route('/staff/call_next', methods=['POST'])
@login_required
@role_required('staff')
def call_next():
    bid = session['branch_id']
    today = date.today().isoformat()
    uid = session['user_id']
    win = query("""SELECT w.* FROM window_assignment wa JOIN window w ON wa.window_id=w.id
                   WHERE wa.staff_id=? AND wa.assigned_date=? AND wa.is_active=1 LIMIT 1""",
                (uid, today), one=True)
    if not win:
        flash("No window assigned.", "error")
        return redirect(url_for('staff_dashboard'))
    # Complete any currently serving
    execute("""UPDATE booking SET status='completed', completed_at=?
               WHERE status='serving' AND time_slot_id IN (
                   SELECT ts.id FROM time_slot ts
                   JOIN branch_service bs ON ts.branch_service_id=bs.id
                   WHERE bs.branch_id=? AND bs.service_id=? AND ts.slot_date=?
               )""", (datetime.now().isoformat(), bid, win['service_id'], today))
    # Get next arrived
    nxt = query("""SELECT bk.id FROM booking bk
                   JOIN time_slot ts ON bk.time_slot_id=ts.id
                   JOIN branch_service bs ON ts.branch_service_id=bs.id
                   WHERE bs.branch_id=? AND bs.service_id=? AND ts.slot_date=?
                   AND bk.status='arrived' ORDER BY bk.queue_number LIMIT 1""",
                (bid, win['service_id'], today), one=True)
    if nxt:
        execute("UPDATE booking SET status='serving', served_at=? WHERE id=?",
                (datetime.now().isoformat(), nxt['id']))
        check_turn_notifications()
        flash("Next citizen called.", "success")
    else:
        flash("No citizens waiting.", "info")
    return redirect(url_for('staff_dashboard'))

@app.route('/staff/mark/<int:bid2>/<status>', methods=['POST'])
@login_required
@role_required('staff')
def mark_booking(bid2, status):
    if status in ('completed','no_show','skipped'):
        ts = {}
        if status == 'completed':
            ts = {'completed_at': datetime.now().isoformat()}
            execute("UPDATE booking SET status=?, completed_at=? WHERE id=?",
                    (status, datetime.now().isoformat(), bid2))
        else:
            execute("UPDATE booking SET status=? WHERE id=?", (status, bid2))
    flash(f"Marked as {status}.", "success")
    return redirect(url_for('staff_dashboard'))

# ── Validation Staff ──────────────────────────────────────────────────────────

@app.route('/validation')
@login_required
@role_required('validation_staff')
def validation_dashboard():
    bid = session['branch_id']
    today = date.today().isoformat()
    bookings = query("""SELECT bk.*, u.full_name, u.phone, s.name as service_name, ts.start_time
                        FROM booking bk
                        JOIN user u ON bk.citizen_id=u.id
                        JOIN time_slot ts ON bk.time_slot_id=ts.id
                        JOIN branch_service bs ON bk.branch_service_id=bs.id
                        JOIN service s ON bs.service_id=s.id
                        WHERE bs.branch_id=? AND ts.slot_date=? AND bk.status='booked'
                        ORDER BY ts.start_time, bk.queue_number""", (bid, today))
    return render_template('staff/validation.html', bookings=bookings,
                           user=current_user(), unread=unread_count(), today=today)

@app.route('/validation/mark/<int:bid2>/<status>', methods=['POST'])
@login_required
@role_required('validation_staff')
def validate_booking(bid2, status):
    if status == 'arrived':
        execute("UPDATE booking SET status='arrived', arrived_at=? WHERE id=?",
                (datetime.now().isoformat(), bid2))
        flash("Citizen marked as arrived.", "success")
    elif status == 'no_show':
        execute("UPDATE booking SET status='no_show' WHERE id=?", (bid2,))
        flash("Marked as no-show.", "warning")
    return redirect(url_for('validation_dashboard'))

# ── Branch Supervisor ─────────────────────────────────────────────────────────

@app.route('/supervisor')
@login_required
@role_required('supervisor')
def supervisor_dashboard():
    bid = session['branch_id']
    today = date.today().isoformat()
    windows = query("""SELECT w.*, s.name as service_name,
                              wa.staff_id, u.full_name as staff_name
                       FROM window w
                       LEFT JOIN service s ON w.service_id=s.id
                       LEFT JOIN window_assignment wa ON wa.window_id=w.id AND wa.assigned_date=? AND wa.is_active=1
                       LEFT JOIN user u ON wa.staff_id=u.id
                       WHERE w.branch_id=?
                       ORDER BY w.window_number""", (today, bid))
    stats = query("""SELECT
                        SUM(CASE WHEN bk.status IN ('booked','arrived') THEN 1 ELSE 0 END) as waiting,
                        SUM(CASE WHEN bk.status='serving' THEN 1 ELSE 0 END) as serving,
                        SUM(CASE WHEN bk.status='completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN bk.status='no_show' THEN 1 ELSE 0 END) as no_show
                     FROM booking bk JOIN time_slot ts ON bk.time_slot_id=ts.id
                     JOIN branch_service bs ON ts.branch_service_id=bs.id
                     WHERE bs.branch_id=? AND ts.slot_date=?""", (bid, today), one=True)
    return render_template('supervisor/dashboard.html', windows=windows, stats=stats,
                           user=current_user(), unread=unread_count(), today=today)

@app.route('/supervisor/windows')
@login_required
@role_required('supervisor')
def supervisor_windows():
    bid = session['branch_id']
    today = date.today().isoformat()
    windows = query("""SELECT w.*, s.name as service_name,
                              wa.id as wa_id, wa.staff_id, u.full_name as staff_name
                       FROM window w
                       LEFT JOIN service s ON w.service_id=s.id
                       LEFT JOIN window_assignment wa ON wa.window_id=w.id AND wa.assigned_date=? AND wa.is_active=1
                       LEFT JOIN user u ON wa.staff_id=u.id
                       WHERE w.branch_id=?""", (today, bid))
    staff = query("SELECT id, full_name FROM user WHERE branch_id=? AND role='staff' AND is_active=1", (bid,))
    services = query("""SELECT s.* FROM service s
                        JOIN branch_service bs ON bs.service_id=s.id
                        WHERE bs.branch_id=? AND bs.is_available=1""", (bid,))
    return render_template('supervisor/windows.html', windows=windows, staff=staff,
                           services=services, user=current_user(), unread=unread_count(), today=today)

@app.route('/supervisor/window/<int:wid>/toggle', methods=['POST'])
@login_required
@role_required('supervisor')
def toggle_window(wid):
    w = query("SELECT * FROM window WHERE id=?", (wid,), one=True)
    if w:
        new_status = 'closed' if w['status'] == 'open' else 'open'
        execute("UPDATE window SET status=? WHERE id=?", (new_status, wid))
        flash(f"Window {new_status}.", "success")
    return redirect(url_for('supervisor_windows'))

@app.route('/supervisor/window/<int:wid>/assign', methods=['POST'])
@login_required
@role_required('supervisor')
def assign_window(wid):
    staff_id = request.form['staff_id']
    today = date.today().isoformat()
    execute("UPDATE window_assignment SET is_active=0 WHERE window_id=? AND assigned_date=?", (wid, today))
    execute("INSERT INTO window_assignment(window_id,staff_id,assigned_date,is_active) VALUES(?,?,?,?)",
            (wid, staff_id, today, 1))
    flash("Staff assigned.", "success")
    return redirect(url_for('supervisor_windows'))

# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    today = date.today().isoformat()
    stats = {
        'users': query("SELECT COUNT(*) as c FROM user WHERE role='citizen'", one=True)['c'],
        'bookings_today': query("SELECT COUNT(*) as c FROM booking bk JOIN time_slot ts ON bk.time_slot_id=ts.id WHERE ts.slot_date=?", (today,), one=True)['c'],
        'services': query("SELECT COUNT(*) as c FROM service WHERE is_active=1", one=True)['c'],
        'branches': query("SELECT COUNT(*) as c FROM branch WHERE is_active=1", one=True)['c'],
    }
    return render_template('admin/dashboard.html', stats=stats,
                           user=current_user(), unread=unread_count())

@app.route('/admin/services', methods=['GET','POST'])
@login_required
@role_required('admin')
def admin_services():
    org = query("SELECT id FROM organization LIMIT 1", one=True)
    if not org:
        flash("No organization configured. Please run seed.py first.", "error")
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            duration = int(request.form.get('duration', 10))
            service_id = execute(
                "INSERT INTO service(organization_id,name,name_ar,estimated_duration_minutes) VALUES(?,?,?,?)",
                (org['id'], request.form['name'], request.form.get('name_ar',''), duration))
            provision_service_branches(service_id, duration)
            flash("Service created and made available for booking.", "success")
        elif action == 'edit':
            execute("UPDATE service SET name=?, name_ar=?, estimated_duration_minutes=? WHERE id=?",
                    (request.form['name'], request.form.get('name_ar',''), request.form.get('duration',10), request.form['id']))
            flash("Service updated.", "success")
        elif action == 'delete':
            service_id = request.form['id']
            execute("UPDATE service SET is_active=0 WHERE id=?", (service_id,))
            execute("UPDATE branch_service SET is_available=0 WHERE service_id=?", (service_id,))
            flash("Service deleted.", "success")
        return redirect(url_for('admin_services'))
    orphans = query("""SELECT s.id, s.estimated_duration_minutes FROM service s
                       LEFT JOIN branch_service bs ON bs.service_id=s.id
                       WHERE s.is_active=1 AND s.organization_id=?
                       GROUP BY s.id HAVING COUNT(bs.id)=0""", (org['id'],))
    for svc in orphans:
        provision_service_branches(svc['id'], svc['estimated_duration_minutes'])
    services = query("""SELECT s.*, COUNT(DISTINCT bs.id) as branch_count
                        FROM service s LEFT JOIN branch_service bs ON bs.service_id=s.id
                        WHERE s.organization_id=? AND s.is_active=1
                        GROUP BY s.id ORDER BY s.name""", (org['id'],))
    return render_template('admin/services.html', services=services,
                           user=current_user(), unread=unread_count())

@app.route('/admin/users', methods=['GET','POST'])
@login_required
@role_required('admin')
def admin_users():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            phone = request.form['phone'].strip()
            if query("SELECT id FROM user WHERE phone=?", (phone,), one=True):
                flash("Phone number already registered.", "error")
                return redirect(url_for('admin_users'))
            try:
                execute("INSERT INTO user(full_name,phone,password_hash,role,branch_id) VALUES(?,?,?,?,?)",
                        (request.form['full_name'].strip(), phone,
                         generate_password_hash(request.form.get('password','changeme')),
                         request.form['role'],
                         request.form.get('branch_id') or None))
                flash("User created.", "success")
            except sqlite3.IntegrityError:
                flash("Phone number already registered.", "error")
        elif action == 'toggle':
            u = query("SELECT is_active FROM user WHERE id=?", (request.form['id'],), one=True)
            if not u:
                flash("User not found.", "error")
                return redirect(url_for('admin_users'))
            execute("UPDATE user SET is_active=? WHERE id=?", (0 if u['is_active'] else 1, request.form['id']))
            flash("User status updated.", "success")
        elif action == 'edit_role':
            execute("UPDATE user SET role=?, branch_id=? WHERE id=?",
                    (request.form['role'], request.form.get('branch_id') or None, request.form['id']))
            flash("User role updated.", "success")
        return redirect(url_for('admin_users'))
    search = request.args.get('search','')
    role_f = request.args.get('role','')
    status_f = request.args.get('status','')
    where = "WHERE 1=1"
    args = []
    if search:
        where += " AND (u.full_name LIKE ? OR u.phone LIKE ?)"
        args += [f'%{search}%', f'%{search}%']
    if role_f:
        where += " AND u.role=?"
        args.append(role_f)
    if status_f == 'active':
        where += " AND u.is_active=1"
    elif status_f == 'inactive':
        where += " AND u.is_active=0"
    users = query(f"""SELECT u.*, b.name as branch_name FROM user u
                      LEFT JOIN branch b ON u.branch_id=b.id
                      {where} ORDER BY u.id DESC""", args)
    branches = query("SELECT id, name FROM branch WHERE is_active=1")
    return render_template('admin/users.html', users=users, branches=branches,
                           search=search, role_f=role_f, status_f=status_f,
                           user=current_user(), unread=unread_count())

@app.route('/admin/reports')
@login_required
@role_required('admin')
def admin_reports():
    today = date.today().isoformat()
    stats = query("""SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN bk.status='completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN bk.status='no_show' THEN 1 ELSE 0 END) as no_show,
                        SUM(CASE WHEN bk.status='cancelled' THEN 1 ELSE 0 END) as cancelled,
                        SUM(CASE WHEN bk.status='skipped' THEN 1 ELSE 0 END) as skipped
                     FROM booking bk JOIN time_slot ts ON bk.time_slot_id=ts.id
                     WHERE ts.slot_date=?""", (today,), one=True)
    services_perf = query("""SELECT s.name, COUNT(bk.id) as total,
                                    SUM(CASE WHEN bk.status='completed' THEN 1 ELSE 0 END) as completed,
                                    SUM(CASE WHEN bk.status='no_show' THEN 1 ELSE 0 END) as no_show,
                                    s.estimated_duration_minutes
                             FROM service s
                             JOIN branch_service bs ON bs.service_id=s.id
                             JOIN time_slot ts ON ts.branch_service_id=bs.id
                             JOIN booking bk ON bk.time_slot_id=ts.id
                             WHERE ts.slot_date=?
                             GROUP BY s.id""", (today,))
    return render_template('admin/reports.html', stats=stats, services_perf=services_perf,
                           user=current_user(), unread=unread_count(), today=today)

# ── API (for JS polling) ──────────────────────────────────────────────────────

@app.route('/api/queue_status/<int:bs_id>')
def api_queue_status(bs_id):
    today = date.today().isoformat()
    serving = query("""SELECT bk.queue_number FROM booking bk
                       JOIN time_slot ts ON bk.time_slot_id=ts.id
                       WHERE ts.branch_service_id=? AND ts.slot_date=? AND bk.status='serving'
                       ORDER BY bk.queue_number LIMIT 1""", (bs_id, today), one=True)
    waiting = query("""SELECT COUNT(*) as c FROM booking bk
                       JOIN time_slot ts ON bk.time_slot_id=ts.id
                       WHERE ts.branch_service_id=? AND ts.slot_date=?
                       AND bk.status IN ('booked','arrived')""", (bs_id, today), one=True)
    return jsonify({
        'serving_now': serving['queue_number'] if serving else None,
        'waiting': waiting['c'] if waiting else 0
    })

@app.route('/api/notifications')
@login_required
def api_notifications():
    notifs = query("SELECT * FROM notification WHERE user_id=? AND is_read=0 ORDER BY sent_at DESC LIMIT 10",
                   (session['user_id'],))
    return jsonify([row_to_dict(n) for n in notifs])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
