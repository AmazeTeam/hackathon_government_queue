# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines the business rules governing queue behavior, ticket lifecycle, service delivery, booking eligibility, notifications, and operational constraints.

These rules represent the authoritative business logic of the platform and take precedence over implementation assumptions.

---

# 2. Booking Rules

## BR-001: Branch Selection Required

A citizen must select a branch before joining a queue.

A booking cannot exist without a branch.

---

## BR-002: Service Selection Required

A citizen must select a service before joining a queue.

A booking cannot exist without a service.

---

## BR-003: Service Availability Validation

A citizen may only join a service queue if the selected branch offers that service.

If the branch does not offer the service, the booking request shall be rejected.

---

## BR-004: One Active Booking Rule

A citizen may have only one active booking at any given time.

---

### Active Booking States

The following ticket states are considered active:

* Waiting
* Called
* In Progress

---

### Inactive Booking States

The following ticket states are considered inactive:

* Completed
* Cancelled
* No Show

A citizen with an inactive booking may create a new booking.

---

## BR-005: Booking Creation Source

Bookings may be created through:

* Citizen self-service
* Door Keeper assisted booking

Both creation methods follow identical queue rules.

No priority is granted to Door Keeper bookings.

---

# 3. Queue Rules

## BR-006: Queue Ownership

A queue exists for every:

* Branch
* Service

combination.

Examples:

* Passport @ Cairo Branch
* Passport @ Alexandria Branch
* National ID @ Cairo Branch

Each queue operates independently.

---

## BR-007: FIFO Ordering

Queues operate using First-In-First-Out ordering.

The first citizen to join a queue shall be the first citizen eligible for service.

---

## BR-008: Queue Position Calculation

Queue position is calculated using:

Number of waiting citizens ahead of the ticket.

The currently served ticket is not counted.

Example:

Current ticket:

Ticket #10

Citizen ticket:

Ticket #15

Position:

4

Tickets ahead:

11, 12, 13, 14

---

## BR-009: Queue Number Assignment

When a citizen joins a queue:

The system shall automatically generate a queue number.

Queue numbers must be unique within:

* Branch
* Service
* Day

combination.

---

## BR-010: Daily Queue Reset

Queue numbering resets at the start of each business day.

Historical tickets remain stored for reporting purposes.

---

# 4. Service Rules

## BR-011: Service Qualification

A staff member may be qualified to perform multiple services.

Examples:

Ahmed:

* Passport Renewal
* National ID

Sara:

* Passport Renewal
* Birth Certificate

---

## BR-012: Qualification Management

Only Branch Supervisors may modify service qualifications assigned to staff members.

---

## BR-013: Service Availability

A service may be active in one branch and inactive in another.

Citizens may only book active services.

---

# 5. Ticket Processing Rules

## BR-014: Ticket Status Lifecycle

Tickets may move through the following states:

Waiting

↓

Called

↓

In Progress

↓

Completed

Alternative outcomes:

Waiting

↓

Called

↓

Skipped

or

Waiting

↓

Called

↓

No Show

---

## BR-015: Call Next Operation

Only Counter Staff may call the next ticket.

Calling a ticket changes its status from:

Waiting

to

Called

---

## BR-016: Ticket Completion

A ticket may be marked completed only after being called.

Completed tickets leave the active queue.

---

## BR-017: Ticket Skip

Counter Staff may skip a ticket when:

* Citizen is temporarily unavailable
* Citizen requests additional time

Skipped tickets are removed from the active queue.

The MVP does not support rejoining skipped tickets automatically.

---

## BR-018: No Show

A ticket may be marked as No Show when:

* Citizen does not respond after being called

No Show tickets leave the active queue.

---

# 6. Multi-Service Staff Rules

## BR-019: Round Robin Service Selection

When a staff member is qualified for multiple services, the system shall determine the next queue to serve using a round-robin algorithm.

Example:

Staff Qualifications:

* Passport
* National ID
* Birth Certificate

Call sequence:

Passport

↓

National ID

↓

Birth Certificate

↓

Passport

↓

...

---

## BR-020: Empty Queue Skipping

If a service queue is empty during round-robin selection:

The queue shall be skipped automatically.

Example:

Passport = 10 tickets

National ID = 0 tickets

Birth Certificate = 5 tickets

Call sequence:

Passport

↓

Birth Certificate

↓

Passport

↓

Birth Certificate

---

## BR-021: Round Robin State Preservation

The system shall remember the last served service for each staff member.

System restarts shall not reset round-robin order.

---

# 7. Wait Time Rules

## BR-022: Estimated Service Duration

Every service shall have a configured estimated service duration.

Examples:

Passport Renewal:

10 minutes

Birth Certificate:

5 minutes

National ID:

8 minutes

---

## BR-023: Estimated Wait Time Calculation

Estimated wait time is calculated using:

People Ahead × Estimated Service Duration

The estimate is informational only.

Actual wait time may vary.

---

## BR-024: Dynamic Recalculation

Estimated wait time shall be recalculated whenever:

* A ticket is completed
* A ticket is cancelled
* A ticket is marked no-show
* A ticket is skipped

---

# 8. Notification Rules

## BR-025: Notification Eligibility

Only citizens with active bookings may receive queue notifications.

---

## BR-026: Queue Approaching Notification

The system shall send a notification when:

Exactly two waiting citizens remain before the ticket.

---

## BR-027: Called Notification

The system shall send a notification when:

The citizen's ticket status changes to Called.

---

## BR-028: Notification Channel

MVP notifications shall use:

Browser Push Notifications

only.

---

# 9. Branch Rules

## BR-029: Staff Ownership

A staff member belongs to exactly one branch.

---

## BR-030: Supervisor Ownership

Each branch shall have one Branch Supervisor.

---

## BR-031: Window Ownership

Each window belongs to exactly one branch.

---

## BR-032: Service Availability

Services are assigned to branches independently.

A branch may offer any subset of available services.

---

# 10. Reporting Rules

## BR-033: Historical Data Preservation

Completed, cancelled, skipped, and no-show tickets shall remain stored permanently.

Tickets shall never be physically deleted.

---

## BR-034: Daily Transaction Count

Daily transaction totals include:

* Completed tickets

only.

---

## BR-035: No Show Rate

No Show Rate =

No Show Tickets

/

Total Tickets Created

---

## BR-036: Cancellation Rate

Cancellation Rate =

Cancelled Tickets

/

Total Tickets Created

---

## BR-037: Average Wait Time

Average wait time shall be calculated separately for each:

* Service
* Branch

combination.

---

# 11. Administrative Rules

## BR-038: Administrative Authority

System Administrators may manage:

* Branches
* Services
* Users
* Roles
* Global settings

across the entire platform.

---

## BR-039: Branch Authority

Branch Supervisors may manage:

* Staff
* Service qualifications
* Windows

only within their assigned branch.

---

## BR-040: Auditability

Administrative actions shall be recorded in an audit log.

Examples:

* User activation
* User deactivation
* Role assignment
* Service creation
* Service deletion
* Branch configuration changes

---

# 12. Data Integrity Rules

## BR-041: Ticket Immutability

Once a queue ticket is created:

Its queue number may never change.

---

## BR-042: Queue Integrity

Staff members may not manually reorder queue tickets.

Queue ordering is controlled exclusively by system rules.

---

## BR-043: Service Integrity

A ticket must always belong to exactly one:

* Branch
* Service

combination.

---

## BR-044: User Identity Integrity

Phone numbers must be unique across all citizen accounts.

Duplicate registrations are not allowed.
