# Government Queue Tracking Platform

Version: MVP 1.0

---

# 1. Purpose

This document defines the REST API contract between the frontend and backend.

All endpoints return JSON.

All protected endpoints require JWT authentication.

---

# 2. Authentication

## Request OTP

### Endpoint

```http
POST /auth/request-otp
```

### Request

```json
{
  "phoneNumber": "+201234567890"
}
```

### Response

```json
{
  "message": "OTP sent successfully"
}
```

---

## Verify OTP

### Endpoint

```http
POST /auth/verify-otp
```

### Request

```json
{
  "phoneNumber": "+201234567890",
  "otp": "123456"
}
```

### Response

```json
{
  "accessToken": "jwt-token",
  "user": {
    "id": "uuid",
    "fullName": "Ahmed",
    "roles": ["Citizen"]
  }
}
```

---

# 3. User APIs

## Get Current User

```http
GET /users/me
```

### Response

```json
{
  "id": "uuid",
  "fullName": "Ahmed",
  "phoneNumber": "+201234567890",
  "preferredLanguage": "en",
  "roles": ["Citizen"]
}
```

---

## Update Profile

```http
PUT /users/me
```

### Request

```json
{
  "fullName": "Ahmed Mohamed",
  "preferredLanguage": "ar"
}
```

### Response

```json
{
  "success": true
}
```

---

# 4. Branch APIs

## Get All Branches

```http
GET /branches
```

### Response

```json
[
  {
    "id": "uuid",
    "name": "Tanta Main Branch",
    "address": "Tanta"
  }
]
```

---

## Get Branch Details

```http
GET /branches/{branchId}
```

### Response

```json
{
  "id": "uuid",
  "name": "Tanta Main Branch",
  "services": [],
  "congestionLevel": "Medium"
}
```

---

# 5. Service APIs

## Get Branch Services

```http
GET /branches/{branchId}/services
```

### Response

```json
[
  {
    "id": "uuid",
    "name": "Passport Renewal",
    "estimatedDurationMinutes": 10
  }
]
```

---

# 6. Ticket APIs

## Create Booking

```http
POST /tickets
```

### Request

```json
{
  "branchId": "uuid",
  "serviceId": "uuid"
}
```

### Response

```json
{
  "ticketId": "uuid",
  "queueNumber": 102,
  "status": "Waiting",
  "position": 5,
  "estimatedWaitMinutes": 50
}
```

---

## Get My Active Ticket

```http
GET /tickets/my-active
```

### Response

```json
{
  "ticketId": "uuid",
  "queueNumber": 102,
  "status": "Waiting",
  "position": 5,
  "estimatedWaitMinutes": 50,
  "currentServingNumber": 97
}
```

---

## Get Ticket Details

```http
GET /tickets/{ticketId}
```

### Response

```json
{
  "ticketId": "uuid",
  "queueNumber": 102,
  "status": "Waiting",
  "position": 5
}
```

---

## Cancel Ticket

```http
POST /tickets/{ticketId}/cancel
```

### Response

```json
{
  "success": true
}
```

---

# 7. Queue APIs

## Get Queue Status

```http
GET /queues/{branchId}/{serviceId}
```

### Response

```json
{
  "currentServingNumber": 97,
  "waitingCount": 24,
  "averageWaitMinutes": 50
}
```

---

# 8. Door Keeper APIs

## Search Citizen

```http
GET /door-keeper/citizens/search?phone=+201234567890
```

### Response

```json
{
  "id": "uuid",
  "fullName": "Ahmed Mohamed"
}
```

---

## Create Citizen

```http
POST /door-keeper/citizens
```

### Request

```json
{
  "fullName": "Ahmed Mohamed",
  "phoneNumber": "+201234567890"
}
```

### Response

```json
{
  "id": "uuid"
}
```

---

## Create Booking For Citizen

```http
POST /door-keeper/bookings
```

### Request

```json
{
  "citizenId": "uuid",
  "branchId": "uuid",
  "serviceId": "uuid"
}
```

### Response

```json
{
  "ticketId": "uuid",
  "queueNumber": 103
}
```

---

# 9. Staff APIs

## Get Eligible Queues

```http
GET /staff/queues
```

### Response

```json
[
  {
    "serviceId": "uuid",
    "serviceName": "Passport Renewal",
    "waitingCount": 14
  }
]
```

---

## Call Next

```http
POST /staff/call-next
```

### Response

```json
{
  "ticketId": "uuid",
  "queueNumber": 104,
  "serviceName": "Passport Renewal",
  "status": "Called"
}
```

---

## Complete Ticket

```http
POST /staff/tickets/{ticketId}/complete
```

### Response

```json
{
  "success": true
}
```

---

## Skip Ticket

```http
POST /staff/tickets/{ticketId}/skip
```

### Response

```json
{
  "success": true
}
```

---

## Mark No Show

```http
POST /staff/tickets/{ticketId}/no-show
```

### Response

```json
{
  "success": true
}
```

---

# 10. Supervisor APIs

## Get Branch Dashboard

```http
GET /supervisor/dashboard
```

### Response

```json
{
  "activeQueues": 6,
  "waitingCitizens": 42,
  "todayCompleted": 118
}
```

---

## Get Branch Staff

```http
GET /supervisor/staff
```

---

## Assign Service To Staff

```http
POST /supervisor/staff/{staffId}/services
```

### Request

```json
{
  "serviceId": "uuid"
}
```

---

## Remove Service From Staff

```http
DELETE /supervisor/staff/{staffId}/services/{serviceId}
```

---

## Get Reports

```http
GET /supervisor/reports
```

### Response

```json
{
  "averageWaitMinutes": 18,
  "completedTickets": 350,
  "noShows": 21
}
```

---

# 11. Admin APIs

## Get Users

```http
GET /admin/users
```

---

## Create Branch

```http
POST /admin/branches
```

### Request

```json
{
  "name": "Tanta Branch",
  "address": "Tanta"
}
```

---

## Create Service

```http
POST /admin/services
```

### Request

```json
{
  "name": "Passport Renewal",
  "description": "Passport renewal service"
}
```

---

## Assign Service To Branch

```http
POST /admin/branch-services
```

### Request

```json
{
  "branchId": "uuid",
  "serviceId": "uuid",
  "estimatedDurationMinutes": 10
}
```

---

# 12. Push Notification APIs

## Register Browser Subscription

```http
POST /notifications/subscribe
```

### Request

```json
{
  "endpoint": "...",
  "p256dhKey": "...",
  "authKey": "..."
}
```

### Response

```json
{
  "success": true
}
```

---

# 13. Standard Error Response

```json
{
  "success": false,
  "message": "Citizen already has an active booking",
  "code": "ACTIVE_BOOKING_EXISTS"
}
```

---

# 14. HTTP Status Codes

| Code | Meaning               |
| ---- | --------------------- |
| 200  | Success               |
| 201  | Created               |
| 400  | Validation Error      |
| 401  | Unauthorized          |
| 403  | Forbidden             |
| 404  | Not Found             |
| 409  | Conflict              |
| 500  | Internal Server Error |

---

```
```
