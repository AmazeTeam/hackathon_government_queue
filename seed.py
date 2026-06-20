"""Seed database per docs/06_ERD.md."""
import os
from datetime import datetime

from db import DB_PATH, execute, init_db, query

ROLES = ['Citizen', 'DoorKeeper', 'CounterStaff', 'BranchSupervisor', 'SystemAdmin']


def seed_roles():
    for name in ROLES:
        execute('INSERT OR IGNORE INTO role(name) VALUES(?)', (name,))


def assign_role(user_id, role_name):
    role = query('SELECT id FROM role WHERE name=?', (role_name,), one=True)
    if role:
        execute('INSERT OR IGNORE INTO user_role(user_id, role_id) VALUES(?,?)', (user_id, role['id']))


def create_user(full_name, phone, branch_id=None):
    ts = datetime.now().isoformat()
    return execute(
        'INSERT INTO user(full_name, phone_number, branch_id, created_at, updated_at) VALUES(?,?,?,?,?)',
        (full_name, phone, branch_id, ts, ts),
    )


def create_branch_service(branch_id, service_id, duration):
    bs_id = execute(
        'INSERT INTO branch_service(branch_id, service_id, estimated_duration_minutes) VALUES(?,?,?)',
        (branch_id, service_id, duration),
    )
    execute(
        'INSERT INTO queue(branch_service_id, created_at) VALUES(?,?)',
        (bs_id, datetime.now().isoformat()),
    )
    return bs_id


def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    init_db()
    seed_roles()

    ts = datetime.now().isoformat()

    b1 = execute(
        'INSERT INTO branch(name, address, created_at) VALUES(?,?,?)',
        ('Downtown Branch', '5 Tahrir Square, Cairo', ts),
    )
    b2 = execute(
        'INSERT INTO branch(name, address, created_at) VALUES(?,?,?)',
        ('East Branch', '12 Nasr City St, Cairo', ts),
    )

    s1 = execute(
        'INSERT INTO service(name, description, created_at) VALUES(?,?,?)',
        ('Civil Registry', 'Civil registry services', ts),
    )
    s2 = execute(
        'INSERT INTO service(name, description, created_at) VALUES(?,?,?)',
        ('Driving License', 'Driving license services', ts),
    )
    s3 = execute(
        'INSERT INTO service(name, description, created_at) VALUES(?,?,?)',
        ('Tax Services', 'Tax related services', ts),
    )
    s4 = execute(
        'INSERT INTO service(name, description, created_at) VALUES(?,?,?)',
        ('Business Permits', 'Business permit services', ts),
    )

    create_branch_service(b1, s1, 20)
    create_branch_service(b1, s2, 15)
    create_branch_service(b1, s3, 10)
    create_branch_service(b2, s1, 20)
    create_branch_service(b2, s4, 25)

    for i in range(1, 4):
        execute('INSERT INTO window(branch_id, window_number, is_open) VALUES(?,?,?)', (b1, i, 1 if i < 3 else 0))
    for i in range(1, 3):
        execute('INSERT INTO window(branch_id, window_number, is_open) VALUES(?,?,?)', (b2, i, 1))

    admin_id = create_user('System Admin', '+20100000000')
    assign_role(admin_id, 'SystemAdmin')

    sup1 = create_user('Laila Hassan', '+20100000001', b1)
    assign_role(sup1, 'BranchSupervisor')

    sup2 = create_user('Nour Adel', '+20100000002', b2)
    assign_role(sup2, 'BranchSupervisor')

    staff1 = create_user('Ahmed Kamal', '+20100000003', b1)
    assign_role(staff1, 'CounterStaff')
    execute('INSERT INTO staff_service(user_id, service_id) VALUES(?,?)', (staff1, s1))
    execute('INSERT INTO staff_service(user_id, service_id) VALUES(?,?)', (staff1, s2))

    staff2 = create_user('Sara Mahmoud', '+20100000004', b1)
    assign_role(staff2, 'CounterStaff')
    execute('INSERT INTO staff_service(user_id, service_id) VALUES(?,?)', (staff2, s2))

    dk = create_user('Omar Door Keeper', '+20100000005', b1)
    assign_role(dk, 'DoorKeeper')

    c1 = create_user('Mohamed Ahmed', '+20100000006')
    assign_role(c1, 'Citizen')

    c2 = create_user('Fatma Ali', '+20100000007')
    assign_role(c2, 'Citizen')

    win1 = query('SELECT id FROM window WHERE branch_id=? AND window_number=1', (b1,), one=True)
    win2 = query('SELECT id FROM window WHERE branch_id=? AND window_number=2', (b1,), one=True)
    if win1:
        execute(
            'INSERT INTO staff_window(user_id, window_id, assigned_at) VALUES(?,?,?)',
            (staff1, win1['id'], ts),
        )
    if win2:
        execute(
            'INSERT INTO staff_window(user_id, window_id, assigned_at) VALUES(?,?,?)',
            (staff2, win2['id'], ts),
        )

    print('Seeded successfully.')
    print('\n=== LOGIN (OTP: 123456) ===')
    print('Admin:       +20100000000')
    print('Supervisor:  +20100000001  (Downtown)')
    print('Supervisor:  +20100000002  (East)')
    print('Staff:       +20100000003  (Downtown)')
    print('Staff:       +20100000004  (Downtown)')
    print('Door Keeper: +20100000005  (Downtown)')
    print('Citizen:     +20100000006')
    print('Citizen:     +20100000007')


if __name__ == '__main__':
    seed()
