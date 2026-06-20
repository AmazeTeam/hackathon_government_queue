# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines the queue-processing algorithms and operational rules used by the platform.

It describes:

* Queue creation
* Ticket creation
* Queue ordering
* Ticket serving
* Wait-time estimation
* Round-robin service selection
* Notification triggering
* Queue statistics

This document is the authoritative source for queue behavior.

---

# 2. Queue Architecture

## Queue Definition

A queue exists for every:

```text
Branch + Service
```

combination.

Examples:

```text
Passport @ Cairo Branch

National ID @ Cairo Branch

Passport @ Alexandria Branch
```

Each queue operates independently.

---

## Queue Ownership

A queue belongs to exactly one:

* Branch
* Service

combination.

A queue contains many tickets.

---

# 3. Ticket Creation Algorithm

## Goal

Create a queue ticket for a citizen.

---

## Preconditions

The citizen:

* Exists in the system
* Has no active booking
* Selected a valid branch
* Selected a valid service

---

## Algorithm

### Step 1

Locate:

```text
Queue
(
 Branch,
 Service
)
```

---

### Step 2

Find latest queue number for today.

Example:

```text
101
```

---

### Step 3

Generate:

```text
102
```

---

### Step 4

Create ticket.

Status:

```text
Waiting
```

---

### Step 5

Calculate queue position.

---

### Step 6

Calculate estimated wait time.

---

### Step 7

Return booking confirmation.

---

## Output

```json
{
  "ticketNumber": 102,
  "status": "Waiting",
  "position": 5,
  "estimatedWaitMinutes": 50
}
```

---

# 4. Queue Ordering Algorithm

## Rule

Queues follow FIFO ordering.

---

## Ordering Field

```text
joined_at
```

Ascending.

---

## Example

```text
Ticket 100
09:00

Ticket 101
09:02

Ticket 102
09:05
```

Serving order:

```text
100
101
102
```

---

# 5. Call Next Algorithm

## Goal

Select the next citizen to be served.

---

## Preconditions

Staff member:

* Is active
* Belongs to a branch
* Has at least one service qualification

---

## Service Selection

The system uses:

```text
Round Robin
```

service selection.

---

## Example

Staff qualifications:

```text
Passport
National ID
Birth Certificate
```

Internal pointer:

```text
Passport
```

---

### First Call

Serve:

```text
Passport
```

Move pointer to:

```text
National ID
```

---

### Second Call

Serve:

```text
National ID
```

Move pointer to:

```text
Birth Certificate
```

---

### Third Call

Serve:

```text
Birth Certificate
```

Move pointer to:

```text
Passport
```

---

## Empty Queue Handling

Empty queues are skipped.

Example:

```text
Passport = 5

National ID = 0

Birth Certificate = 3
```

Calls:

```text
Passport

Birth Certificate

Passport

Birth Certificate
```

---

## Ticket Selection

Within the selected queue:

Choose:

```text
Oldest Waiting Ticket
```

---

## Status Update

Change:

```text
Waiting
```

to:

```text
Called
```

---

## Timestamp

Set:

```text
called_at
```

---

# 6. Complete Ticket Algorithm

## Preconditions

Ticket status:

```text
Called
```

or

```text
InProgress
```

---

## Actions

Update:

```text
status = Completed
completed_at = now()
```

---

## Result

Ticket leaves active queue.

---

# 7. Skip Ticket Algorithm

## Preconditions

Ticket status:

```text
Called
```

---

## Actions

Update:

```text
status = Skipped
```

---

## Result

Ticket leaves active queue.

---

# 8. No Show Algorithm

## Preconditions

Ticket status:

```text
Called
```

---

## Actions

Update:

```text
status = NoShow
```

---

## Result

Ticket leaves active queue.

---

# 9. Cancellation Algorithm

## Preconditions

Ticket status:

```text
Waiting
```

---

## Actions

Update:

```text
status = Cancelled
```

---

## Result

Ticket leaves active queue.

---

# 10. Queue Position Algorithm

## Goal

Determine citizen position.

---

## Formula

```text
Count(
 Waiting Tickets
 Before Current Ticket
)
```

---

## Example

Queue:

```text
101
102
103
104
105
```

Citizen:

```text
105
```

Position:

```text
4
```

---

# 11. Estimated Wait Time Algorithm

## Service Duration

Use:

```text
BranchService.estimated_duration_minutes
```

---

## Formula

```text
People Ahead
×
Estimated Service Duration
```

---

## Example

People Ahead:

```text
6
```

Duration:

```text
10 min
```

Result:

```text
60 min
```

---

## Notes

Estimated wait time is informational only.

Actual wait time may vary.

---

# 12. Queue Statistics Algorithm

For every queue calculate:

---

## Waiting Count

Tickets with:

```text
Waiting
```

---

## Called Count

Tickets with:

```text
Called
```

---

## Completed Count

Tickets with:

```text
Completed
```

today.

---

## No Show Count

Tickets with:

```text
NoShow
```

today.

---

## Cancellation Count

Tickets with:

```text
Cancelled
```

today.

---

# 13. Notification Engine

## Notification Type 1

Queue Approaching

---

### Trigger

Exactly:

```text
2 waiting citizens
```

remain before the ticket.

---

### Example

Citizen:

```text
105
```

Current serving:

```text
102
```

Waiting ahead:

```text
103
104
```

Send notification.

---

### Message

```text
Your turn is approaching.

Only two citizens remain before your ticket.
```

---

## Notification Type 2

Ticket Called

---

### Trigger

Ticket status changes:

```text
Waiting
```

↓

```text
Called
```

---

### Message

```text
Your ticket is now being served.
```

---

# 14. Daily Queue Reset

## Trigger

Start of business day.

---

## Actions

Queue numbering sequence resets.

---

## Historical Data

Tickets remain stored.

No ticket records are deleted.

---

# 15. Queue Integrity Rules

## Rule 1

Queue order cannot be modified manually.

---

## Rule 2

Staff cannot choose tickets manually.

All selections are system-driven.

---

## Rule 3

Citizens cannot choose queue numbers.

Queue numbers are system-generated.

---

## Rule 4

Only one active ticket per citizen.

---

## Rule 5

Queue tickets are immutable after creation.

Queue number never changes.

---

# 16. Failure Handling

## Staff Calls Next

If all eligible queues are empty:

Return:

```json
{
  "message": "No waiting citizens."
}
```

---

## Booking Attempt

If citizen already has active booking:

Return:

```json
{
  "message": "Citizen already has an active booking."
}
```

---

## Notification Failure

If browser notification delivery fails:

* Log failure
* Continue queue processing

Queue flow must never depend on notification delivery.

```
```
