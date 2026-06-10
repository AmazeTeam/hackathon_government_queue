from db import init_db, execute, query
from werkzeug.security import generate_password_hash
from datetime import date, timedelta

def seed():
    init_db()

    # Check if already seeded
    if query("SELECT id FROM organization LIMIT 1"):
        print("Already seeded.")
        return

    # Organization
    org_id = execute("INSERT INTO organization(name) VALUES(?)", ("Egyptian Government Services",))

    # Branches
    b1 = execute("INSERT INTO branch(organization_id,name,address,phone,working_hours) VALUES(?,?,?,?,?)",
                 (org_id,"Downtown Branch","5 Tahrir Square, Cairo","+20-2-1234","08:00-16:00"))
    b2 = execute("INSERT INTO branch(organization_id,name,address,phone,working_hours) VALUES(?,?,?,?,?)",
                 (org_id,"East Branch","12 Nasr City St, Cairo","+20-2-5678","08:00-16:00"))

    # Services
    s1 = execute("INSERT INTO service(organization_id,name,name_ar,estimated_duration_minutes) VALUES(?,?,?,?)",
                 (org_id,"Civil Registry","السجل المدني",20))
    s2 = execute("INSERT INTO service(organization_id,name,name_ar,estimated_duration_minutes) VALUES(?,?,?,?)",
                 (org_id,"Driving License","رخصة القيادة",15))
    s3 = execute("INSERT INTO service(organization_id,name,name_ar,estimated_duration_minutes) VALUES(?,?,?,?)",
                 (org_id,"Tax Services","الخدمات الضريبية",10))
    s4 = execute("INSERT INTO service(organization_id,name,name_ar,estimated_duration_minutes) VALUES(?,?,?,?)",
                 (org_id,"Business Permits","تصاريح الأعمال",25))

    # Branch services
    bs1 = execute("INSERT INTO branch_service(branch_id,service_id) VALUES(?,?)", (b1,s1))
    bs2 = execute("INSERT INTO branch_service(branch_id,service_id) VALUES(?,?)", (b1,s2))
    bs3 = execute("INSERT INTO branch_service(branch_id,service_id) VALUES(?,?)", (b1,s3))
    bs4 = execute("INSERT INTO branch_service(branch_id,service_id) VALUES(?,?)", (b2,s1))
    bs5 = execute("INSERT INTO branch_service(branch_id,service_id) VALUES(?,?)", (b2,s4))

    # Windows
    for i in range(1,4):
        execute("INSERT INTO window(branch_id,service_id,window_number,label,status) VALUES(?,?,?,?,?)",
                (b1,s1,i,f"Window {i}","open" if i<3 else "closed"))
    for i in range(1,3):
        execute("INSERT INTO window(branch_id,service_id,window_number,label,status) VALUES(?,?,?,?,?)",
                (b1,s2,i,f"Window {i}","open"))
    for i in range(1,3):
        execute("INSERT INTO window(branch_id,service_id,window_number,label,status) VALUES(?,?,?,?,?)",
                (b2,s1,i,f"Window {i}","open"))

    # Users
    admin_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,is_active) VALUES(?,?,?,?,?)",
        ("System Admin","+20100000000",generate_password_hash("admin123"),"admin",1))

    sup1_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,branch_id,is_active) VALUES(?,?,?,?,?,?)",
        ("Laila Hassan","+20100000001",generate_password_hash("super123"),"supervisor",b1,1))

    sup2_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,branch_id,is_active) VALUES(?,?,?,?,?,?)",
        ("Nour Adel","+20100000002",generate_password_hash("super123"),"supervisor",b2,1))

    staff1_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,branch_id,is_active) VALUES(?,?,?,?,?,?)",
        ("Ahmed Kamal","+20100000003",generate_password_hash("staff123"),"staff",b1,1))

    staff2_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,branch_id,is_active) VALUES(?,?,?,?,?,?)",
        ("Sara Mahmoud","+20100000004",generate_password_hash("staff123"),"staff",b1,1))

    val_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,branch_id,is_active) VALUES(?,?,?,?,?,?)",
        ("Omar Validation","+20100000005",generate_password_hash("val123"),"validation_staff",b1,1))

    c1_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,is_active) VALUES(?,?,?,?,?)",
        ("Mohamed Ahmed","+20100000006",generate_password_hash("citizen123"),"citizen",1))

    c2_id = execute(
        "INSERT INTO user(full_name,phone,password_hash,role,is_active) VALUES(?,?,?,?,?)",
        ("Fatma Ali","+20100000007",generate_password_hash("citizen123"),"citizen",1))

    # Window assignments
    win1 = query("SELECT id FROM window WHERE branch_id=? AND window_number=1 AND service_id=?", (b1,s1), one=True)
    win2 = query("SELECT id FROM window WHERE branch_id=? AND window_number=2 AND service_id=?", (b1,s2), one=True)
    today = date.today().isoformat()
    if win1:
        execute("INSERT INTO window_assignment(window_id,staff_id,assigned_date,is_active) VALUES(?,?,?,?)",
                (win1["id"],staff1_id,today,1))
    if win2:
        execute("INSERT INTO window_assignment(window_id,staff_id,assigned_date,is_active) VALUES(?,?,?,?)",
                (win2["id"],staff2_id,today,1))

    # Time slots for today and tomorrow
    for bs, svc_id, est in [(bs1,s1,20),(bs2,s2,15),(bs3,s3,10),(bs4,s1,20),(bs5,s4,25)]:
        for d_off in range(3):
            slot_date = (date.today() + timedelta(days=d_off)).isoformat()
            for hour in range(8, 16):
                execute(
                    "INSERT INTO time_slot(branch_service_id,slot_date,start_time,end_time,max_capacity,booked_count) VALUES(?,?,?,?,?,?)",
                    (bs, slot_date, f"{hour:02d}:00", f"{hour:02d}:{est:02d}", 5, 0))

    print("Seeded successfully.")
    print("\n=== LOGIN CREDENTIALS ===")
    print("Admin:      +20100000000 / admin123")
    print("Supervisor: +20100000001 / super123  (Downtown)")
    print("Supervisor: +20100000002 / super123  (East)")
    print("Staff:      +20100000003 / staff123  (Downtown)")
    print("Staff:      +20100000004 / staff123  (Downtown)")
    print("Val.Staff:  +20100000005 / val123    (Downtown)")
    print("Citizen:    +20100000006 / citizen123")
    print("Citizen:    +20100000007 / citizen123")

if __name__ == "__main__":
    seed()
