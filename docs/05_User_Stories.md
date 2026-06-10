# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines the user stories and acceptance criteria for the Government Queue Tracking Platform.

User stories describe system behavior from the perspective of each user role and serve as the primary reference for implementation and testing.

---

# 2. Guest User Stories

---

## US-GUEST-001

### View Available Branches

As a Guest,

I want to view available government branches,

so that I can choose where to receive a service.

### Acceptance Criteria

* Branch list is visible without authentication.
* Branch names are displayed.
* Branch status is displayed.

---

## US-GUEST-002

### View Available Services

As a Guest,

I want to see services offered by a branch,

so that I know whether the branch can serve my needs.

### Acceptance Criteria

* Services are displayed per branch.
* Inactive services are hidden.
* Service names are visible.

---

## US-GUEST-003

### View Queue Congestion

As a Guest,

I want to view congestion levels,

so that I can estimate branch crowding.

### Acceptance Criteria

* Current queue sizes are visible.
* Estimated waiting times are visible.
* Current ticket numbers are visible.

---

## US-GUEST-004

### Register Prompt

As a Guest,

I want to be guided to register,

so that I can join a queue.

### Acceptance Criteria

* Join Queue actions redirect to authentication.
* Registration option is clearly visible.

---

# 3. Citizen User Stories

---

## US-CIT-001

### Register Account

As a Citizen,

I want to register using my phone number,

so that I can access the platform.

### Acceptance Criteria

* Phone number is collected.
* OTP is sent.
* OTP verification completes registration.
* User account is created.

---

## US-CIT-002

### Login Using OTP

As a Citizen,

I want to log in using my phone number,

so that I can securely access my account.

### Acceptance Criteria

* OTP is generated.
* OTP verification succeeds.
* Authenticated session is created.

---

## US-CIT-003

### Join Queue

As a Citizen,

I want to join a service queue,

so that I can receive government services.

### Acceptance Criteria

* Branch can be selected.
* Service can be selected.
* Queue ticket is generated.
* Queue number is displayed.
* Estimated waiting time is displayed.

---

## US-CIT-004

### Prevent Duplicate Active Bookings

As a Citizen,

I want the system to prevent multiple active bookings,

so that queue integrity is maintained.

### Acceptance Criteria

* Second active booking is rejected.
* Clear validation message is shown.

---

## US-CIT-005

### Track Queue Position

As a Citizen,

I want to monitor my queue progress,

so that I know when my turn is approaching.

### Acceptance Criteria

* Current position is visible.
* Current ticket being served is visible.
* Estimated waiting time is visible.
* Status is visible.

---

## US-CIT-006

### Cancel Booking

As a Citizen,

I want to cancel my booking,

so that I can leave the queue if necessary.

### Acceptance Criteria

* Active booking can be cancelled.
* Queue updates immediately.
* Ticket status becomes Cancelled.

---

## US-CIT-007

### Receive Queue Notification

As a Citizen,

I want to receive browser notifications,

so that I know when I should prepare for service.

### Acceptance Criteria

* Notification is sent when two citizens remain.
* Notification is sent when ticket is called.
* Browser permission is requested.

---

## US-CIT-008

### Manage Profile

As a Citizen,

I want to update my profile,

so that my information remains accurate.

### Acceptance Criteria

* Profile data is visible.
* Profile data can be updated.
* Language preference can be changed.

---

# 4. Door Keeper User Stories

---

## US-DK-001

### Search Citizen

As a Door Keeper,

I want to search for citizens,

so that I can assist them quickly.

### Acceptance Criteria

* Search by phone number is supported.
* Existing citizens are displayed.

---

## US-DK-002

### Register Citizen

As a Door Keeper,

I want to create citizen accounts,

so that walk-in citizens can use the system.

### Acceptance Criteria

* Citizen profile can be created.
* Phone number is stored.
* Citizen becomes searchable.

---

## US-DK-003

### Create Booking for Citizen

As a Door Keeper,

I want to create bookings on behalf of citizens,

so that walk-in visitors can join queues.

### Acceptance Criteria

* Branch can be selected.
* Service can be selected.
* Queue ticket is generated.
* Queue number is displayed.

---

# 5. Counter Staff User Stories

---

## US-STAFF-001

### View Eligible Queues

As Counter Staff,

I want to view queues for services I can perform,

so that I can serve citizens.

### Acceptance Criteria

* Eligible service queues are displayed.
* Queue lengths are visible.
* Current tickets are visible.

---

## US-STAFF-002

### Call Next Ticket

As Counter Staff,

I want to call the next ticket,

so that citizens are served in order.

### Acceptance Criteria

* Next ticket is selected automatically.
* Round-robin service selection is respected.
* Ticket status becomes Called.

---

## US-STAFF-003

### Complete Ticket

As Counter Staff,

I want to complete a ticket,

so that service completion is recorded.

### Acceptance Criteria

* Ticket status becomes Completed.
* Queue metrics update.

---

## US-STAFF-004

### Mark No Show

As Counter Staff,

I want to mark absent citizens,

so that queue flow continues.

### Acceptance Criteria

* Ticket status becomes No Show.
* Queue metrics update.

---

## US-STAFF-005

### Skip Ticket

As Counter Staff,

I want to skip a ticket,

so that service can continue when a citizen is unavailable.

### Acceptance Criteria

* Ticket status becomes Skipped.
* Queue metrics update.

---

# 6. Branch Supervisor User Stories

---

## US-SUP-001

### View Branch Dashboard

As a Branch Supervisor,

I want to monitor branch activity,

so that I can manage operations effectively.

### Acceptance Criteria

* Queue statistics are visible.
* Waiting citizen counts are visible.
* Service activity is visible.

---

## US-SUP-002

### Manage Staff Service Qualifications

As a Branch Supervisor,

I want to assign services to staff,

so that staff can perform appropriate work.

### Acceptance Criteria

* Services can be assigned.
* Services can be removed.
* Changes take effect immediately.

---

## US-SUP-003

### Manage Windows

As a Branch Supervisor,

I want to manage branch windows,

so that branch operations remain organized.

### Acceptance Criteria

* Windows can be opened.
* Windows can be closed.
* Window status is visible.

---

## US-SUP-004

### View Branch Reports

As a Branch Supervisor,

I want to analyze branch performance,

so that I can improve service delivery.

### Acceptance Criteria

* Daily transactions are visible.
* Average wait times are visible.
* No-show statistics are visible.
* Cancellation statistics are visible.

---

# 7. System Administrator User Stories

---

## US-ADMIN-001

### Manage Branches

As a System Administrator,

I want to manage branches,

so that organization structure remains accurate.

### Acceptance Criteria

* Branches can be created.
* Branches can be edited.
* Branches can be deactivated.

---

## US-ADMIN-002

### Manage Services

As a System Administrator,

I want to manage services,

so that service offerings remain current.

### Acceptance Criteria

* Services can be created.
* Services can be edited.
* Services can be deleted.

---

## US-ADMIN-003

### Manage Users

As a System Administrator,

I want to manage users,

so that platform access remains controlled.

### Acceptance Criteria

* Users can be viewed.
* Users can be activated.
* Users can be deactivated.
* Roles can be assigned.

---

## US-ADMIN-004

### Configure System

As a System Administrator,

I want to configure platform settings,

so that system behavior matches operational needs.

### Acceptance Criteria

* Queue settings are configurable.
* Notification settings are configurable.
* Working hours are configurable.

---

## US-ADMIN-005

### View Organization Analytics

As a System Administrator,

I want to view organization-wide metrics,

so that I can monitor platform performance.

### Acceptance Criteria

* Service demand metrics are visible.
* Branch demand metrics are visible.
* Wait-time metrics are visible.
* Cancellation metrics are visible.
* No-show metrics are visible.

---

# 8. MVP Demo Stories

The following stories represent the minimum end-to-end demo flow for the hackathon.

### Demo Flow 1

Citizen registers.

Citizen joins Passport queue.

Citizen receives queue ticket.

Citizen tracks queue position.

Citizen receives notification.

Citizen is called.

Staff completes service.

---

### Demo Flow 2

Door Keeper registers walk-in citizen.

Door Keeper creates booking.

Citizen receives ticket.

Citizen enters queue.

Staff serves citizen.

---

### Demo Flow 3

Supervisor monitors branch activity.

Supervisor views reports.

Supervisor manages staff qualifications.

---

### Demo Flow 4

Admin creates service.

Admin enables service for branch.

Citizens immediately begin using the service.
