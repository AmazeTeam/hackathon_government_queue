# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines all state machines used by the platform.

State machines are the authoritative source for lifecycle transitions and prevent invalid state changes.

---

# 2. Ticket State Machine

## States

```text
Waiting
Called
InProgress
Completed
Cancelled
Skipped
NoShow
```

---

## Lifecycle Diagram

```text
Waiting
│
├── Cancelled
│
└── Called
      │
      ├── InProgress
      │      │
      │      └── Completed
      │
      ├── Skipped
      │
      └── NoShow
```

---

## Valid Transitions

| From       | To         |
| ---------- | ---------- |
| Waiting    | Called     |
| Waiting    | Cancelled  |
| Called     | InProgress |
| Called     | Skipped    |
| Called     | NoShow     |
| InProgress | Completed  |

---

## Invalid Transitions

Examples:

```text
Completed → Waiting
Cancelled → Waiting
NoShow → Called
Skipped → Called
Completed → Cancelled
```

All invalid transitions must be rejected.

---

# 3. User State Machine

## States

```text
Active
Inactive
```

---

## Lifecycle

```text
Active
  ↓
Inactive
  ↓
Active
```

---

## Rules

Inactive users:

* Cannot authenticate
* Cannot create bookings
* Cannot access protected endpoints

Historical data remains preserved.

---

# 4. Branch State Machine

## States

```text
Active
Inactive
```

---

## Lifecycle

```text
Active
  ↓
Inactive
```

---

## Rules

Inactive branches:

* Cannot accept bookings
* Do not appear in public branch listings
* Preserve historical records

---

# 5. Service State Machine

## States

```text
Active
Inactive
```

---

## Lifecycle

```text
Active
  ↓
Inactive
```

---

## Rules

Inactive services:

* Cannot accept new bookings
* Remain available in historical reports

---

# 6. Branch Service State Machine

Represents a service enabled inside a specific branch.

---

## States

```text
Active
Inactive
```

---

## Lifecycle

```text
Active
  ↓
Inactive
```

---

## Rules

Inactive branch services:

* Cannot receive new tickets
* Existing historical tickets remain valid

---

# 7. Window State Machine

## States

```text
Open
Closed
```

---

## Lifecycle

```text
Closed
  ↓
Open
  ↓
Closed
```

---

## Rules

Open windows:

* Can receive staff assignments

Closed windows:

* Cannot receive staff assignments

---

# 8. Push Subscription State Machine

## States

```text
Active
Expired
```

---

## Lifecycle

```text
Active
  ↓
Expired
```

---

## Transition Trigger

When browser push delivery repeatedly fails.

---

## Rules

Expired subscriptions:

* Receive no notifications
* Can be replaced by a new subscription

---

# 9. OTP State Machine

## States

```text
Generated
Verified
Expired
```

---

## Lifecycle

```text
Generated
│
├── Verified
│
└── Expired
```

---

## Rules

Generated OTP:

* Valid for configured duration

Verified OTP:

* Cannot be reused

Expired OTP:

* Cannot be verified

---

# 10. Queue State Machine

For MVP queues are always active.

---

## States

```text
Active
```

---

No additional queue states are required in MVP.

---

# 11. Booking State Definition

A booking is considered Active when ticket state is:

```text
Waiting
Called
InProgress
```

---

A booking is considered Inactive when ticket state is:

```text
Completed
Cancelled
Skipped
NoShow
```

---

# 12. State Validation Rules

Before every state transition the system must:

1. Validate current state.
2. Validate target state.
3. Validate transition rule.
4. Reject invalid transitions.
5. Log successful transitions.

---

# 13. Audit Events

The following transitions should generate audit events:

## Ticket Events

```text
Waiting → Called
Called → InProgress
InProgress → Completed
Called → NoShow
Called → Skipped
Waiting → Cancelled
```

---

## Administrative Events

```text
User Activated
User Deactivated

Branch Activated
Branch Deactivated

Service Activated
Service Deactivated
```

---

# 14. Implementation Recommendation

Use explicit enums in code.

Example:

```typescript
export enum TicketStatus {
  Waiting = "Waiting",
  Called = "Called",
  InProgress = "InProgress",
  Completed = "Completed",
  Cancelled = "Cancelled",
  Skipped = "Skipped",
  NoShow = "NoShow"
}
```

State transitions should be centralized in domain services rather than implemented directly in controllers.

This guarantees consistent behavior across the entire platform.

```
```
