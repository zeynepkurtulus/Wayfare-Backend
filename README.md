# WayfareProject - Travel Planning API

A comprehensive travel planning API built with FastAPI that helps users create personalized travel itineraries, manage routes, and share experiences through feedback systems.

## Features

- **User Authentication**: JWT-based authentication with email verification
- **Route Planning**: AI-powered travel route generation with smart scheduling
- **Places Management**: Comprehensive places database with geocoding
- **Cities & Countries**: Location management system
- **Email Verification**: Secure email verification for user registration
- **Feedback System**: User reviews and ratings for places and routes
- **Analytics**: Route statistics and feedback analytics

## Quick Start

### Prerequisites

- Python 3.9+
- MongoDB Atlas account
- Gmail account (for email verification)

### 1. Clone the Repository

```bash
git clone https://github.com/zeynepkurtulus/Wayfare-Backend.git
cd WayfareProject
```

### 2. Set Up Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp env_example.txt .env

# Edit .env with your actual credentials
# See "Environment Setup" section below
```

### 4. Start the Server

```bash
# From the root directory
uvicorn backend.main:app --reload
```

The API will be available at: `http://localhost:8000`

## Environment Setup

### Required Environment Variables

Create a `.env` file in the root directory with the following variables:

#### Database Configuration
```env
MONGO_USERNAME=your_mongodb_username
MONGO_PASSWORD=your_mongodb_password
MONGO_CLUSTER=your_cluster_url
MONGO_DATABASE=Wayfare
```

#### Security Keys
```env
SECRET_KEY=your_jwt_secret_key_here
FORGET_PWD_SECRET_KEY=your_forget_password_key_here
```

#### Email Configuration
```env
GMAIL_USERNAME=your_project_email@gmail.com
GMAIL_APP_PASSWORD=your_16_digit_app_password
GMAIL_FROM=your_project_email@gmail.com
```

#### Application Settings
```env
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

###Email Setup (Gmail)

1. **Enable 2-Step Verification**: Go to [Google Account Security](https://myaccount.google.com/security)
2. **Create App Password**: Visit [App Passwords](https://myaccount.google.com/apppasswords)
3. **Generate Password**: Create password for "WayfareProject"
4. **Update .env**: Add the 16-digit password to `GMAIL_APP_PASSWORD`

##Project Structure

```
WayfareProject/
├── backend/
│   ├── config/
│   │   ├── database.py          # Database connections
│   │   └── email.py             # Email configurations
│   ├── models/
│   │   └── model.py             # Pydantic models
│   ├── routers/
│   │   └── router.py            # API endpoints
│   ├── main.py                  # FastAPI application
│   └── scrapper.py              # Place data scraping
├── requirements.txt             # Python dependencies
├── API_DOCUMENTATION.md         # Complete API documentation
└── README.md                    # This file
```

## API Documentation

### Available Endpoints

- **User Management**: Registration, login, profile management
- **🗺Route Planning**: Create, update, delete travel routes
- **Places**: Search and manage places
- **🏙Cities & Countries**: Location data management
- **Email Verification**: Secure email verification system
- **Feedback**: User reviews and ratings

### Interactive Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

For detailed API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## 🗄️ Database Schema

The project uses MongoDB with the following collections:

- **users**: User accounts and authentication
- **routes**: Travel itineraries and schedules
- **places**: Location data with geocoding
- **cities**: City information with coordinates
- **countries**: Country and region data
- **place_feedback**: User reviews for places
- **route_feedback**: User reviews for routes

## 🔧 Development

### Running Tests

```bash
# Example API test
curl -X POST "http://localhost:8000/user/sendVerification" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com"}'
```

### Adding New Features

1. **Add Models**: Update `backend/models/model.py`
2. **Create Endpoints**: Add to `backend/routers/router.py`
3. **Update Main**: Register routes in `backend/main.py`
4. **Update Docs**: Add to `API_DOCUMENTATION.md`

##  Security Considerations

- **Environment Variables**: Never commit `.env` files
- **API Keys**: Use App Passwords for Gmail, not regular passwords
- **JWT Secrets**: Generate strong, unique secret keys
- **Database**: Use MongoDB Atlas with proper authentication

## 📈 Production Deployment

### Environment-Specific Configurations

- **Development**: Uses `development_config` (emails printed to console)
- **Production**: Uses `gmail_config` (real emails sent)

### Switching Email Modes

Edit `backend/config/email.py`:
```python
# For development (no real emails)
mail_config = development_config

# For production (real emails)
mail_config = gmail_config
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the [API Documentation](API_DOCUMENTATION.md)
2. Review environment setup
3. Ensure all dependencies are installed
4. Verify MongoDB and email configurations

## Version History

- **v1.0.0**: Initial release with core features
  - User authentication and email verification
  - Route planning and management
  - Places and location data
  - Feedback system
  - Comprehensive API documentation 
