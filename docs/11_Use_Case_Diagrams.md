# Government Queue Tracking Platform

Version: MVP 1.0

---

# Use Case Diagrams

This document describes the primary use cases supported by the Government Queue Tracking Platform.

---

# 1. Actors

## Guest

* View branches
* View services
* View congestion levels
* View estimated waiting times

## Citizen

* Register account
* Authenticate via OTP
* Join queue
* Track queue status
* Cancel booking
* Manage profile
* Receive notifications

## Door Keeper

* Search citizen
* Register citizen
* Create booking on behalf of citizen
* View citizen booking information

## Counter Staff

* View queues
* Call next ticket
* Complete ticket
* Skip ticket
* Mark no-show

## Branch Supervisor

* Manage staff qualifications
* Manage windows
* Monitor branch operations
* View reports

## System Admin

* Manage branches
* Manage services
* Manage users
* Configure system settings
* View organization analytics

---

# 2. Citizen Use Cases

```mermaid
flowchart LR

Citizen((Citizen))

A[Register]
B[Login via OTP]
C[Join Queue]
D[Track Queue]
E[Cancel Booking]
F[Manage Profile]
G[Receive Notifications]

Citizen --> A
Citizen --> B
Citizen --> C
Citizen --> D
Citizen --> E
Citizen --> F
Citizen --> G
```

---

# 3. Door Keeper Use Cases

```mermaid
flowchart LR

DoorKeeper((Door Keeper))

A[Search Citizen]
B[Register Citizen]
C[Create Booking]
D[View Booking Information]

DoorKeeper --> A
DoorKeeper --> B
DoorKeeper --> C
DoorKeeper --> D
```

---

# 4. Counter Staff Use Cases

```mermaid
flowchart LR

Staff((Counter Staff))

A[View Queue]
B[Call Next Ticket]
C[Complete Ticket]
D[Skip Ticket]
E[Mark No Show]

Staff --> A
Staff --> B
Staff --> C
Staff --> D
Staff --> E
```

---

# 5. Branch Supervisor Use Cases

```mermaid
flowchart LR

Supervisor((Branch Supervisor))

A[Assign Services]
B[Remove Services]
C[Open Window]
D[Close Window]
E[Monitor Operations]
F[View Reports]

Supervisor --> A
Supervisor --> B
Supervisor --> C
Supervisor --> D
Supervisor --> E
Supervisor --> F
```

---

# 6. System Admin Use Cases

```mermaid
flowchart LR

Admin((System Admin))

A[Manage Branches]
B[Manage Services]
C[Manage Users]
D[Configure Settings]
E[View Analytics]

Admin --> A
Admin --> B
Admin --> C
Admin --> D
Admin --> E
```

---

# 7. End-to-End Booking Flow

```mermaid
flowchart TD

Citizen --> SelectBranch
SelectBranch --> SelectService
SelectService --> EligibilityCheck
EligibilityCheck --> CreateTicket
CreateTicket --> AssignQueueNumber
AssignQueueNumber --> CalculateWaitTime
CalculateWaitTime --> ActiveQueue
ActiveQueue --> Notification
Notification --> Called
Called --> ServiceCompletion
```
