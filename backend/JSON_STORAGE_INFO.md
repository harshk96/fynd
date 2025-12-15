# JSON-Based Storage System

## Overview
This system uses JSON files for all data storage - no database required!

## Storage Files

### 1. `users.json` - User Authentication Data
Location: `backend/users.json`

Stores all user accounts with:
- `_id`: Unique user identifier
- `username`: Unique username
- `email`: Unique email address
- `password`: Bcrypt hashed password (never plain text!)
- `role`: "user" or "admin"
- `created_at`: Account creation timestamp

Example:
```json
[
  {
    "_id": "user_20241201120000_0",
    "username": "john_doe",
    "email": "john@example.com",
    "password": "$2b$12$...",
    "role": "user",
    "created_at": "2024-12-01T12:00:00"
  }
]
```

### 2. `submissions.json` - Review Submissions
Location: `backend/submissions.json`

Stores all review submissions with:
- `id`: Unique submission identifier
- `user_id`: ID of the user who submitted
- `username`: Username of submitter
- `rating`: Star rating (1-5)
- `review_text`: Review content
- `ai_response`: AI-generated response
- `ai_summary`: AI-generated summary
- `ai_recommended_actions`: AI recommendations
- `predicted_stars`: AI-predicted rating
- `prediction_explanation`: Explanation of prediction
- `timestamp`: Submission timestamp

## Security Features

1. **Password Hashing**: All passwords are hashed using bcrypt before storage
2. **JWT Tokens**: Secure token-based authentication
3. **No Plain Text**: Passwords are never stored in plain text

## File Management

- Files are automatically created if they don't exist
- Data is appended/updated in real-time
- No database setup required
- Perfect for development and small-scale deployments

## Notes

- For production with many users, consider migrating to a database
- JSON files are simple but may have performance limitations with large datasets
- Always backup JSON files before deployment

