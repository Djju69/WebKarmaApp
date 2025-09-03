# API Documentation

## Table of Contents
- [Authentication](#authentication)
  - [Login](#login)
  - [Refresh Token](#refresh-token)
  - [Test Token](#test-token)
- [Users](#users)
  - [Get Current User](#get-current-user)
  - [List Users](#list-users)
  - [Create User](#create-user)
  - [Get User by ID](#get-user-by-id)
  - [Update User](#update-user)
  - [Delete User](#delete-user)

## Authentication

### Login

Authenticate user and get access token.

```http
POST /api/v1/auth/login
```

**Request Body (form-data):**
- `username` (required): User's email or username
- `password` (required): User's password

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Refresh Token

Get a new access token using a refresh token.

```http
POST /api/v1/auth/refresh
```

**Request Body (JSON):**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Test Token

Test if the provided access token is valid.

```http
POST /api/v1/auth/test-token
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T00:00:00"
}
```

## Users

### Get Current User

Get information about the currently authenticated user.

```http
GET /api/v1/users/me
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T00:00:00",
  "roles": ["user"]
}
```

### List Users

List all users (admin only).

```http
GET /api/v1/users/?skip=0&limit=100
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100, max: 1000)

**Response:**
```json
[
  {
    "id": 1,
    "email": "admin@example.com",
    "username": "admin",
    "is_active": true,
    "is_superuser": true,
    "created_at": "2023-01-01T00:00:00"
  },
  {
    "id": 2,
    "email": "user@example.com",
    "username": "user",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2023-01-02T00:00:00"
  }
]
```

### Create User

Create a new user (admin only).

```http
POST /api/v1/users/
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "SecurePass123!",
  "first_name": "New",
  "last_name": "User",
  "is_active": true,
  "role_ids": [2]
}
```

**Password Requirements:**
- At least 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

**Response (201 Created):**
```json
{
  "id": 3,
  "email": "newuser@example.com",
  "username": "newuser",
  "first_name": "New",
  "last_name": "User",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-01-03T00:00:00",
  "updated_at": "2023-01-03T00:00:00"
}
```

### Get User by ID

Get user details by ID (admin only).

```http
GET /api/v1/users/{user_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-01T00:00:00",
  "roles": [
    {
      "id": 1,
      "name": "user",
      "description": "Regular user",
      "permissions": [
        {
          "id": 1,
          "name": "users:read",
          "description": "Read user information"
        }
      ]
    }
  ]
}
```

### Update User

Update user information (admin only).

```http
PUT /api/v1/users/{user_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "first_name": "John Updated",
  "last_name": "Doe Updated",
  "is_active": true,
  "role_ids": [1, 2]
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John Updated",
  "last_name": "Doe Updated",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-03T00:00:00"
}
```

### Delete User

Delete a user (admin only).

```http
DELETE /api/v1/users/{user_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```
204 No Content
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

## Rate Limiting

API is rate limited to 1000 requests per hour per IP address. The following headers are included in rate-limited responses:

- `X-RateLimit-Limit`: The maximum number of requests allowed in a time window
- `X-RateLimit-Remaining`: The number of requests remaining in the current window
- `X-RateLimit-Reset`: The time at which the current rate limit window resets (UTC timestamp)

## Authentication

All endpoints except `/auth/login` and `/auth/refresh` require authentication. Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

## Response Format

All successful responses are returned in JSON format with the following structure:

```json
{
  "data": {},  // Response data (if any)
  "meta": {}   // Metadata (pagination, etc.)
}
```

Error responses follow the format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable error message",
    "details": {}  // Additional error details (if any)
  }
}
```
