# GovQueue — Government Queue Tracking Platform

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Seed the database (creates govqueue.db + demo data)
python seed.py

# 3. Run the app
python app.py
# → Open http://localhost:5000
```

## Login Credentials

| Role             | Phone           | Password    |
|------------------|-----------------|-------------|
| System Admin     | +20100000000    | admin123    |
| Supervisor (DT)  | +20100000001    | super123    |
| Supervisor (East)| +20100000002    | super123    |
| Counter Staff    | +20100000003    | staff123    |
| Counter Staff    | +20100000004    | staff123    |
| Validation Staff | +20100000005    | val123      |
| Citizen          | +20100000006    | citizen123  |
| Citizen          | +20100000007    | citizen123  |

## File Structure

```
govqueue/
├── app.py              # Flask app — all routes
├── db.py               # SQLite helpers
├── schema.sql          # Database schema
├── seed.py             # Demo data seeder
├── requirements.txt
└── templates/
    ├── base.html           # Shared layout + navbar
    ├── index.html          # Public landing page
    ├── login.html
    ├── register.html
    ├── citizen/
    │   ├── dashboard.html  # Active ticket + quick actions
    │   ├── book.html       # Branch → Service → Slot picker
    │   ├── bookings.html   # List + cancel
    │   ├── track.html      # Live queue position
    │   └── profile.html
    ├── staff/
    │   ├── dashboard.html  # Call next / mark done/skip/noshow
    │   └── validation.html # Mark arrived / no-show
    ├── supervisor/
    │   ├── dashboard.html  # Branch overview + window grid
    │   └── windows.html    # Open/close + assign staff
    └── admin/
        ├── dashboard.html
        ├── services.html   # CRUD services
        ├── users.html      # CRUD users + role management
        └── reports.html    # Daily stats + service performance
```

## Workflow

1. **Citizen** registers → books a slot → arrives → validation staff marks "Arrived"
2. **Counter staff** clicks "Call Next" → citizen served → marked Completed/Skipped/No-show
3. **Supervisor** monitors windows, opens/closes them, assigns staff
4. **Admin** manages services, users, views reports
5. **Notifications** fire in-browser when citizen is ≤2 spots from their turn
