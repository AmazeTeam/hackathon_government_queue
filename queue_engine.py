"""Queue processing per docs/07_Queue_Engine.md and docs/04_Business_Rules.md."""
from datetime import date, datetime
from db import query, execute

ACTIVE_STATUSES = ('Waiting', 'Called', 'InProgress')

VALID_TRANSITIONS = {
    'Waiting': ('Called', 'Cancelled'),
    'Called': ('InProgress', 'Skipped', 'NoShow', 'Completed'),
    'InProgress': ('Completed',),
}


class QueueError(Exception):
    def __init__(self, message, code='QUEUE_ERROR'):
        super().__init__(message)
        self.message = message
        self.code = code


def today_str():
    return date.today().isoformat()


def now_iso():
    return datetime.now().isoformat()


def get_branch_service(branch_id, service_id):
    return query(
        """SELECT bs.*, s.name as service_name, b.name as branch_name
           FROM branch_service bs
           JOIN service s ON bs.service_id = s.id
           JOIN branch b ON bs.branch_id = b.id
           WHERE bs.branch_id=? AND bs.service_id=?
             AND bs.is_active=1 AND s.is_active=1 AND b.is_active=1""",
        (branch_id, service_id),
        one=True,
    )


def get_or_create_queue(branch_service_id):
    q = query("SELECT * FROM queue WHERE branch_service_id=?", (branch_service_id,), one=True)
    if q:
        return q
    execute(
        "INSERT INTO queue(branch_service_id, current_serving_number, created_at) VALUES(?,?,?)",
        (branch_service_id, 0, now_iso()),
    )
    return query("SELECT * FROM queue WHERE branch_service_id=?", (branch_service_id,), one=True)


def has_active_ticket(citizen_id):
    placeholders = ','.join('?' * len(ACTIVE_STATUSES))
    return query(
        f"SELECT id FROM ticket WHERE citizen_id=? AND status IN ({placeholders}) LIMIT 1",
        (citizen_id, *ACTIVE_STATUSES),
        one=True,
    )


def next_queue_number(queue_id, ticket_date):
    row = query(
        "SELECT MAX(queue_number) as m FROM ticket WHERE queue_id=? AND ticket_date=?",
        (queue_id, ticket_date),
        one=True,
    )
    return (row['m'] or 0) + 1


def count_waiting_ahead(queue_id, ticket_date, queue_number):
    row = query(
        """SELECT COUNT(*) as c FROM ticket
           WHERE queue_id=? AND ticket_date=? AND status='Waiting' AND queue_number < ?""",
        (queue_id, ticket_date, queue_number),
        one=True,
    )
    return row['c'] if row else 0


def get_position(ticket):
    ahead = count_waiting_ahead(ticket['queue_id'], ticket['ticket_date'], ticket['queue_number'])
    return ahead + 1


def get_estimated_wait_minutes(branch_service_id, people_ahead):
    bs = query("SELECT estimated_duration_minutes FROM branch_service WHERE id=?", (branch_service_id,), one=True)
    duration = bs['estimated_duration_minutes'] if bs else 10
    return people_ahead * duration


def get_current_serving_number(queue_id, ticket_date):
    row = query(
        """SELECT queue_number FROM ticket
           WHERE queue_id=? AND ticket_date=? AND status IN ('Called', 'InProgress')
           ORDER BY called_at ASC LIMIT 1""",
        (queue_id, ticket_date),
        one=True,
    )
    if row:
        return row['queue_number']
    row = query(
        """SELECT MAX(queue_number) as n FROM ticket
           WHERE queue_id=? AND ticket_date=? AND status='Completed'""",
        (queue_id, ticket_date),
        one=True,
    )
    return row['n'] if row and row['n'] else 0


def ticket_payload(ticket, branch_service_id=None):
    ahead = count_waiting_ahead(ticket['queue_id'], ticket['ticket_date'], ticket['queue_number'])
    if branch_service_id is None:
        q = query("SELECT branch_service_id FROM queue WHERE id=?", (ticket['queue_id'],), one=True)
        branch_service_id = q['branch_service_id'] if q else None
    return {
        'ticketId': ticket['id'],
        'queueNumber': ticket['queue_number'],
        'status': ticket['status'],
        'position': ahead + 1,
        'estimatedWaitMinutes': get_estimated_wait_minutes(branch_service_id, ahead),
        'currentServingNumber': get_current_serving_number(ticket['queue_id'], ticket['ticket_date']),
    }


def create_ticket(citizen_id, branch_id, service_id):
    bs = get_branch_service(branch_id, service_id)
    if not bs:
        raise QueueError('Service not available at this branch', 'SERVICE_UNAVAILABLE')

    if has_active_ticket(citizen_id):
        raise QueueError('Citizen already has an active booking', 'ACTIVE_BOOKING_EXISTS')

    queue = get_or_create_queue(bs['id'])
    ticket_date = today_str()
    qnum = next_queue_number(queue['id'], ticket_date)
    joined = now_iso()

    ticket_id = execute(
        """INSERT INTO ticket(queue_id, citizen_id, queue_number, status, ticket_date, joined_at)
           VALUES(?,?,?,?,?,?)""",
        (queue['id'], citizen_id, qnum, 'Waiting', ticket_date, joined),
    )
    ticket = query("SELECT * FROM ticket WHERE id=?", (ticket_id,), one=True)
    payload = ticket_payload(ticket, bs['id'])
    check_approaching_notifications(queue['id'], ticket_date)
    return payload


def transition_ticket(ticket_id, allowed_from, to_status, **extra_fields):
    ticket = query("SELECT * FROM ticket WHERE id=?", (ticket_id,), one=True)
    if not ticket:
        raise QueueError('Ticket not found', 'NOT_FOUND')
    if ticket['status'] not in allowed_from:
        raise QueueError(f'Cannot transition from {ticket["status"]} to {to_status}', 'INVALID_TRANSITION')
    if to_status not in VALID_TRANSITIONS.get(ticket['status'], ()):
        raise QueueError(f'Invalid transition to {to_status}', 'INVALID_TRANSITION')

    sets = ['status=?']
    args = [to_status]
    for field, value in extra_fields.items():
        sets.append(f'{field}=?')
        args.append(value)
    args.append(ticket_id)
    execute(f"UPDATE ticket SET {', '.join(sets)} WHERE id=?", args)
    return query("SELECT * FROM ticket WHERE id=?", (ticket_id,), one=True)


def cancel_ticket(ticket_id, citizen_id=None):
    ticket = query("SELECT * FROM ticket WHERE id=?", (ticket_id,), one=True)
    if not ticket:
        raise QueueError('Ticket not found', 'NOT_FOUND')
    if citizen_id and ticket['citizen_id'] != citizen_id:
        raise QueueError('Forbidden', 'FORBIDDEN')
    updated = transition_ticket(ticket_id, ('Waiting',), 'Cancelled')
    check_approaching_notifications(ticket['queue_id'], ticket['ticket_date'])
    return updated


def get_staff_services(staff_id):
    return query(
        """SELECT ss.service_id, s.name as service_name
           FROM staff_service ss
           JOIN service s ON ss.service_id = s.id
           WHERE ss.user_id=?
           ORDER BY ss.service_id""",
        (staff_id,),
    )


def waiting_count(branch_id, service_id, ticket_date=None):
    ticket_date = ticket_date or today_str()
    row = query(
        """SELECT COUNT(*) as c FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND bs.service_id=? AND t.ticket_date=? AND t.status='Waiting'""",
        (branch_id, service_id, ticket_date),
        one=True,
    )
    return row['c'] if row else 0


def find_oldest_waiting(branch_id, service_id, ticket_date=None):
    ticket_date = ticket_date or today_str()
    return query(
        """SELECT t.* FROM ticket t
           JOIN queue q ON t.queue_id = q.id
           JOIN branch_service bs ON q.branch_service_id = bs.id
           WHERE bs.branch_id=? AND bs.service_id=? AND t.ticket_date=? AND t.status='Waiting'
           ORDER BY t.joined_at ASC LIMIT 1""",
        (branch_id, service_id, ticket_date),
        one=True,
    )


def _next_service_round_robin(staff_id, branch_id, services):
    if not services:
        return None
    service_ids = [s['service_id'] for s in services]
    rr = query("SELECT last_service_id FROM staff_round_robin WHERE user_id=?", (staff_id,), one=True)
    start_idx = 0
    if rr and rr['last_service_id'] in service_ids:
        start_idx = (service_ids.index(rr['last_service_id']) + 1) % len(service_ids)

    ticket_date = today_str()
    for offset in range(len(service_ids)):
        idx = (start_idx + offset) % len(service_ids)
        sid = service_ids[idx]
        if waiting_count(branch_id, sid, ticket_date) > 0:
            return sid
    return None


def call_next(staff_id):
    staff = query("SELECT * FROM user WHERE id=? AND is_active=1", (staff_id,), one=True)
    if not staff or not staff['branch_id']:
        raise QueueError('Staff not assigned to a branch', 'STAFF_NO_BRANCH')

    services = get_staff_services(staff_id)
    if not services:
        raise QueueError('Staff has no service qualifications', 'NO_QUALIFICATIONS')

    selected_service = _next_service_round_robin(staff_id, staff['branch_id'], services)
    if not selected_service:
        raise QueueError('No waiting citizens', 'QUEUE_EMPTY')

    nxt = find_oldest_waiting(staff['branch_id'], selected_service)
    if not nxt:
        raise QueueError('No waiting citizens', 'QUEUE_EMPTY')

    called = transition_ticket(nxt['id'], ('Waiting',), 'Called', called_at=now_iso())
    execute(
        "UPDATE queue SET current_serving_number=? WHERE id=?",
        (called['queue_number'], called['queue_id']),
    )
    execute(
        """INSERT INTO staff_round_robin(user_id, last_service_id) VALUES(?,?)
           ON CONFLICT(user_id) DO UPDATE SET last_service_id=excluded.last_service_id""",
        (staff_id, selected_service),
    )

    service = query("SELECT name FROM service WHERE id=?", (selected_service,), one=True)
    log_notification(
        called['citizen_id'],
        called['id'],
        'ticket_called',
        'Your ticket is now being served.',
    )
    check_approaching_notifications(called['queue_id'], called['ticket_date'])

    return {
        'ticketId': called['id'],
        'queueNumber': called['queue_number'],
        'serviceName': service['name'] if service else '',
        'status': called['status'],
    }


def complete_ticket(ticket_id):
    ticket = transition_ticket(ticket_id, ('Called', 'InProgress'), 'Completed', completed_at=now_iso())
    check_approaching_notifications(ticket['queue_id'], ticket['ticket_date'])
    return ticket


def skip_ticket(ticket_id):
    ticket = transition_ticket(ticket_id, ('Called',), 'Skipped')
    check_approaching_notifications(ticket['queue_id'], ticket['ticket_date'])
    return ticket


def no_show_ticket(ticket_id):
    ticket = transition_ticket(ticket_id, ('Called',), 'NoShow')
    check_approaching_notifications(ticket['queue_id'], ticket['ticket_date'])
    return ticket


def start_ticket(ticket_id):
    return transition_ticket(ticket_id, ('Called',), 'InProgress')


def get_queue_status(branch_id, service_id):
    bs = get_branch_service(branch_id, service_id)
    if not bs:
        raise QueueError('Queue not found', 'NOT_FOUND')
    queue = get_or_create_queue(bs['id'])
    ticket_date = today_str()
    waiting = waiting_count(branch_id, service_id, ticket_date)
    return {
        'currentServingNumber': get_current_serving_number(queue['id'], ticket_date),
        'waitingCount': waiting,
        'averageWaitMinutes': get_estimated_wait_minutes(bs['id'], waiting),
    }


def get_active_ticket(citizen_id):
    placeholders = ','.join('?' * len(ACTIVE_STATUSES))
    return query(
        f"""SELECT t.*, bs.id as branch_service_id, bs.branch_id, bs.service_id,
                   s.name as service_name, b.name as branch_name
            FROM ticket t
            JOIN queue q ON t.queue_id = q.id
            JOIN branch_service bs ON q.branch_service_id = bs.id
            JOIN service s ON bs.service_id = s.id
            JOIN branch b ON bs.branch_id = b.id
            WHERE t.citizen_id=? AND t.status IN ({placeholders})
            ORDER BY t.joined_at DESC LIMIT 1""",
        (citizen_id, *ACTIVE_STATUSES),
        one=True,
    )


def log_notification(user_id, ticket_id, ntype, message):
    existing = query(
        "SELECT id FROM notification_log WHERE user_id=? AND ticket_id=? AND type=?",
        (user_id, ticket_id, ntype),
        one=True,
    )
    if existing:
        return
    execute(
        """INSERT INTO notification_log(user_id, ticket_id, type, message, sent_at)
           VALUES(?,?,?,?,?)""",
        (user_id, ticket_id, ntype, message, now_iso()),
    )


def check_approaching_notifications(queue_id, ticket_date):
    waiting = query(
        """SELECT * FROM ticket
           WHERE queue_id=? AND ticket_date=? AND status='Waiting'
           ORDER BY queue_number""",
        (queue_id, ticket_date),
    )
    serving_num = get_current_serving_number(queue_id, ticket_date)
    for i, t in enumerate(waiting):
        ahead = i
        if serving_num and t['queue_number'] > serving_num:
            ahead = sum(1 for w in waiting if w['queue_number'] < t['queue_number'])
        if ahead == 2:
            log_notification(
                t['citizen_id'],
                t['id'],
                'approaching',
                'Your turn is approaching. Only two citizens remain before your ticket.',
            )


def congestion_rows():
    ticket_date = today_str()
    return query(
        """SELECT bs.id, b.name as branch_name, s.name as service_name,
                  bs.estimated_duration_minutes,
                  COALESCE(SUM(CASE WHEN t.status='Waiting' THEN 1 ELSE 0 END), 0) as waiting
           FROM branch_service bs
           JOIN branch b ON bs.branch_id = b.id
           JOIN service s ON bs.service_id = s.id
           LEFT JOIN queue q ON q.branch_service_id = bs.id
           LEFT JOIN ticket t ON t.queue_id = q.id AND t.ticket_date = ?
           WHERE bs.is_active=1 AND b.is_active=1 AND s.is_active=1
           GROUP BY bs.id""",
        (ticket_date,),
    )
