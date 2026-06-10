# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines the high-level software architecture of the Government Queue Tracking Platform.

It describes:

* System components
* Service responsibilities
* Data flow
* Backend architecture
* Frontend architecture
* Notification architecture
* Deployment architecture

This document serves as the blueprint for implementation.

---

# 2. Architecture Goals

The architecture should be:

* Simple enough for hackathon delivery
* Modular enough for future growth
* Easy for AI agents to implement
* Easy to demonstrate
* Easy to maintain

---

# 3. High-Level Architecture

```text
┌─────────────────────┐
│     Web Client      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      REST API       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Application Core  │
└──────────┬──────────┘
           │
 ┌─────────┼─────────┐
 ▼         ▼         ▼

Auth    Queue    Notification
Module   Module     Module

           │
           ▼

┌─────────────────────┐
│     PostgreSQL      │
└─────────────────────┘
```

---

# 4. Technology Stack

## Frontend

Recommended:

```text
Next.js
TypeScript
TailwindCSS
ShadCN UI
```

Reasons:

* Fast development
* Excellent UX
* Responsive design
* Large ecosystem

---

## Backend

Recommended:

```text
NestJS
TypeScript
```

Reasons:

* Structured architecture
* Dependency injection
* Strong typing
* Suitable for scaling

---

## Database

```text
PostgreSQL
```

Reasons:

* Reliable
* Relational model fits domain
* Excellent indexing support

---

## Authentication

```text
Phone Number + OTP
JWT Access Token
```

---

## Notifications

```text
Web Push API
```

Implementation:

```text
Service Worker
Push Subscription
Web Push Server
```

---

# 5. Backend Architecture

The backend follows a modular monolith architecture.

---

## Module Structure

```text
src/

├── auth
├── users
├── branches
├── services
├── queues
├── tickets
├── notifications
├── reports
├── admin
└── shared
```

---

# 6. Auth Module

## Responsibilities

* OTP generation
* OTP verification
* JWT creation
* Session management

---

## Entities

```text
User
Role
UserRole
```

---

## Public Endpoints

```text
POST /auth/request-otp
POST /auth/verify-otp
```

---

# 7. Users Module

## Responsibilities

* Profile management
* Role management
* User retrieval

---

## Entities

```text
User
Role
UserRole
```

---

# 8. Branches Module

## Responsibilities

* Branch CRUD
* Window CRUD
* Branch lookup

---

## Entities

```text
Branch
Window
```

---

# 9. Services Module

## Responsibilities

* Service CRUD
* Branch-service assignment
* Service availability management

---

## Entities

```text
Service
BranchService
```

---

# 10. Queue Module

## Responsibilities

* Queue retrieval
* Position calculation
* Wait-time calculation
* Queue statistics

---

## Entities

```text
Queue
```

---

# 11. Ticket Module

## Responsibilities

* Ticket creation
* Ticket cancellation
* Ticket serving
* Ticket lifecycle management

---

## Entities

```text
Ticket
```

---

## Business Logic

Contains:

* FIFO processing
* Round-robin service selection
* Queue numbering
* Ticket status transitions

---

# 12. Notification Module

## Responsibilities

* Push subscription storage
* Notification dispatch
* Queue alert generation

---

## Entities

```text
PushSubscription
```

---

## Notification Types

### Approaching Turn

```text
2 citizens remaining
```

---

### Ticket Called

```text
Status = Called
```

---

# 13. Reports Module

## Responsibilities

* Daily reports
* Wait-time reports
* No-show reports
* Cancellation reports
* Branch analytics

---

# 14. Admin Module

## Responsibilities

* User administration
* Branch administration
* Service administration
* Global settings

---

# 15. Suggested Folder Structure

```text
src/

├── auth/
├── users/
├── branches/
├── services/
├── queues/
├── tickets/
├── notifications/
├── reports/
├── admin/

├── common/
│   ├── guards
│   ├── decorators
│   ├── interceptors
│   ├── filters
│   └── constants

├── database/
│   ├── entities
│   ├── migrations
│   └── seeders
│
└── main.ts
```

---

# 16. Frontend Architecture

Recommended architecture:

```text
app/

├── auth
├── dashboard
├── queue
├── profile
├── admin
├── supervisor
└── staff
```

---

# 17. Frontend Pages

## Public Pages

```text
/
branches
branches/[id]
login
verify-otp
```

---

## Citizen Pages

```text
/dashboard

/book

/my-ticket

/profile
```

---

## Door Keeper Pages

```text
/door-keeper

/create-booking
```

---

## Staff Pages

```text
/staff

/staff/queues

/staff/current-ticket
```

---

## Supervisor Pages

```text
/supervisor

/staff-management

/windows

/reports
```

---

## Admin Pages

```text
/admin

/branches

/services

/users
```

---

# 18. Authentication Flow

```text
Phone Number
        ↓

Request OTP
        ↓

Receive OTP
        ↓

Verify OTP
        ↓

Generate JWT
        ↓

Authenticated Session
```

---

# 19. Queue Booking Flow

```text
Citizen
    ↓

Select Branch
    ↓

Select Service
    ↓

Create Ticket
    ↓

Assign Queue Number
    ↓

Calculate Wait Time
    ↓

Return Ticket
```

---

# 20. Queue Serving Flow

```text
Staff
    ↓

Call Next
    ↓

Round Robin Service Selection
    ↓

Select Oldest Waiting Ticket
    ↓

Update Status = Called
    ↓

Citizen Notification
```

---

# 21. Notification Flow

```text
Citizen Grants Permission
          ↓

Store Push Subscription
          ↓

Queue Changes
          ↓

Notification Trigger
          ↓

Web Push Sent
          ↓

Browser Displays Alert
```

---

# 22. Authorization Strategy

Role-based access control (RBAC).

---

## Roles

```text
Citizen

DoorKeeper

CounterStaff

BranchSupervisor

SystemAdmin
```

---

## Guards

Every protected endpoint shall require:

```text
JWT Authentication
```

and

```text
Role Validation
```

---

# 23. Deployment Architecture

For MVP:

```text
Frontend
    ↓

Vercel

Backend
    ↓

Railway / Render

Database
    ↓

PostgreSQL
```

---

# 24. Logging

Application logs:

```text
Errors
Warnings
Queue Operations
Authentication Events
```

---

# 25. Future Scalability

The architecture should allow future extraction of:

```text
Notification Service

Reporting Service

Authentication Service
```

into independent microservices.

No architectural redesign should be required.

---

# 26. MVP Architectural Principle

The MVP should prioritize:

1. Simplicity
2. Reliability
3. Demo Quality

over

1. Extreme Scalability
2. Premature Optimization
3. Complex Infrastructure

A working system demonstrated end-to-end is more valuable than an over-engineered platform.

```
```
