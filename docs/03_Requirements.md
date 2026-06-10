# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines the functional and non-functional requirements for the Government Queue Tracking Platform.

The platform enables citizens to remotely join service queues, track queue progress, receive notifications, and reduce physical waiting time at government service branches.

The system also provides operational tools for staff, supervisors, and administrators to manage services, queues, users, and branch performance.

---

# 2. Scope

The system supports:

* Multiple government branches
* Multiple services per branch
* Service-based queue management
* OTP-based authentication
* Browser push notifications
* Role-based access control
* Queue tracking and monitoring
* Reporting and analytics

The system does not support:

* Appointment time slots
* Native mobile applications
* SMS notifications
* Email notifications
* Online payments
* Priority queue categories
* External government integrations

---

# 3. User Roles

The platform includes the following roles:

1. Guest
2. Citizen
3. Door Keeper
4. Counter Staff
5. Branch Supervisor
6. System Admin

---

# 4. Functional Requirements

## 4.1 Guest

### Purpose

Allow public users to monitor branch congestion before registration.

### Permissions

Guests may:

* View available branches
* View available services per branch
* View congestion levels
* View estimated waiting times
* View currently served ticket numbers

Guests may not:

* Join queues
* Create bookings
* Receive notifications
* Access protected pages

---

## 4.2 Citizen

### Purpose

Join and track service queues.

### Authentication

Citizens authenticate using:

* Phone number
* One-Time Password (OTP)

### Functional Requirements

#### Registration

The system shall allow citizens to:

* Register using a phone number
* Verify ownership through OTP
* Create a citizen profile

---

#### Queue Booking

The system shall allow citizens to:

* Select a branch
* Select a service
* Join a queue

The system shall:

* Validate booking eligibility
* Create a queue ticket
* Assign a queue number
* Calculate estimated waiting time

---

#### Active Booking Rule

A citizen may have only one active booking at a time.

Active bookings include:

* Waiting
* Called
* In Progress

Inactive bookings include:

* Completed
* Cancelled
* No Show

---

#### Queue Tracking

The system shall allow citizens to view:

* Queue number
* Current position
* Current ticket being served
* Estimated waiting time
* Ticket status

Updates shall be refreshed manually.

---

#### Booking Cancellation

Citizens may cancel active bookings.

Cancelled tickets are removed from the queue.

---

#### Notifications

Citizens shall receive browser push notifications when:

* Two citizens remain before their turn
* Their ticket is being called

---

#### Profile Management

Citizens shall be able to:

* View profile information
* Update profile information
* Change preferred language
* Manage notification permissions

---

## 4.3 Door Keeper

### Purpose

Assist walk-in citizens.

### Functional Requirements

The Door Keeper shall be able to:

* Search for existing citizens
* Register new citizens
* Create bookings on behalf of citizens
* View citizen booking information

The Door Keeper shall not:

* Modify queue ordering
* Serve tickets
* Access administrative functions

---

## 4.4 Counter Staff

### Purpose

Serve citizens and process queue tickets.

### Staff-Service Capability

A staff member may be qualified to perform multiple services.

Service qualifications are managed by the Branch Supervisor.

---

### Functional Requirements

Counter Staff shall be able to:

* View assigned branch queues
* View current queue status
* Call next ticket
* Mark ticket as completed
* Mark ticket as skipped
* Mark ticket as no-show

---

### Queue Selection Logic

When a staff member is qualified for multiple services, the system shall select the next service queue using a round-robin algorithm.

Empty queues shall be skipped automatically.

Detailed behavior is defined in the Queue Engine document.

---

## 4.5 Branch Supervisor

### Purpose

Manage branch operations.

### Functional Requirements

Branch Supervisors shall be able to:

#### Staff Management

* View branch staff
* Assign services to staff
* Remove services from staff

---

#### Window Management

* View windows
* Open windows
* Close windows

---

#### Operational Monitoring

* View active queues
* View queue lengths
* View current tickets
* View waiting citizens
* View branch congestion

---

#### Reporting

View:

* Daily transactions
* Service performance
* Average wait times
* No-show rates
* Cancellation rates
* Peak-hour statistics

---

## 4.6 System Admin

### Purpose

Manage organization-wide configuration.

### Functional Requirements

#### Branch Management

* Create branch
* Update branch
* Deactivate branch

---

#### Service Management

* Create service
* Edit service
* Delete service
* Configure service availability per branch
* Configure estimated service duration

---

#### User Management

* View users
* Activate users
* Deactivate users
* Assign roles

---

#### System Configuration

Configure:

* OTP settings
* Working hours
* Notification settings
* Queue rules
* No-show thresholds

---

#### Analytics

View organization-wide:

* Service demand
* Branch demand
* Wait times
* Cancellation statistics
* No-show statistics

---

# 5. Queue Requirements

## Queue Structure

A queue exists for each:

* Branch
* Service

Combination.

Examples:

* Passport @ Cairo Branch
* Passport @ Alexandria Branch
* National ID @ Cairo Branch

---

## Queue Ordering

Queues shall operate using FIFO ordering.

Citizens are served in the order they joined.

---

## Queue Numbering

Queue numbers shall be unique within a service queue.

Queue numbering resets daily.

---

## Queue Statuses

A ticket may have one of the following statuses:

* Waiting
* Called
* In Progress
* Completed
* Cancelled
* Skipped
* No Show

---

# 6. Notification Requirements

The system shall support browser push notifications.

The system shall:

* Store browser subscriptions
* Send queue alerts
* Track delivery attempts

Notifications shall be delivered when:

* Two citizens remain before the user's turn
* The user's ticket is called

---

# 7. Localization Requirements

The platform shall support:

* Arabic
* English

Users may switch languages at any time.

---

# 8. Reporting Requirements

The system shall generate:

* Daily transaction reports
* Service utilization reports
* Branch performance reports
* Wait-time reports
* Cancellation reports
* No-show reports
* Peak-hour reports

Reports shall be exportable.

---

# 9. Security Requirements

The system shall implement:

* OTP authentication
* JWT authorization
* Role-based access control
* Protected API endpoints
* Secure passwordless authentication

The system shall maintain audit logs for administrative actions.

---

# 10. Non-Functional Requirements

## Performance

* Queue operations should complete in under 1 second.
* Dashboard pages should load in under 3 seconds.
* Notification processing should occur in near real-time.

---

## Availability

Target availability:

99.5%

---

## Scalability

The platform shall support:

* Multiple branches
* Thousands of citizens
* Concurrent queue operations

without architectural redesign.

---

## Maintainability

The system shall use a modular architecture with clearly separated:

* Authentication
* Queue Management
* Notifications
* Reporting
* Administration

modules.

---

## Responsiveness

The platform shall function correctly on:

* Desktop browsers
* Mobile browsers
* Tablet browsers

without requiring a native application.
