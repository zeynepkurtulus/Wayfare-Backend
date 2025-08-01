# 🗺️ Wayfare Travel Planning API Documentation

**Base URL:** `https://api.wayfare.com`  
**Authentication:** Bearer Token (JWT)  
**Content-Type:** `application/json`

## ⚙️ **Configuration**

### **Email Configuration**
- **Location:** `backend/config/email.py`
- **Development Mode:** Email sending suppressed, codes printed to console
- **Production Options:** Gmail (App Password), Mailtrap, Outlook
- **Verification Codes:** 6-digit, 10-minute expiry, in-memory storage

To switch email providers:
1. Edit `backend/config/email.py` 
2. Change `mail_config = your_chosen_config`
3. Update credentials and restart server

---

## 👤 **User Management Endpoints**

### **@POST /user/register**

It allows users to:
- Create a new user account
- Register with username, email, and personal information
- Automatically hash passwords and set default preferences

**Request Body:**
```json
{
    "username": "traveler123",
    "password": "securepass123", 
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
}
```

**Response:**
```json
{
    "message": "User registered successfully",
    "success": true,
    "user_id": "64a1b2c3d4e5f6789abcdef0"
}
```

---

### **@POST /user/login**

It allows users to:
- Authenticate with username and password
- Receive access token for API authorization
- Maintain secure session management

**Request Body:**
```json
{
    "username": "traveler123",
    "password": "securepass123"
}
```

**Response:**
```json
{
    "message": "User logged in successfully",
    "success": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### **@POST /user/addInfo**
🔒 **Requires Authentication**

It allows users to:
- Add travel preferences and interests
- Set budget and travel style preferences
- Define home city for personalized recommendations

**Request Body:**
```json
{
    "preferences": {
        "interests": ["museums", "architecture", "food"],
        "budget": "medium",
        "travel_style": "moderate"
    },
    "home_city": "New York"
}
```

**Response:**
```json
{
    "message": "User information updated successfully",
    "success": true,
    "status_code": 200
}
```

---

### **@GET /user/getCurrentUser**
🔒 **Requires Authentication**

It allows users to:
- Retrieve current user profile information
- Access personal preferences and settings
- View account details and travel preferences

**Response:**
```json
{
    "user_id": "64a1b2c3d4e5f6789abcdef0",
    "email": "user@example.com",
    "username": "traveler123",
    "name": "John",
    "surname": "Doe",
    "preferences": {
        "interests": ["museums", "architecture", "food"],
        "budget": "medium", 
        "travel_style": "moderate"
    },
    "home_city": "New York"
}
```

---

### **@POST /user/changePassword**
🔒 **Requires Authentication**

It allows users to:
- Update account password securely
- Verify current password before change
- Ensure password confirmation matches

**Request Body:**
```json
{
    "current_password": "oldpassword123",
    "new_password": "newpassword456",
    "confirm_password": "newpassword456"
}
```

**Response:**
```json
{
    "message": "Password changed successfully",
    "success": true,
    "status_code": 200
}
```

---

### **@DELETE /user/delete**
🔒 **Requires Authentication**

It allows users to:
- Permanently delete their account
- Remove all associated data and routes
- Verify identity with password confirmation

**Request Body:**
```json
{
    "password": "userpassword123"
}
```

**Response:**
```json
{
    "message": "User account deleted successfully",
    "success": true,
    "status_code": 200
}
```

---

### **@POST /user/sendVerification**

It allows users to:
- Send verification code to email address
- Start email verification process during registration
- Receive 6-digit verification code valid for 10 minutes

**Request Body:**
```json
{
    "email": "user@example.com"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Code sent successfully",
    "status_code": 200
}
```

---

### **@POST /user/sendVerification/verifyCode**

It allows users to:
- Verify email verification code
- Complete email verification process
- Validate 6-digit code within 10-minute expiry

**Request Body:**
```json
{
    "verification_code": "123456"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Code verified successfully",
    "status_code": 200
}
```

**Error Responses:**
```json
// Invalid code
{
    "detail": "Invalid verification code"
}

// Expired code (after 10 minutes)
{
    "detail": "Verification code has expired"
}
```

---

## 🗺️ **Route Management Endpoints**

### **@POST /route/create**
🔒 **Requires Authentication**

It allows users to:
- Create a customized daily schedule of activities (linked to places)
- Specify must-visit places with notes and preferences
- Generate AI-powered route recommendations based on travel style

**Request Body:**
```json
{
    "title": "Trip to Rome",
    "city": "Rome", 
    "start_date": "2025-06-01",
    "end_date": "2025-06-07",
    "category": "city_break",
    "season": "summer",
    "must_visit": [
        {
            "place_id": "abc123",
            "place_name": "Colosseum",
            "address": "Rome",
            "notes": "Morning preferred",
            "source": "google",
            "coordinates": { "lat": 41.89, "lng": 12.49 }
        },
        {
            "place_name": "Hidden Bookstore",
            "notes": "TikTok place",
            "source": "user"
        }
    ],
    "days": [
        {
            "date": "2025-06-01",
            "activities": [
                {
                    "place_id": "abc123",
                    "place_name": "Colosseum",
                    "time": "10:00",
                    "notes": "Visit the Colosseum"
                }
            ]
        }
    ]
}
```

**Response:**
```json
{
    "message": "Route created successfully",
    "success": true,
    "route_id": "string",
    "status_code": 200
}
```

---

### **@GET /routes/user**
🔒 **Requires Authentication**

It allows users to:
- Retrieve all routes created by the authenticated user
- View route summaries and basic information
- Access personal travel planning history

**Response:**
```json
{
    "success": true,
    "message": "User routes retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "route_id": "64a1b2c3d4e5f6789abcdef1",
            "user_id": "64a1b2c3d4e5f6789abcdef0",
            "title": "Trip to Rome",
            "city": "Rome",
            "country": "Italy",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "budget": "medium",
            "travel_style": "moderate",
            "category": "city_break",
            "season": "summer",
            "stats": {
                "views_count": 5,
                "copies_count": 2,
                "likes_count": 8
            },
            "created_at": "2024-12-01T10:00:00Z",
            "updated_at": "2024-12-01T10:00:00Z"
        }
    ]
}
```

---

### **@GET /routes/{route_id}**
🔒 **Requires Authentication**

It allows users to:
- Retrieve detailed information for a specific route
- Access complete daily schedules and activities
- View all must-visit places and their details

**Path Parameters:**
- `route_id` (string): Unique identifier of the route

**Response:**
```json
{
    "success": true,
    "message": "Route retrieved successfully",
    "status_code": 200,
    "data": {
        "route_id": "64a1b2c3d4e5f6789abcdef1",
        "user_id": "64a1b2c3d4e5f6789abcdef0",
        "title": "Trip to Rome",
        "city": "Rome",
        "country": "Italy",
        "start_date": "2025-06-01",
        "end_date": "2025-06-07",
        "budget": "medium",
        "travel_style": "moderate", 
        "category": "city_break",
        "season": "summer",
        "stats": {
            "views_count": 5,
            "copies_count": 2,
            "likes_count": 8
        },
        "must_visit": [
            {
                "place_id": "abc123",
                "place_name": "Colosseum",
                "address": "Rome",
                "coordinates": { "lat": 41.89, "lng": 12.49 },
                "notes": "Morning preferred",
                "source": "google",
                "opening_hours": {
                    "monday": "08:30-19:15",
                    "tuesday": "08:30-19:15"
                }
            }
        ],
        "days": [
            {
                "date": "2025-06-01",
                "activities": [
                    {
                        "place_id": "abc123",
                        "place_name": "Colosseum",
                        "time": "10:00",
                        "notes": "Visit the Colosseum"
                    }
                ]
            }
        ],
        "created_at": "2024-12-01T10:00:00Z",
        "updated_at": "2024-12-01T10:00:00Z"
    }
}
```

---

### **@PUT /routes/{route_id}**
🔒 **Requires Authentication**

It allows users to:
- Update existing route information
- Modify travel dates, destinations, or preferences
- Add or remove must-visit places and activities

**Path Parameters:**
- `route_id` (string): Unique identifier of the route

**Request Body:**
```json
{
    "title": "Updated Trip to Rome",
    "city": "Rome",
    "start_date": "2025-06-15",
    "end_date": "2025-06-20",
    "category": "cultural",
    "season": "summer",
    "must_visit": [
        {
            "place_name": "Vatican Museums",
            "notes": "Book tickets in advance",
            "source": "user"
        }
    ]
}
```

**Response:**
```json
{
    "message": "Route updated successfully",
    "success": true,
    "status_code": 200
}
```

---

### **@DELETE /routes/{route_id}**
🔒 **Requires Authentication**

It allows users to:
- Permanently delete a specific route
- Remove all associated activities and schedules
- Clean up travel planning history

**Path Parameters:**
- `route_id` (string): Unique identifier of the route

**Response:**
```json
{
    "message": "Route deleted successfully",
    "success": true,
    "status_code": 200
}
```

---

### **@GET /routes/public**
🔒 **Requires Authentication**

It allows users to:
- Browse publicly shared routes from other users
- Filter routes by category, season, and budget
- Discover travel inspiration and ideas

**Query Parameters:**
- `category` (string, optional): Filter by route category
- `season` (string, optional): Filter by travel season  
- `budget` (string, optional): Filter by budget level
- `limit` (int): Maximum number of routes to return (default: 10)

**Response:**
```json
{
    "success": true,
    "message": "Public routes retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "route_id": "64a1b2c3d4e5f6789abcdef2",
            "user_id": "64a1b2c3d4e5f6789abcdef9",
            "title": "Rome in 5 Days",
            "city": "Rome",
            "country": "Italy",
            "category": "city_break",
            "season": "spring",
            "budget": "medium",
            "stats": {
                "views_count": 156,
                "copies_count": 23,
                "likes_count": 89
            }
        }
    ]
}
```

---

## 📍 **Places Management Endpoints**

### **@GET /places/city**
🔒 **Requires Authentication**

It allows users to:
- Retrieve all available places in a specific city
- Access place details including coordinates and categories
- Browse destinations for route planning

**Query Parameters:**
- `city` (string): Name of the city to search places in

**Response:**
```json
{
    "success": true,
    "message": "Places retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "place_id": "abc123",
            "name": "Colosseum",
            "address": "Piazza del Colosseo, 1, 00184 Roma RM, Italy",
            "coordinates": { "lat": 41.8902, "lng": 12.4922 },
            "category": "historical_site",
            "rating": 4.5,
            "price_level": 3,
            "opening_hours": {
                "monday": "08:30-19:15",
                "tuesday": "08:30-19:15"
            }
        }
    ]
}
```

---

### **@POST /places/id**
🔒 **Requires Authentication**

It allows users to:
- Retrieve detailed information for specific places by their IDs
- Get multiple place details in a single request
- Access comprehensive place data for route planning

**Request Body:**
```json
{
    "place_ids": ["abc123", "def456", "ghi789"]
}
```

**Response:**
```json
{
    "success": true,
    "message": "Places retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "place_id": "abc123",
            "name": "Colosseum",
            "address": "Piazza del Colosseo, 1, 00184 Roma RM, Italy",
            "coordinates": { "lat": 41.8902, "lng": 12.4922 },
            "category": "historical_site",
            "rating": 4.5,
            "price_level": 3,
            "opening_hours": {
                "monday": "08:30-19:15",
                "tuesday": "08:30-19:15"
            }
        }
    ]
}
```

---

### **@POST /places/search**
🔒 **Requires Authentication**

It allows users to:
- Search for places using text queries
- Filter results by city, category, and other criteria
- Find specific attractions and points of interest

**Request Body:**
```json
{
    "query": "museum",
    "city": "Rome",
    "category": "cultural",
    "limit": 20
}
```

**Response:**
```json
{
    "success": true,
    "message": "Search results retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "place_id": "mus123",
            "name": "Vatican Museums",
            "address": "00120 Vatican City",
            "coordinates": { "lat": 41.9065, "lng": 12.4536 },
            "category": "museum",
            "rating": 4.4,
            "price_level": 4
        }
    ]
}
```

---

### **@POST /places/autocomplete**
🔒 **Requires Authentication**

It allows users to:
- Get autocomplete suggestions for place names
- Provide real-time search assistance
- Improve user experience during place selection

**Request Body:**
```json
{
    "query": "colo",
    "city": "Rome",
    "limit": 5
}
```

**Response:**
```json
{
    "success": true,
    "message": "Autocomplete results retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "place_id": "abc123",
            "name": "Colosseum",
            "category": "historical_site"
        },
        {
            "place_id": "abc124", 
            "name": "Colonna di Traiano",
            "category": "monument"
        }
    ]
}
```

---

## 🏙️ **Cities Management Endpoints**

### **@GET /cities/all**
🔒 **Requires Authentication**

It allows users to:
- Retrieve a complete list of all available cities
- Access city information including country, coordinates, timezone, and status
- Browse destinations for travel planning with geographical data

**Response:**
```json
{
    "success": true,
    "message": "Cities retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "city_id": "68824f500e3bd95431ee840c",
            "name": "Rome",
            "country": "Italy",
            "country_id": "IT",
            "active": true,
            "coordinates": {
                "lat": 41.9028,
                "lng": 12.4964
            },
            "timezone": "Europe/Rome",
            "created_at": "2025-07-30T15:34:43.551000",
            "updated_at": "2025-07-30T15:34:43.551000"
        },
        {
            "city_id": "68824f50960d81e2439af257",
            "name": "Paris", 
            "country": "France",
            "country_id": "FR",
            "active": true,
            "coordinates": {
                "lat": 48.8566,
                "lng": 2.3522
            },
            "timezone": "Europe/Paris",
            "created_at": "2025-07-30T15:34:43.551000",
            "updated_at": "2025-07-30T15:34:43.551000"
        }
    ]
}
```

---

### **@POST /cities/specific**
🔒 **Requires Authentication**

It allows users to:
- Retrieve cities within a specific country
- Filter destinations by country preference with complete geographical data
- Narrow down location options for trip planning with coordinates and timezone info

**Request Body:**
```json
{
    "country": "Italy"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Cities in Italy retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "city_id": "68824f500e3bd95431ee840c",
            "name": "Rome",
            "country": "Italy",
            "country_id": "IT",
            "active": true,
            "coordinates": {
                "lat": 41.9028,
                "lng": 12.4964
            },
            "timezone": "Europe/Rome",
            "created_at": "2025-07-30T15:34:43.551000",
            "updated_at": "2025-07-30T15:34:43.551000"
        },
        {
            "city_id": "68824f50b1c9d54783ee842f",
            "name": "Milan",
            "country": "Italy",
            "country_id": "IT", 
            "active": true,
            "coordinates": {
                "lat": 45.4642,
                "lng": 9.1900
            },
            "timezone": "Europe/Rome",
            "created_at": "2025-07-30T15:34:43.551000",
            "updated_at": "2025-07-30T15:34:43.551000"
        }
    ]
}
```

---

## 🌍 **Countries Management Endpoints**

### **@GET /countries/all**
🔒 **Requires Authentication**

It allows users to:
- Retrieve a complete list of all available countries
- Access country information with creation/update timestamps
- Browse destinations by country for travel planning

**Response:**
```json
{
    "success": true,
    "message": "Countries fetched successfully",
    "status_code": 200,
    "data": [
        {
            "name": "Italy",
            "country_id": "IT",
            "region": "Europe",
            "active": true,
            "created_at": "2025-07-30T16:06:03.201000",
            "updated_at": "2025-07-30T16:06:03.201000"
        },
        {
            "name": "France",
            "country_id": "FR",
            "region": "Europe",
            "active": true,
            "created_at": "2025-07-30T16:06:03.201000",
            "updated_at": "2025-07-30T16:06:03.201000"
        }
    ]
}
```

---

### **@POST /countries/region**
🔒 **Requires Authentication**

It allows users to:
- Retrieve countries within a specific geographical region
- Filter destinations by regional preferences
- Explore travel options by geographical area

**Request Body:**
```json
{
    "region": "Southern Europe"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Countries by region retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "_id": "country123",
            "name": "Italy",
            "region": "Southern Europe"
        },
        {
            "_id": "country126",
            "name": "Spain", 
            "region": "Southern Europe"
        }
    ]
}
```

---

### **@POST /countries/search**
🔒 **Requires Authentication**

It allows users to:
- Search for countries using text queries
- Find specific destinations quickly
- Filter countries by name or other criteria

**Request Body:**
```json
{
    "query": "ital",
    "limit": 10
}
```

**Response:**
```json
{
    "success": true,
    "message": "Search results retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "_id": "country123",
            "name": "Italy",
            "region": "Southern Europe"
        }
    ]
}
```

---

### **@GET /countries/allRegions**
🔒 **Requires Authentication**

It allows users to:
- Retrieve a complete list of all geographical regions
- Access regional classification for countries
- Browse destinations by geographical regions

**Response:**
```json
{
    "success": true,
    "message": "Regions retrieved successfully", 
    "status_code": 200,
    "data": [
        "Northern Europe",
        "Southern Europe", 
        "Western Europe",
        "Eastern Europe",
        "North America",
        "South America",
        "Asia",
        "Africa",
        "Oceania"
    ]
}
```

---

## 🔐 **Authentication & Error Handling**

### **Authentication**
- All endpoints marked with 🔒 require a valid JWT token
- Include token in the `Authorization` header: `Bearer <your_jwt_token>`
- Tokens expire after 30 minutes and need to be refreshed

### **Common Error Responses**

**401 Unauthorized:**
```json
{
    "detail": "Could not validate credentials",
    "success": false,
    "status_code": 401
}
```

**400 Bad Request:**
```json
{
    "detail": "Invalid input data",
    "success": false,
    "status_code": 400
}
```

**404 Not Found:**
```json
{
    "detail": "Resource not found",
    "success": false,
    "status_code": 404
}
```

**500 Internal Server Error:**
```json
{
    "detail": "Internal server error",
    "success": false,
    "status_code": 500
}
```

---

## 📊 **API Usage Guidelines**

### **Rate Limiting**
- 1000 requests per hour per authenticated user
- 100 requests per hour for unauthenticated endpoints

### **Data Formats**
- All dates should be in `YYYY-MM-DD` format
- Coordinates use decimal degrees (latitude, longitude)
- Times are in 24-hour format `HH:MM`

### **Travel Styles**
- `relaxed`: Slower pace, longer visits, more downtime
- `moderate`: Balanced schedule with reasonable activities
- `accelerated`: Fast-paced, maximum activities per day

### **Budget Levels**
- `low`: Budget-conscious options
- `medium`: Balanced cost options  
- `high`: Premium experiences

### **Categories**
- `city_break`: Urban exploration and cultural sites
- `beach`: Coastal and water-based activities
- `mountain`: Outdoor and adventure activities
- `road_trip`: Multi-destination driving routes

---

## 📝 **Feedback Management Endpoints**

### **@POST /feedback/place**

It allows users to:
- Submit feedback and ratings for places they've visited
- Add comments about their experience
- Provide visit date information
- Prevent duplicate feedback for the same place

**Request Body:**
```json
{
    "place_id": "ChIJyWEHuEmuEmsRm9hTkapTCrk",
    "rating": 5,
    "comment": "Amazing place! The view was breathtaking and the staff was very friendly.",
    "visited_on": "2024-12-01"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Place feedback submitted successfully",
    "status_code": 201,
    "feedback_id": "64f8a1b2c3d4e5f6789abc01",
    "created_at": "2024-12-01T10:30:00Z"
}
```

---

### **@GET /feedback/place/{place_id}**

It allows users to:
- Retrieve all feedback for a specific place
- View ratings and comments from other users
- Access feedback history and statistics

**Response:**
```json
{
    "success": true,
    "message": "Retrieved 15 feedback entries for place",
    "status_code": 200,
    "data": [
        {
            "feedback_id": "64f8a1b2c3d4e5f6789abc01",
            "user_id": "64a1b2c3d4e5f6789abcdef0",
            "place_id": "ChIJyWEHuEmuEmsRm9hTkapTCrk",
            "rating": 5,
            "comment": "Amazing place! The view was breathtaking.",
            "visited_on": "2024-12-01",
            "created_at": "2024-12-01T10:30:00Z",
            "updated_at": "2024-12-01T10:30:00Z"
        }
    ]
}
```

---

### **@GET /feedback/place/{place_id}/user/{user_id}**

It allows users to:
- Retrieve specific user's feedback for a place
- Check if a user has already provided feedback
- Access user-specific feedback details

**Response:**
```json
{
    "success": true,
    "message": "User feedback retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "feedback_id": "64f8a1b2c3d4e5f6789abc01",
            "user_id": "64a1b2c3d4e5f6789abcdef0",
            "place_id": "ChIJyWEHuEmuEmsRm9hTkapTCrk",
            "rating": 5,
            "comment": "Amazing place!",
            "visited_on": "2024-12-01",
            "created_at": "2024-12-01T10:30:00Z",
            "updated_at": "2024-12-01T10:30:00Z"
        }
    ]
}
```

---

### **@PUT /feedback/place/{feedback_id}**

It allows users to:
- Update their existing place feedback
- Modify rating, comment, or visit date
- Maintain feedback history with updated timestamps

**Request Body:**
```json
{
    "rating": 4,
    "comment": "Updated review - still great but had some issues.",
    "visited_on": "2024-12-02"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Place feedback updated successfully",
    "status_code": 200,
    "updated_at": "2024-12-01T11:45:00Z"
}
```

---

### **@DELETE /feedback/place/{feedback_id}**

It allows users to:
- Delete their own place feedback
- Remove feedback from the system
- Maintain data integrity with proper authorization checks

**Response:**
```json
{
    "success": true,
    "message": "Place feedback deleted successfully",
    "status_code": 200,
    "deleted_at": "2024-12-01T12:00:00Z"
}
```

---

### **@GET /feedback/place/{place_id}/stats**

It allows users to:
- Get aggregated statistics for place feedback
- View average ratings and rating distribution
- Access comprehensive feedback analytics

**Response:**
```json
{
    "success": true,
    "message": "Place feedback statistics retrieved successfully",
    "status_code": 200,
    "data": {
        "total_feedback": 120,
        "average_rating": 4.2,
        "rating_distribution": {
            "1": 5,
            "2": 10,
            "3": 25,
            "4": 35,
            "5": 45
        }
    }
}
```

---

### **@POST /feedback/route**

It allows users to:
- Submit feedback and ratings for routes they've followed
- Share their experience with route planning
- Help other users with route recommendations

**Request Body:**
```json
{
    "route_id": "68877b97cd6e495f565e416c",
    "rating": 4,
    "comment": "Great route! Well planned with good timing between locations.",
    "visited_on": "2024-12-01"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Route feedback submitted successfully",
    "status_code": 201,
    "feedback_id": "64f8a1b2c3d4e5f6789abc02",
    "created_at": "2024-12-01T14:30:00Z"
}
```

---

### **@GET /feedback/route/{route_id}**

It allows users to:
- Retrieve all feedback for a specific route
- View user experiences and recommendations
- Access route quality information

**Response:**
```json
{
    "success": true,
    "message": "Retrieved 8 feedback entries for route",
    "status_code": 200,
    "data": [
        {
            "feedback_id": "64f8a1b2c3d4e5f6789abc02",
            "user_id": "64a1b2c3d4e5f6789abcdef0",
            "route_id": "68877b97cd6e495f565e416c",
            "rating": 4,
            "comment": "Great route! Well planned.",
            "visited_on": "2024-12-01",
            "created_at": "2024-12-01T14:30:00Z",
            "updated_at": "2024-12-01T14:30:00Z"
        }
    ]
}
```

---

### **@GET /feedback/route/{route_id}/user/{user_id}**

It allows users to:
- Retrieve specific user's feedback for a route
- Check if a user has already provided route feedback
- Access user-specific route feedback details

**Response:**
```json
{
    "success": true,
    "message": "User route feedback retrieved successfully",
    "status_code": 200,
    "data": [
        {
            "feedback_id": "64f8a1b2c3d4e5f6789abc02",
            "user_id": "64a1b2c3d4e5f6789abcdef0",
            "route_id": "68877b97cd6e495f565e416c",
            "rating": 4,
            "comment": "Great route! Well planned.",
            "visited_on": "2024-12-01",
            "created_at": "2024-12-01T14:30:00Z",
            "updated_at": "2024-12-01T14:30:00Z"
        }
    ]
}
```

---

### **@PUT /feedback/route/{feedback_id}**

It allows users to:
- Update their existing route feedback
- Modify rating, comment, or visit date
- Maintain feedback history with updated timestamps

**Request Body:**
```json
{
    "rating": 3,
    "comment": "Updated review - route was okay but had some timing issues.",
    "visited_on": "2024-12-02"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Route feedback updated successfully",
    "status_code": 200,
    "updated_at": "2024-12-01T15:45:00Z"
}
```

---

### **@DELETE /feedback/route/{feedback_id}**

It allows users to:
- Delete their own route feedback
- Remove feedback from the system
- Maintain data integrity with proper authorization checks

**Response:**
```json
{
    "success": true,
    "message": "Route feedback deleted successfully",
    "status_code": 200,
    "deleted_at": "2024-12-01T16:00:00Z"
}
```

---

### **@GET /feedback/route/{route_id}/stats**

It allows users to:
- Get aggregated statistics for route feedback
- View average ratings and success metrics
- Access route performance analytics

**Response:**
```json
{
    "success": true,
    "message": "Route feedback statistics retrieved successfully",
    "status_code": 200,
    "data": {
        "total_feedback": 45,
        "average_rating": 4.1,
        "rating_distribution": {
            "1": 2,
            "2": 3,
            "3": 8,
            "4": 15,
            "5": 17
        }
    }
}
```

---

## 🗄️ **Database Collections Schema**

The Wayfare API uses MongoDB with the following collections structure:

### **User Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier
    "email": "user@example.com", // Required, unique
    "first_name": "John",
    "last_name": "Doe", 
    "username": "johndoe", // Display name, required
    "hashed_password": "bcrypt_hashed_password_string",
    "preferences": {
        "interests": ["Museums and Art Galleries", "Food & Drinks", "Outdoors", "Hidden Gems", "Family Friendly"],
        "budget": "medium", // can be: low, medium, high
        "travel_style": "relaxed" // can be: relaxed, moderate, accelerated
    },
    "home_city": "New York"
}
```

### **Route Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier  
    "route_id": "string", // Application-level route ID
    "user_id": "64a1b2c3d4e5f6789abcdef0", // Reference to user who created route
    "title": "Trip to Rome",
    "city": "Rome",
    "city_id": "city_objectid_string",
    "country": "Italy", 
    "country_id": "country_objectid_string",
    "start_date": "2025-06-01",
    "end_date": "2025-06-07",
    "budget": "medium", // low, medium, high - inherited from user preferences
    "travel_style": "moderate", // relaxed, moderate, accelerated
    "category": "city_break", // city_break, beach, mountain, road_trip
    "season": "summer", // spring, summer, autumn, winter
    "stats": {
        "views_count": 0,
        "copies_count": 0, 
        "likes_count": 0
    },
    "must_visit": [
        {
            "place_id": "abc123", // Optional - from places collection
            "place_name": "Colosseum",
            "address": "Piazza del Colosseo, 1, 00184 Roma RM, Italy",
            "coordinates": { "lat": 41.89, "lng": 12.49 },
            "notes": "Morning preferred",
            "source": "google", // google, user, database
            "opening_hours": {
                "monday": "08:30-19:15",
                "tuesday": "08:30-19:15",
                "wednesday": "08:30-19:15", 
                "thursday": "08:30-19:15",
                "friday": "08:30-19:15",
                "saturday": "08:30-19:15",
                "sunday": "08:30-19:15"
            }
        }
    ],
    "days": [
        {
            "date": "2025-06-01",
            "activities": [
                {
                    "place_id": "abc123", // Optional - from places collection
                    "place_name": "Colosseum",
                    "time": "10:00", // 24-hour format
                    "notes": "Visit the ancient amphitheater"
                }
            ]
        }
    ],
    "created_at": "2024-12-01T10:00:00Z",
    "updated_at": "2024-12-01T10:00:00Z"
}
```

### **Places Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier
    "place_id": "abc123", // Unique place identifier (from Google Places API or generated)
    "city": "Rome",
    "city_id": "city_objectid_string", // Reference to cities collection
    "country": "Italy",
    "country_id": "country_objectid_string", // Reference to countries collection  
    "name": "Colosseum",
    "category": "historical_site", // attraction category
    "wayfare_category": "must_see", // Optional - our internal categorization
    "price": "€15-25", // Price range or specific price
    "rating": "4.5", // User rating (string format)
    "popularity": "4.8", // Popularity score (string format)
    "image": "https://example.com/colosseum.jpg", // Optional image URL
    "detail_url": "https://maps.google.com/place/...", // Optional detail URL
    "opening_hours": {
        "monday": "08:30-19:15",
        "tuesday": "08:30-19:15",
        "wednesday": "08:30-19:15",
        "thursday": "08:30-19:15", 
        "friday": "08:30-19:15",
        "saturday": "08:30-19:15",
        "sunday": "08:30-19:15"
    },
    "coordinates": {
        "lat": 41.8902,
        "lng": 12.4922
    },
    "address": "Piazza del Colosseo, 1, 00184 Roma RM, Italy",
    "source": "google", // google, manual, scraping
    "duration": 120, // Recommended visit duration in minutes
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### **Cities Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier
    "name": "Rome",
    "country": "Italy",
    "country_id": "country_objectid_string", // Reference to countries collection
    "active": true, // Whether city is available for route planning
    "coordinates": { // Optional - city center coordinates
        "lat": 41.9028,
        "lng": 12.4964
    },
    "timezone": "Europe/Rome", // Optional timezone information
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}
```

### **Countries Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier
    "name": "Italy",
    "country_id": "IT", // ISO country code identifier
    "region": "Europe", // Geographical region classification
    "active": true, // Whether country is available for route planning
    "created_at": "2025-07-30T16:06:03.201000",
    "updated_at": "2025-07-30T16:06:03.201000"
}
```

### **Place Feedback Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier
    "user_id": "64a1b2c3d4e5f6789abcdef0", // Reference to user who submitted feedback
    "place_id": "ChIJyWEHuEmuEmsRm9hTkapTCrk", // Google Places ID or internal place identifier
    "rating": 5, // Integer from 1-5 rating scale
    "comment": "Amazing place! The view was breathtaking and staff was very friendly.", // Optional user comment (max 1000 characters)
    "visited_on": "2024-12-01", // Date when user visited the place (YYYY-MM-DD format)
    "created_at": "2024-12-01T10:30:00Z", // Timestamp when feedback was submitted
    "updated_at": "2024-12-01T10:30:00Z" // Timestamp when feedback was last modified
}
```

### **Route Feedback Collection**
```json
{
    "_id": ObjectId, // MongoDB auto-generated unique identifier
    "user_id": "64a1b2c3d4e5f6789abcdef0", // Reference to user who submitted feedback
    "route_id": "68877b97cd6e495f565e416c", // Reference to route from routes collection
    "rating": 4, // Integer from 1-5 rating scale
    "comment": "Great route! Well planned with good timing between locations.", // Optional user comment (max 1000 characters)
    "visited_on": "2024-12-01", // Date when user followed the route (YYYY-MM-DD format)
    "created_at": "2024-12-01T14:30:00Z", // Timestamp when feedback was submitted
    "updated_at": "2024-12-01T14:30:00Z" // Timestamp when feedback was last modified
}
```

### **Collection Relationships**

```
Countries (1) ←→ (many) Cities ←→ (many) Places
     ↑                                    ↓
Users (1) ←→ (many) Routes ←→ (many) Must_Visit_Places
  ↓                ↓                      ↓
(many) Place_Feedback + Route_Feedback ←→ Places
```

- **Users** create multiple **Routes** and submit **Feedback**
- **Routes** reference **Cities** and **Countries** 
- **Routes** contain **Must_Visit** places which may reference **Places**
- **Places** belong to **Cities** which belong to **Countries**
- **Place Feedback** links **Users** to **Places** with ratings and comments
- **Route Feedback** links **Users** to **Routes** with ratings and comments
- All collections use MongoDB ObjectIds for relationships

### **Key Features**
- **Flexible Schema**: MongoDB allows for optional fields and schema evolution
- **Geocoding Integration**: Places can be added from external APIs (Google Places)
- **User-Generated Content**: Routes can include custom places not in the places collection
- **Hierarchical Data**: Countries → Cities → Places relationship
- **Feedback System**: Users can rate and review places and routes with validation
- **Duplicate Prevention**: One feedback per user per place/route to maintain data integrity
- **Statistics**: Dynamic calculation of ratings, averages, and distributions
- **Audit Trail**: All collections include created_at and updated_at timestamps

---

**🚀 Ready to start building amazing travel experiences? Check out our [Getting Started Guide](/) and [API Examples](/) for implementation details!** 