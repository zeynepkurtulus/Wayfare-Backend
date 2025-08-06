from models.model import UserRegistration
from typing import List  # Import List from the typing module
from fastapi import APIRouter
from fastapi_mail import MessageSchema, MessageType
import random
from motor.motor_asyncio import AsyncIOMotorCollection
import string
from config.database import user_collection
from bson import ObjectId #this is what mongodb uses to be able to identify the id that it creates itself
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from config.database import database
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from fastapi import Body
import re
import os
from fastapi_mail import ConnectionConfig
import logging
from collections import Counter
import numpy as np
from jose import JWTError, jwt
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse.linalg import svds
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from typing import Dict, List
from scrapper import PlaceScraper 

from typing import Optional



router = APIRouter()
from models.model import(
    ChangePasswordRequest,
    UserInDB,
    UserAddInfo,
    UserInfoResponse,
    DeleteUserRequest,
    RouteCreateInput,
    CityResponse,
    CityCoordinates,
    CitySearchResult,
    CitySearchResponse,
    PlaceSearchResult,
    PlaceSearchResponse,
    CityByCountryRequest,
    GetAllCitiesResponse,
    GetCitiesByCountryResponse,
    GetAllCountiesResponse,
    GetAllCountriesListResponse,
    GetCountriesByRegionRequest,
    GetCountriesByRegionResponse,
    GetCountriesByRegionListResponse,
    SearchCountriesRequest,
    GetAllRegionsResponse,
    GetPlaceByIdResponse,
    GetPlacesByIdsRequest,
    SearchPlacesRequest,
    RouteResponse, RouteListResponse, RouteDetailResponse, RouteCreateResponse, RouteUpdateInput,
    Coordinates, Activity, Day, MustVisit, RouteCreateInput, Route, RouteStats,
    GetPlacesInCityResponse, PlaceInCityResponse, SearchPlacesResponse, SearchPlacesRequest,PlaceCoordinates,
    PlaceModel, AutocompletePlacesRequest,
    # Feedback Models
    SubmitPlaceFeedbackRequest, SubmitRouteFeedbackRequest,
    UpdatePlaceFeedbackRequest, UpdateRouteFeedbackRequest, 
    PlaceFeedbackResponse, RouteFeedbackResponse,
    SubmitFeedbackResponse, GetPlaceFeedbackResponse, GetRouteFeedbackResponse,
    UpdateFeedbackResponse, DeleteFeedbackResponse, FeedbackStatsResponse,
    # Email Verification Models
    SendVerificationRequest, VerifyCodeRequest, VerificationResponse,
    TopRatedPlacesResponse, TopRatedPlaceResponse
)
from config.database import (
    user_collection,
    route_collection,
    cities_collection,
    countries_collection,
    places_collection,
    place_feedback_collection,
    route_feedback_collection
)
from config.email import fastmail
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get security configuration from environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_in_production")
FORGET_PWD_SECRET_KEY = os.getenv("FORGET_PWD_SECRET_KEY", "fallback_forget_pwd_key_change_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
outh2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme = HTTPBearer()
router = APIRouter()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def register_user_endpoint(user_data: UserRegistration):
    # Check if username or email already exists
    existing_user = await user_collection.find_one({
        "$or": [
            {"username": user_data.username},
            {"email": user_data.email}
        ]
    })
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    # Hash the password
    hashed_password = pwd_context.hash(user_data.password)

    # Convert model to dict and apply updates
    user_data_dict = user_data.model_dump()
    user_data_dict["hashed_password"] = hashed_password

    # Normalize names
    user_data_dict["first_name"] = user_data_dict["first_name"].capitalize()
    user_data_dict["last_name"] = user_data_dict["last_name"].capitalize()

    # Remove raw password if present
    user_data_dict.pop("password", None)

    # Set default structure
    user_data_dict["preferences"] = user_data_dict.get("preferences", {
        "interests": [],
        "budget": "medium",
        "travel_style": "relaxed"
    })
    user_data_dict["home_city"] = user_data_dict.get("home_city", "")

    # Insert user data into MongoDB
    user_id = (await user_collection.insert_one(user_data_dict)).inserted_id

    return {
        "message": "User registered successfully",
        "success": True
    }


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_reset_password_token(email: str):
    data = {"sub": email, "exp": datetime.utcnow() + timedelta(minutes=10)}
    token = jwt.encode(data, FORGET_PWD_SECRET_KEY, ALGORITHM)
    return token


async def get_user(username: str, user_collection):
    user = await user_collection.find_one({"username": username})
    if user:
        return UserInDB(**user)
    return None



async def authenticate_user(username: str, password: str, user_collection):
    user = await get_user(username, user_collection)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt



async def add_user_info(user_info: UserAddInfo, token: HTTPAuthorizationCredentials):
    try:
        current_user = await get_current_user(token)

        # Update only the preferences field for the current user
        await user_collection.update_one(
            {"username": current_user.username},
            {"$set": {
                "preferences": user_info.preferences.dict(),
                "home_city": user_info.home_city
                
            }}
        )

        return {"message": "User preferences updated successfully", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> UserInDB:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await user_collection.find_one({"username": username})
        #print("Username from token:", username)
        #print("Matched user:", user)
        if user:
            return UserInDB(**user)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")



async def get_current_user_endpoint(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_current_user(token)


async def get_current_user(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> UserInDB:
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserInfoResponse(
            user_id=str(user.get("_id")),
            email=user.get("email"),
            username=user.get("username"),
            name=user.get("first_name"),
            surname=user.get("last_name"),
            preferences=user.get("preferences"),
            home_city=user.get("home_city")
        )

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    



async def delete_user_account_endpoint(body: DeleteUserRequest, token: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not pwd_context.verify(body.password, user["hashed_password"]):
            raise HTTPException(status_code=403, detail="Incorrect password")

        await user_collection.delete_one({"username": username})
        return {"message": "User deleted successfully", "success": True}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    



async def change_user_password_endpoint(data: ChangePasswordRequest, token: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not pwd_context.verify(data.current_password, user["hashed_password"]):
            raise HTTPException(status_code=403, detail="Current password is incorrect")

        if data.new_password != data.confirm_password:
            raise HTTPException(status_code=400, detail="New passwords do not match")

        new_hashed_password = pwd_context.hash(data.new_password)
        await user_collection.update_one(
            {"username": username},
            {"$set": {"hashed_password": new_hashed_password}}
        )

        return {"message": "Password changed successfully", "success": True}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")



def is_place_open(opening_hours: Dict, visit_time: datetime) -> bool:
    day = visit_time.strftime("%A")
    hours = opening_hours.get(day)
    if not hours or hours.strip() == "" or hours.lower() == "notice":
        return True  # No info: assume always open
    try:
        open_str, close_str = hours.split(" - ")
        open_time = datetime.strptime(open_str, "%I:%M %p").time()
        close_time = datetime.strptime(close_str, "%I:%M %p").time()
        return open_time <= visit_time.time() <= close_time
    except Exception:
        return True  # If parsing fails, assume open


def find_best_visit_time(opening_hours: Dict, current_time: datetime, duration_hours: float) -> Optional[datetime]:
    """Find the best time to visit a place within its opening hours and our 20:30 cutoff"""
    if not opening_hours:
        return current_time
    
    day = current_time.strftime("%A")
    hours = opening_hours.get(day)
    if not hours or hours.strip() == "" or hours.lower() == "notice":
        return current_time
    
    # ENFORCE: Our hard cutoff - activities must finish before 20:30
    cutoff_time = datetime.combine(current_time.date(), datetime.strptime("20:30", "%H:%M").time())
    activity_finish_time = current_time + timedelta(hours=duration_hours)
    
    # If current time would already violate our cutoff, return None
    if activity_finish_time > cutoff_time:
        return None
    
    try:
        open_str, close_str = hours.split(" - ")
        open_time = datetime.strptime(open_str, "%I:%M %p").time()
        close_time = datetime.strptime(close_str, "%I:%M %p").time()
        
        # Convert to datetime for comparison
        open_datetime = datetime.combine(current_time.date(), open_time)
        close_datetime = datetime.combine(current_time.date(), close_time)
        
        # Calculate duration in minutes
        duration_minutes = int(duration_hours * 60)
        
        # Check if we can fit the visit within opening hours AND our cutoff
        if current_time < open_datetime:
            # Place opens later, check if opening time would violate our cutoff
            proposed_finish = open_datetime + timedelta(minutes=duration_minutes)
            if proposed_finish > cutoff_time:
                return None  # Would violate our cutoff
            return open_datetime
        elif current_time + timedelta(minutes=duration_minutes) > close_datetime:
            # Visit would end after closing, try to start earlier
            latest_start = close_datetime - timedelta(minutes=duration_minutes)
            if latest_start >= open_datetime:
                # Check if this adjusted time would violate our cutoff
                proposed_finish = latest_start + timedelta(minutes=duration_minutes)
                if proposed_finish > cutoff_time:
                    return None  # Would violate our cutoff
                return latest_start
            else:
                return None  # Cannot fit visit within opening hours
        else:
            return current_time  # Current time is fine
    except Exception:
        # If parsing fails, still check our cutoff
        if activity_finish_time > cutoff_time:
            return None
        return current_time
    


async def create_route_endpoint(
    route_input: RouteCreateInput,
    token: HTTPAuthorizationCredentials
):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_id = str(user["_id"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    now = datetime.utcnow()
    city = route_input.city
    start_date = datetime.strptime(route_input.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(route_input.end_date, "%Y-%m-%d")
    
    # ENFORCE: Validate that trip is not in the past
    today = datetime.now().date()
    if start_date.date() < today:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create route for past dates. Start date ({route_input.start_date}) is before today ({today.strftime('%Y-%m-%d')})"
        )
    
    # ENFORCE: Validate date range - end_date must be >= start_date
    if end_date < start_date:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid date range: end_date ({route_input.end_date}) cannot be before start_date ({route_input.start_date})"
        )
    
    num_days = (end_date - start_date).days + 1
    
    # ENFORCE: Validate trip duration - reasonable limits
    if num_days <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trip duration: {num_days} days. Trip must be at least 1 day."
        )
    elif num_days > 30:
        raise HTTPException(
            status_code=400,
            detail=f"Trip duration too long: {num_days} days. Maximum allowed is 30 days."
        )
    
        # Get user preferences (use user profile for both travel_style and budget)
    user_preferences = user.get("preferences", {})
    user_interests = user_preferences.get("interests", [])
    user_travel_style = user_preferences.get("travel_style", "relaxed")
    user_budget = user_preferences.get("budget", "medium")

    # Use user profile for both travel_style and budget
    route_budget = user_budget
    
    # Determine places per day based on user's travel style
    places_per_day = {
        "relaxed": 2,
        "moderate": 4,
        "accelerated": 6
    }.get(user_travel_style, 2)
    
    total_places_needed = num_days * places_per_day
    
    # Auto-detect season if not provided
    if not route_input.season:
        month = start_date.month
        if month in [3, 4, 5]:
            season = "spring"
        elif month in [6, 7, 8]:
            season = "summer"
        elif month in [9, 10, 11]:
            season = "autumn"
        else:
            season = "winter"
    else:
        season = route_input.season

    # Get city and country info
    city_info = await cities_collection.find_one({"name": {"$regex": f"^{city}$", "$options": "i"}})
    city_id = str(city_info["_id"]) if city_info else None
    country = city_info.get("country") if city_info else None
    country_id = city_info.get("country_id") if city_info else None

    # Process must_visit places first
    scraper = PlaceScraper()
    updated_must_visit = []
    must_visit_places = []

    for mv in route_input.must_visit:
        must_visit_obj = MustVisit(
            place_id=mv.place_id,
            place_name=mv.place_name,
            notes=mv.notes,
            source=mv.source
        )

        # Enrich with DB info
        print(f"DEBUG: Enriching must-visit place: {mv.place_name}")
        place = await scraper.get_place(city, mv.place_name)
        if place:
            # Handle both Place objects and potential dict returns
            if hasattr(place, 'place_id'):
                must_visit_obj.place_id = place.place_id
                # ENFORCE: Only create coordinates if we have valid lat/lng values
                if place.latitude is not None and place.longitude is not None:
                    must_visit_obj.coordinates = Coordinates(lat=place.latitude, lng=place.longitude)
                    print(f"DEBUG: {mv.place_name} - Enriched with coordinates: ({place.latitude}, {place.longitude})")
                else:
                    print(f"DEBUG: {mv.place_name} - No valid coordinates available, skipping coordinates assignment")
                must_visit_obj.address = place.address
                must_visit_obj.opening_hours = place.opening_hours
                print(f"DEBUG: {mv.place_name} - Enriched via scraper with place_id: {place.place_id}")
            else:
                # Fallback for dict-like objects
                must_visit_obj.place_id = place.get('place_id')
                coords = place.get('coordinates', {})
                if coords and coords.get('lat') is not None and coords.get('lng') is not None:
                    must_visit_obj.coordinates = Coordinates(lat=coords.get('lat'), lng=coords.get('lng'))
                    print(f"DEBUG: {mv.place_name} - Enriched with dict coordinates: ({coords.get('lat')}, {coords.get('lng')})")
                else:
                    print(f"DEBUG: {mv.place_name} - No valid coordinates in dict, skipping coordinates assignment")
                must_visit_obj.address = place.get('address')
                must_visit_obj.opening_hours = place.get('opening_hours')
                print(f"DEBUG: {mv.place_name} - Enriched via scraper (dict) with place_id: {place.get('place_id')}")
        else:
            # Try to find place in places collection using name
            print(f"DEBUG: {mv.place_name} - Scraper failed, trying database lookup...")
            
            # First try exact match
            db_place = await places_collection.find_one({
                "city": {"$regex": f"^{city}$", "$options": "i"},
                "name": {"$regex": f"^{mv.place_name}$", "$options": "i"}
            })
            
            if db_place:
                must_visit_obj.place_id = db_place.get("place_id")
                if db_place.get("coordinates"):
                    must_visit_obj.coordinates = Coordinates(
                        lat=db_place["coordinates"]["lat"], 
                        lng=db_place["coordinates"]["lng"]
                    )
                must_visit_obj.address = db_place.get("address")
                must_visit_obj.opening_hours = db_place.get("opening_hours", {})
                print(f"DEBUG: {mv.place_name} - Found in database with place_id: {db_place.get('place_id')}")
            else:
                print(f"DEBUG: {mv.place_name} - Exact match failed, trying smart partial matching...")
                
                # Try smart partial matching - check if must-visit name is contained in database name
                db_place = await places_collection.find_one({
                    "city": {"$regex": f"^{city}$", "$options": "i"},
                    "name": {"$regex": mv.place_name, "$options": "i"}
                })
                
                if not db_place:
                    # Try reverse matching - check if database name is contained in must-visit name
                    db_place = await places_collection.find_one({
                        "city": {"$regex": f"^{city}$", "$options": "i"},
                        "name": {"$regex": f".*{mv.place_name}.*", "$options": "i"}
                    })
                
                if not db_place:
                    # Try word-by-word matching
                    must_visit_words = mv.place_name.lower().split()
                    print(f"DEBUG: {mv.place_name} - Trying word-by-word matching with words: {must_visit_words}")
                    
                    # Get all places in the city to check manually
                    all_city_places = await places_collection.find({
                        "city": {"$regex": f"^{city}$", "$options": "i"}
                    }).to_list(length=None)
                    
                    best_match = None
                    best_score = 0
                    
                    for place in all_city_places:
                        db_name = place.get("name", "").lower()
                        score = 0
                        
                        # Count how many words from must-visit name are in database name
                        for word in must_visit_words:
                            if word in db_name:
                                score += 1
                        
                        # Also check if database name words are in must-visit name
                        db_words = db_name.split()
                        for word in db_words:
                            if word in mv.place_name.lower():
                                score += 0.5
                        
                        if score > best_score:
                            best_score = score
                            best_match = place
                    
                    if best_match and best_score >= 1:  # At least one word match
                        db_place = best_match
                        print(f"DEBUG: {mv.place_name} - Found via word matching with score {best_score}: {best_match.get('name')}")
                    else:
                        print(f"DEBUG: {mv.place_name} - No word matches found")
                
                if db_place:
                    must_visit_obj.place_id = db_place.get("place_id")
                    if db_place.get("coordinates"):
                        must_visit_obj.coordinates = Coordinates(
                            lat=db_place["coordinates"]["lat"], 
                            lng=db_place["coordinates"]["lng"]
                        )
                    must_visit_obj.address = db_place.get("address")
                    must_visit_obj.opening_hours = db_place.get("opening_hours", {})
                    print(f"DEBUG: {mv.place_name} - Found via smart matching with place_id: {db_place.get('place_id')}")
                    print(f"DEBUG: {mv.place_name} - Matched to database name: {db_place.get('name')}")
                else:
                    must_visit_obj.opening_hours = {}
                    must_visit_obj.coordinates = None
                    must_visit_obj.address = None
                    if not must_visit_obj.place_id:
                        must_visit_obj.place_id = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                    print(f"DEBUG: {mv.place_name} - Not found anywhere, using random place_id: {must_visit_obj.place_id}")
        
        updated_must_visit.append(must_visit_obj)
        must_visit_places.append(must_visit_obj)

    # Find additional places based on user interests and budget
    additional_places_needed = total_places_needed - len(must_visit_places)
    additional_places = []
    
    if additional_places_needed > 0:
        # ENHANCED: Try multiple city name variations for better database matching
        city_variations = [
            city,
            city.replace(" ", ""),  # "New York" -> "NewYork"
            city.split()[0] if " " in city else city,  # "New York" -> "New"
            city.split()[-1] if " " in city else city,  # "New York" -> "York"
        ]
        
        # ENHANCED: Calculate minimum places needed for all days
        min_places_needed = num_days * 2  # At least 2 places per day
        target_places = max(min_places_needed, total_places_needed)
        print(f"DEBUG: Need at least {min_places_needed} places ({target_places} target) for {num_days} days")
        
        all_places = []
        
        # First try exact city matches
        for city_var in city_variations:
            places = await places_collection.find({
                "city": {"$regex": f"^{city_var}$", "$options": "i"}
            }).sort([
                ("rating", -1),  # Higher rated places first
                ("popularity", 1)  # Then by popularity (lower is better)
            ]).to_list(length=None)
            
            if places:
                all_places.extend(places)
                print(f"DEBUG: Found {len(places)} places using exact match for: '{city_var}'")
        
        # If we don't have enough places, try broader search
        if len(all_places) < min_places_needed:
            print(f"DEBUG: Only found {len(all_places)} places, need {min_places_needed}. Trying broader search...")
            for city_var in city_variations:
                places = await places_collection.find({
                    "city": {"$regex": city_var, "$options": "i"}
                }).sort([
                    ("rating", -1),
                    ("popularity", 1)
                ]).limit(100).to_list(length=None)  # Limit to avoid irrelevant results
                
                if places:
                    # Add only new places
                    existing_ids = {p.get("place_id") for p in all_places}
                    new_places = [p for p in places if p.get("place_id") not in existing_ids]
                    all_places.extend(new_places)
                    print(f"DEBUG: Added {len(new_places)} new places from broader search for: '{city_var}'")
                    
                    if len(all_places) >= target_places:
                        break
        
        # If still not enough places, try country-based search
        if len(all_places) < min_places_needed:
            print(f"DEBUG: Still only have {len(all_places)} places, trying country search...")
            
            # Get country from city info
            country_name = country if country else None
            if not country_name:
                # Try to get country from existing places
                for place in all_places:
                    if place.get("country"):
                        country_name = place["country"]
                        break
            
            if country_name:
                places = await places_collection.find({
                    "country": {"$regex": country_name, "$options": "i"}
                }).sort([
                    ("rating", -1),
                    ("popularity", 1)
                ]).limit(100).to_list(length=None)
                
                if places:
                    # Add only new places
                    existing_ids = {p.get("place_id") for p in all_places}
                    new_places = [p for p in places if p.get("place_id") not in existing_ids]
                    all_places.extend(new_places)
                    print(f"DEBUG: Added {len(new_places)} new places from country: {country_name}")
            
            # If still not enough, try common countries
            if len(all_places) < min_places_needed:
                country_queries = ["United States", "USA", "UK", "United Kingdom", "France", "Germany", "Spain", "Italy", "Japan"]
                for country in country_queries:
                    places = await places_collection.find({
                        "country": {"$regex": country, "$options": "i"}
                    }).sort([
                        ("rating", -1),
                        ("popularity", 1)
                    ]).limit(50).to_list(length=None)
                    
                    if places:
                        # Add only new places
                        existing_ids = {p.get("place_id") for p in all_places}
                        new_places = [p for p in places if p.get("place_id") not in existing_ids]
                        all_places.extend(new_places)
                        print(f"DEBUG: Added {len(new_places)} new places from country: {country}")
                        
                        if len(all_places) >= min_places_needed:
                            break
        
        # Filter places based on user interests and budget
        filtered_places = []
        category_counts = {}  # Track category distribution for diversity
        
        for place in all_places:
            # Skip if already in must_visit (fuzzy matching)
            place_name = place.get("name", "")
            skip_place = False
            
            for mv in must_visit_places:
                if is_place_name_similar(mv.place_name, place_name):
                    print(f"DEBUG: Skipping {place_name} - similar to must_visit: {mv.place_name}")
                    skip_place = True
                    break
            
            if skip_place:
                continue
                
            # Check if place matches user interests
            place_category = place.get("category", "").lower()
            wayfare_category = place.get("wayfare_category", "").lower()
            place_name_lower = place.get("name", "").lower()
            
            interest_match = False
            if user_interests and len(user_interests) > 0:
                # User has interests - check for matches
                for interest in user_interests:
                    interest_lower = interest.lower()
                    # Check against both category and wayfare_category
                    if (interest_lower in place_category or 
                        interest_lower in wayfare_category or
                        interest_lower in place_name_lower or 
                        place_category in interest_lower or
                        wayfare_category in interest_lower or
                        place_name_lower in interest_lower):
                        interest_match = True
                        break
            else:
                # User has no interests - include all places but ensure diversity
                interest_match = True
            
            if not interest_match:
                continue
            
            # Check budget compatibility
            price_str = place.get("price", "")
            if price_str:
                price_value = parse_price(price_str)
                if route_budget == "low" and price_value >= 20:
                    continue
                elif route_budget == "medium" and price_value >= 50:
                    continue
                # For 'high', include all places
            
            # ENHANCED: Filter out poor quality/inappropriate places
            place_name_check = place_name.lower()
            skip_low_quality = False
            
            # Skip places that seem like services rather than attractions
            low_quality_indicators = [
                'taxi', 'transfer', 'transport', 'car hire', 'rental',
                'hotel booking', 'room booking', 'accommodation',
                'ultimate party', 'party service', 'event planning',
                'delivery', 'courier', 'shipping', 'logistics'
            ]
            
            for indicator in low_quality_indicators:
                if indicator in place_name_check or indicator in wayfare_category.lower():
                    print(f"DEBUG: Skipping {place_name} - appears to be service/transport rather than attraction")
                    skip_low_quality = True
                    break
            
            if skip_low_quality:
                continue
            
            # ENHANCED: Enforce category diversity to prevent overloading
            category_key = wayfare_category if wayfare_category else place_category
            if category_key:
                category_counts[category_key] = category_counts.get(category_key, 0)
                
                # ADAPTIVE: Adjust category limits based on trip length and travel style
                if user_travel_style == "relaxed":
                    # Relaxed travelers want variety, so be more permissive
                    base_limit = 4 if num_days <= 3 else 6
                elif user_travel_style == "moderate":
                    base_limit = 3 if num_days <= 5 else 5
                else:  # accelerated
                    base_limit = 2 if num_days <= 3 else 4
                
                max_per_category = base_limit
                
                # EXCEPTION: For short trips, be more lenient to ensure we have enough places
                if num_days <= 3 and len(filtered_places) < (num_days * 2):
                    max_per_category = max_per_category + 2  # Allow more variety for short trips
                
                if category_counts[category_key] >= max_per_category:
                    print(f"DEBUG: Skipping {place_name} - category '{category_key}' limit reached ({max_per_category})")
                    continue
                
                category_counts[category_key] += 1
            
            filtered_places.append(place)
        
        # ENHANCED: Ensure we have enough places for all days
        available_places_count = len(filtered_places)
        min_places_for_all_days = num_days * 2  # At least 2 places per day for variety
        min_absolute = num_days * 1  # Absolute minimum 1 place per day
        
        # CRITICAL: Always ensure we have at least num_days places
        if available_places_count < min_absolute:
            print(f"CRITICAL: Only {available_places_count} places for {num_days} days - will cause empty days!")
        
        if additional_places_needed > available_places_count:
            # Need to reuse places to fill all days
            if available_places_count > 0:
                cycles_needed = (additional_places_needed // available_places_count) + 1
                extended_places = (filtered_places * cycles_needed)[:additional_places_needed]
                additional_places = extended_places
                print(f"DEBUG: Trip ({num_days} days) - cycling {available_places_count} places {cycles_needed} times to get {additional_places_needed} places")
            else:
                additional_places = []
                print(f"DEBUG: No places available after filtering for {num_days}-day trip")
        elif available_places_count >= min_places_for_all_days:
            # We have enough places - distribute them intelligently
            if user_travel_style == "relaxed":
                # For relaxed, prefer fewer high-quality places
                additional_places = filtered_places[:min(additional_places_needed, available_places_count)]
            else:
                # For other styles, take as requested
                additional_places = filtered_places[:additional_places_needed]
        else:
            # Take all available places
            additional_places = filtered_places
            print(f"DEBUG: Taking all {len(additional_places)} available places for {num_days}-day trip")
        
            print(f"DEBUG: Found {len(filtered_places)} places after filtering")
    
    # CRITICAL: Ensure we select enough places for all days 
    min_additional_needed = max(num_days * 2, 6)  # At least 2 per day, minimum 6 total
    min_absolute_needed = num_days  # Absolute minimum 1 per day
    
    if len(additional_places) < min_absolute_needed:
        print(f"CRITICAL FIX: Only {len(additional_places)} places for {num_days} days!")
        # Force duplication if needed to prevent empty days
        if len(additional_places) > 0:
            while len(additional_places) < min_absolute_needed:
                additional_places.append(additional_places[0])  # Duplicate the best place
            print(f"DEBUG: CRITICAL DUPLICATION - Expanded to {len(additional_places)} places to prevent empty days")
    
    elif len(additional_places) < min_additional_needed and len(filtered_places) > len(additional_places):
        # Take more places from filtered_places to ensure we have enough
        remaining_places = [p for p in filtered_places if p not in additional_places]
        additional_needed = min_additional_needed - len(additional_places)
        additional_places.extend(remaining_places[:additional_needed])
        print(f"DEBUG: Expanded additional_places from {len(additional_places) - additional_needed} to {len(additional_places)} to cover all days")
    
    print(f"DEBUG: Selected {len(additional_places)} additional places for {num_days}-day trip")
        #print(f"DEBUG: First few places by popularity:")
        #for i, place in enumerate(additional_places[:5]):
        #    print(f"  {i+1}. {place.get('name')} - Popularity: {place.get('popularity')}")

    # 🎯 COMBINE MUST-VISIT PLACES WITH ADDITIONAL PLACES
    # User's must-visit places get priority, then fill with additional places
    all_places_for_route = must_visit_places + additional_places
    #print(f"DEBUG: Combined {len(must_visit_places)} must-visit places with {len(additional_places)} additional places")
    
    # 🎯 DISTRIBUTE MUST-VISIT PLACES ACROSS DAYS FIRST
    # Ensure must-visit places are distributed evenly across all days
    distributed_places = []
    
    if len(must_visit_places) > 0:
        # Distribute must-visit places across days
        must_visit_per_day = max(1, len(must_visit_places) // num_days)
        remaining_must_visit = len(must_visit_places) % num_days
        
        must_visit_index = 0
        for day in range(num_days):
            day_places = []
            
            # Add must-visit places for this day
            places_for_this_day = must_visit_per_day
            if remaining_must_visit > 0:
                places_for_this_day += 1
                remaining_must_visit -= 1
            
            for _ in range(places_for_this_day):
                if must_visit_index < len(must_visit_places):
                    day_places.append(must_visit_places[must_visit_index])
                    must_visit_index += 1
            
            # Add additional places to fill remaining slots
            additional_needed = places_per_day - len(day_places)
            if additional_needed > 0 and additional_places:
                # Take additional places for this day
                start_idx = day * additional_needed
                end_idx = start_idx + additional_needed
                day_additional = additional_places[start_idx:end_idx]
                day_places.extend(day_additional)
            
            if day_places:
                distributed_places.append(day_places)
            else:
                distributed_places.append([])
    else:
        # No must-visit places - use original grouping logic
        if user_interests and len(user_interests) > 0:
            # User has interests - group by proximity for optimal daily routes
            distributed_places = group_places_by_proximity(all_places_for_route, places_per_day)
        else:
            # User has no interests - prioritize popularity (most popular places in earlier days)
            distributed_places = group_places_by_popularity(all_places_for_route, places_per_day, num_days)
    
    # Distribute grouped places across days
    days = []
    
    # Initialize travel counter for the entire trip
    travel_counter = 1
    
    for day_offset in range(num_days):
        day_date = start_date + timedelta(days=day_offset)
        day_str = day_date.strftime("%Y-%m-%d")
        
        # Get places for this day
        if day_offset < len(distributed_places):
            day_places = distributed_places[day_offset]
        else:
            day_places = []
            print(f"WARNING: Day {day_offset + 1} ({day_str}) has no distributed places - distributed_places length: {len(distributed_places)}")
        
        print(f"DEBUG: Day {day_offset + 1} ({day_str}) - {len(day_places)} places assigned")
        
        # Create smart schedule for this day (pass travel_counter by reference)
        scheduled_activities, travel_counter = await create_smart_schedule(day_places, day_date, user_travel_style, city, travel_counter)
        
        # Validate and fix the schedule to ensure realistic timing
        # FIXED: Use direct schedule from create_smart_schedule since our constraints work perfectly
        # validate_and_fix_schedule was adding unwanted travel activities past 20:30
        validated_activities = scheduled_activities
        
        days.append(Day(date=day_str, activities=validated_activities))

    # Build and save the Route object
    route = Route(
        route_id=None,  # Will be set after insertion
        user_id=user_id,
        title=route_input.title,
        city=route_input.city,
        city_id=city_id,
        country=country,
        country_id=country_id,
        start_date=route_input.start_date,
        end_date=route_input.end_date,
        budget=user_budget,
        travel_style=user_travel_style,
        category=route_input.category,
        season=season,
        stats=RouteStats(),
        must_visit=updated_must_visit,
        days=days,
        created_at=now,
        updated_at=now
    )
    route_dict = route.model_dump()

    result = await route_collection.insert_one(route_dict)
    route_id = str(result.inserted_id)
    
    # 🎯 ADD route_id TO THE DATABASE DOCUMENT
    await route_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"route_id": route_id}}
    )

    return RouteCreateResponse(
        message="Route created successfully",
        success=True,
        route_id=route_id,
        status_code=200
    )



async def get_cities_endpoint():
    cities = await cities_collection.find().to_list(length=None)
    result = []
    for city in cities:
        city["city_id"] = str(city["_id"])  # or use city.get("city_id") if you have it
        city.pop("_id", None)  # Remove the raw ObjectId
        result.append(CityResponse(**city))
    
    return GetAllCitiesResponse(
        success=True,
        message="Cities retrieved successfully",
        status_code=200,
        data=result
    )



async def get_city_by_name_endpoint(city_name: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    city = await cities_collection.find_one({"name": city_name})
    if city:
        city["city_id"] = str(city["_id"])
        city.pop("_id", None)
        return CityResponse(**city)
    return None



async def get_cities_by_country_endpoint(country: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    cities = await cities_collection.find({"country": country}).to_list(length=None)
    if not cities:
        raise HTTPException(status_code=404, detail=f"No cities found for country: {country}")
    result = []
    for city in cities:
        city["city_id"] = str(city["_id"])
        city.pop("_id", None)
        result.append(CityResponse(**city))
    
    return GetCitiesByCountryResponse(
        success=True,
        message=f"Cities in {country} retrieved successfully",
        status_code=200,
        data=result
    )


async def get_all_countries_endpoint(token: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return GetAllCountriesListResponse(
                success=False,
                message="Invalid credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
                data=[]
            )
    except JWTError:
        return GetAllCountriesListResponse(
            success=False,
            message="Invalid token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            data=[]
        )
    try:
        countries = await countries_collection.find().to_list(length=None)
        result = []
        for country in countries:
            country["_id"] = str(country["_id"])
            result.append(GetAllCountiesResponse(**country))
        return GetAllCountriesListResponse(
            success=True,
            message="Countries fetched successfully",
            status_code=200,
            data=result
        )
    except Exception as e:
        return GetAllCountriesListResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data=[]
        )



async def get_countries_by_region_endpoint(
    request: GetCountriesByRegionRequest,
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return GetCountriesByRegionListResponse(
                success=False,
                message="Invalid credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
                data=[]
            )
    except JWTError:
        return GetCountriesByRegionListResponse(
            success=False,
            message="Invalid token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            data=[]
        )
    try:
        countries = await countries_collection.find({"region": {"$regex": f"^{request.region}$", "$options": "i"}}).to_list(length=None)
        result = []
        for country in countries:
            country["_id"] = str(country["_id"])
            result.append(GetCountriesByRegionResponse(**country))
        if not result:
            return GetCountriesByRegionListResponse(
                success=True,
                message="No countries found in the specified region.",
                status_code=200,
                data=[]
            )
        return GetCountriesByRegionListResponse(
            success=True,
            message="Countries in region fetched successfully",
            status_code=200,
            data=result
        )
    except Exception as e:
        return GetCountriesByRegionListResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data=[]
        )


async def search_countries_endpoint(
    request: SearchCountriesRequest,
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return GetCountriesByRegionListResponse(
                success=False,
                message="Invalid credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
                data=[]
            )
    except JWTError:
        return GetCountriesByRegionListResponse(
            success=False,
            message="Invalid token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            data=[]
        )
    try:
        # Build a case-insensitive regex for each name
        name_regexes = [{"name": {"$regex": f"^{name}$", "$options": "i"}} for name in request.names]
        countries = await countries_collection.find({"$or": name_regexes}).to_list(length=None)
        result = []
        for country in countries:
            country["_id"] = str(country["_id"])
            result.append(GetCountriesByRegionResponse(**country))
        if not result:
            return GetCountriesByRegionListResponse(
                success=True,
                message="No countries found matching the search.",
                status_code=200,
                data=[]
            )
        return GetCountriesByRegionListResponse(
            success=True,
            message="Countries matching search fetched successfully",
            status_code=200,
            data=result
        )
    except Exception as e:
        return GetCountriesByRegionListResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            data=[]
        )



async def get_all_regions_endpoint(token: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return GetAllRegionsResponse(
                success=False,
                message="Invalid credentials",
                status_code=status.HTTP_401_UNAUTHORIZED,
                data=[]
            )
    except JWTError:
        return GetAllRegionsResponse(
            success=False,
            message="Invalid token",
            status_code=status.HTTP_401_UNAUTHORIZED,
            data=[]
        )
    
    try:
        regions = await countries_collection.distinct("region")
        return GetAllRegionsResponse(
            success=True,
            message="Regions fetched successfully",
            status_code=200,
            data=regions
        )
    except Exception as e:
        return GetAllRegionsResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=500,
            data=[]
        )


async def get_places_in_city_endpoint(
    city: str,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    try:
        # User authentication
        try:
            payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return GetPlacesInCityResponse(
                    success=False,
                    message="Invalid credentials",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    datas=[]
                )
        except JWTError:
            return GetPlacesInCityResponse(
                success=False,
                message="Invalid token",
                status_code=status.HTTP_401_UNAUTHORIZED,
                datas=[]
            )

        # Case-insensitive city search
        places = await places_collection.find({"city": {"$regex": f"^{city}$", "$options": "i"}}).to_list(length=None)
        result = []
        for place in places:
            place["_id"] = str(place["_id"])
            if "coordinates" in place and place["coordinates"]:
                coords = place["coordinates"]
                if isinstance(coords, dict):
                    lat = coords.get("lat")
                    lng = coords.get("lng")
                    coords["lat"] = float(lat) if lat is not None else 0.0
                    coords["lng"] = float(lng) if lng is not None else 0.0
                    place["coordinates"] = coords
            result.append(PlaceInCityResponse(**place))
        if not result:
            return GetPlacesInCityResponse(
                success=True,
                message="No places found in the specified city.",
                status_code=200,
                datas=[]
            )
        return GetPlacesInCityResponse(
            success=True,
            message="Places retrieved successfully",
            status_code=200,
            datas=result
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=GetPlacesInCityResponse(
                success=False,
                message=f"Error: {str(e)}",
                status_code=500,
                datas=[]
            ).dict()
        )



async def get_place_by_id_endpoint(
        request: GetPlacesByIdsRequest, 
        token: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    try:
        # User authentication
        try:
            payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return GetPlacesInCityResponse(
                    success=False,
                    message="Invalid credentials",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    datas=[]
                )
        except JWTError:
            return GetPlacesInCityResponse(
                success=False,
                message="Invalid token",
                status_code=status.HTTP_401_UNAUTHORIZED,
                datas=[]
            )

        # request.place_ids is expected to be a list of place IDs
        places = await places_collection.find({"place_id": {"$in": request.place_ids}}).to_list(length=None)
        result = []
        for place in places:
            place["_id"] = str(place["_id"])
            if "coordinates" in place and place["coordinates"]:
                coords = place["coordinates"]
                if isinstance(coords, dict):
                    lat = coords.get("lat")
                    lng = coords.get("lng")
                    coords["lat"] = float(lat) if lat is not None else 0.0
                    coords["lng"] = float(lng) if lng is not None else 0.0
                    place["coordinates"] = coords
            result.append(PlaceInCityResponse(**place))
        if not result:
            return GetPlaceByIdResponse(
                success=False,
                message="No places found for the given IDs.",
                status_code=404,
                data=None
            )
        # If only one place was requested, return a single object, else a list
        if len(result) == 1:
            data = result[0]
        else:
            data = result
        return GetPlaceByIdResponse(
            success=True,
            message="Place(s) retrieved successfully",
            status_code=200,
            data=data
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=GetPlacesInCityResponse(
                success=False,
                message=f"Error: {str(e)}",
                status_code=500,
                datas=[]
            ).dict()
        )
    




def parse_price(price_str):
    if not price_str or price_str.strip() == "":
        return 0.0  # Free
    # Extract the first number in the string (handles "24£", "€29.90", etc.)
    match = re.search(r"\d+(\.\d+)?", price_str.replace(",", "."))
    if match:
        return float(match.group())
    return float('inf')  # If no number found, treat as very expensive


def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two coordinates using Haversine formula"""
    from math import radians, cos, sin, asin, sqrt
    
    # Validate coordinates
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return float('inf')  # Return infinite distance if coordinates are missing
    
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def group_places_by_proximity(places, places_per_day):
    """Group places by proximity to optimize daily routes"""
    if not places:
        return []
    
    # Convert places to list if needed
    places_list = list(places)
    
    # If we have coordinates, group by proximity
    places_with_coords = []
    places_without_coords = []
    
    for place in places_list:
        if hasattr(place, 'coordinates') and place.coordinates:
            places_with_coords.append(place)
        else:
            places_without_coords.append(place)
    
    # Group places with coordinates by proximity
    grouped_places = []
    used_indices = set()
    
    for i, place1 in enumerate(places_with_coords):
        if i in used_indices:
            continue
            
        group = [place1]
        used_indices.add(i)
        
        # Find nearby places
        for j, place2 in enumerate(places_with_coords):
            if j in used_indices:
                continue
                
            if (place1.coordinates and place2.coordinates):
                distance = calculate_distance(
                    place1.coordinates.lat, place1.coordinates.lng,
                    place2.coordinates.lat, place2.coordinates.lng
                )
                
                # If within 2km, group together
                if distance <= 2.0 and len(group) < places_per_day:
                    group.append(place2)
                    used_indices.add(j)
        
        grouped_places.append(group)
    
    # Add remaining places without coordinates
    for place in places_without_coords:
        if grouped_places and len(grouped_places[-1]) < places_per_day:
            grouped_places[-1].append(place)
        else:
            grouped_places.append([place])
    
    return grouped_places


def group_places_by_popularity(places, places_per_day, num_days):
    """Group places by popularity with proximity optimization - most popular places in earlier days"""
    if not places:
        # ENHANCED: Even with no places, create empty days structure for long trips
        return [[] for _ in range(num_days)]
    
    # Convert places to list if needed
    places_list = list(places)
    
    # Separate must_visit places (they have priority) and additional places
    must_visit_places = []
    additional_places = []
    
    for place in places_list:
        if hasattr(place, 'place_name'):  # Must visit place
            must_visit_places.append(place)
        else:  # Additional place from DB
            additional_places.append(place)
    
    # Sort additional places by popularity (ascending - most popular first)
    def get_popularity_value(place):
        try:
            return float(place.get("popularity", "999999"))
        except (ValueError, TypeError):
            return 999999  # Default to least popular if parsing fails
    
    additional_places.sort(key=get_popularity_value)
    
    print(f"DEBUG: Distribution - {len(must_visit_places)} must-visit, {len(additional_places)} additional places for {num_days} days")
    for i, place in enumerate(additional_places[:5]):
        print(f"  {i+1}. {place.get('name')} - Popularity: {place.get('popularity')}")
    
    # CRITICAL: Ensure we have enough places to fill all days
    if len(additional_places) < num_days and additional_places:
        # Duplicate best places to ensure each day gets something
        while len(additional_places) < num_days:
            additional_places.append(additional_places[0])  # Reuse the best place
        print(f"DEBUG: Duplicated places to ensure {num_days} days coverage")
    
    # ENHANCED: Ensure we have enough places for all days
    if len(additional_places) > 0:
        # Calculate minimum places needed (at least 2 per day for variety)
        min_places_needed = num_days * 2  # Minimum 2 places per day
        target_places = max(min_places_needed, num_days * places_per_day)
        
        # Sort places by rating and popularity
        def get_combined_score(place):
            rating = float(place.get("rating", 0) or 0)
            popularity = float(place.get("popularity", 999999))
            # Normalize popularity (lower is better)
            popularity_score = 1 - (popularity / 1000000)
            return (rating * 0.7) + (popularity_score * 0.3)  # Weight rating more
        
        sorted_places = sorted(additional_places, key=get_combined_score, reverse=True)
        
        # Create initial pool with best places for each day
        extended_additional = []
        places_per_day_min = max(2, places_per_day // 2)  # At least 2 places per day
        
        # First, ensure each day gets at least one high-quality place
        for day in range(num_days):
            if day < len(sorted_places):
                extended_additional.append(sorted_places[day])
        
        # Then add more high-rated places to meet minimum
        remaining_top = sorted_places[num_days:min_places_needed]
        extended_additional.extend(remaining_top)
        
        # Finally, cycle through remaining places for variety
        remaining_places = sorted_places[min_places_needed:]
        
        # CRITICAL FIX: Prevent ZeroDivisionError when no remaining places
        if len(remaining_places) > 0:
            cycles_needed = max(1, (target_places - len(extended_additional)) // len(remaining_places) + 1)
            
            for cycle in range(cycles_needed):
                if cycle % 2 == 0:
                    extended_additional.extend(remaining_places)
                else:
                    extended_additional.extend(reversed(remaining_places))
        else:
            print(f"DEBUG: No remaining places to cycle - using existing {len(extended_additional)} places")
            # FALLBACK: If we still don't have enough places, duplicate the best ones
            if len(extended_additional) < num_days:
                shortfall = num_days - len(extended_additional)
                if len(sorted_places) > 0:
                    # Duplicate the best places to meet minimum requirement
                    for i in range(shortfall):
                        best_place = sorted_places[i % len(sorted_places)]
                        extended_additional.append(best_place)
                    print(f"DEBUG: CRITICAL FALLBACK - Duplicated {shortfall} best places to prevent empty days")
        
        additional_places = extended_additional
        print(f"DEBUG: Distribution strategy - {len(extended_additional)} places ({num_days} guaranteed + {len(remaining_top) if 'remaining_top' in locals() else 0} extra top + cycling)")
    
    # Distribute places across days with proximity optimization
    grouped_places = []
    used_places = set()
    
    for day in range(num_days):
        day_places = []
        
        # First, add must_visit places if any remain
        while len(day_places) < places_per_day and must_visit_places:
            day_places.append(must_visit_places.pop(0))
        
        # ENHANCED: For relaxed style, ensure at least 1 place per day minimum
        min_places_this_day = 1  # ALWAYS ensure at least 1 place per day
        target_places_this_day = max(min_places_this_day, places_per_day)
        
        # Then, add additional places with proximity optimization
        attempts = 0
        max_attempts = len(additional_places) * 2  # Prevent infinite loops
        
        while len(day_places) < target_places_this_day and attempts < max_attempts:
            attempts += 1
            best_place = None
            best_score = float('inf')
            
            # Find the best place to add (considering popularity and proximity)
            for i, place in enumerate(additional_places):
                if i in used_places:
                    continue
                
                # Calculate popularity score (lower is better)
                popularity_score = get_popularity_value(place)
                
                # Calculate proximity score (distance to existing places in this day)
                proximity_score = 0
                if day_places:
                    min_distance = float('inf')
                    place_coords = place.get("coordinates")
                    
                    for existing_place in day_places:
                        existing_coords = None
                        if hasattr(existing_place, 'coordinates'):
                            existing_coords = existing_place.coordinates
                        elif isinstance(existing_place, dict):
                            existing_coords = existing_place.get("coordinates")
                        
                        if place_coords and existing_coords:
                            # Handle both dictionary and Pydantic model coordinates
                            if isinstance(existing_coords, dict):
                                existing_lat = existing_coords.get("lat", 0)
                                existing_lng = existing_coords.get("lng", 0)
                            else:
                                existing_lat = existing_coords.lat
                                existing_lng = existing_coords.lng
                            
                            distance = calculate_distance(
                                place_coords.get("lat", 0), place_coords.get("lng", 0),
                                existing_lat, existing_lng
                            )
                            min_distance = min(min_distance, distance)
                    
                    if min_distance != float('inf'):
                        proximity_score = min_distance
                    else:
                        proximity_score = 10  # Default distance if no coordinates
                else:
                    proximity_score = 0  # First place in the day
                
                # Combined score: popularity + proximity weight
                # Lower score = better choice
                combined_score = popularity_score + (proximity_score * 0.1)  # Weight proximity less than popularity
                
                if combined_score < best_score:
                    best_score = combined_score
                    best_place = (i, place)
            
            if best_place:
                place_index, place = best_place
                day_places.append(place)
                used_places.add(place_index)
                print(f"DEBUG: Day {day + 1} - Added {place.get('name')} (popularity: {place.get('popularity')}, score: {best_score:.2f})")
            else:
                # ENHANCED: If no unused places available, try to ensure at least one place per day
                if len(day_places) == 0 and additional_places:
                    # For empty days, find the best available place
                    available_places = [p for i, p in enumerate(additional_places) if i not in used_places]
                    if available_places:
                        # Use the best available place (highest rating)
                        def get_place_rating(place):
                            return float(place.get("rating", 0) or 0)
                        
                        best_available = max(available_places, key=get_place_rating)
                        day_places.append(best_available)
                        print(f"DEBUG: Day {day + 1} - Added best available: {best_available.get('name')} (rating: {best_available.get('rating')})")
                    else:
                        # If all places are used, cycle through them
                        place_to_reuse = additional_places[day % len(additional_places)]
                        day_places.append(place_to_reuse)
                        print(f"DEBUG: Day {day + 1} - Reusing {place_to_reuse.get('name')} (all places used)")
                else:
                    break  # Day has at least one place, ok to stop
        
        # CRITICAL ENFORCE: Ensure every day has at least one activity 
        if len(day_places) == 0:
            if additional_places and len(additional_places) > 0:
                # ALWAYS force add a place for empty days
                place_index = day % len(additional_places)
                forced_place = additional_places[place_index]
                day_places.append(forced_place)
                print(f"DEBUG: Day {day + 1} - FORCED to add place: {forced_place.get('name')} (empty day prevention)")
            else:
                print(f"CRITICAL WARNING: Day {day + 1} - No places available to prevent empty day (additional_places: {len(additional_places) if additional_places else 0})")
        
        # ENHANCED: Always add a day structure, even if empty
        grouped_places.append(day_places)
        print(f"DEBUG: Day {day + 1} scheduled with {len(day_places)} places")
    
    # FINAL VALIDATION: Ensure we have exactly num_days entries
    while len(grouped_places) < num_days:
        empty_day_index = len(grouped_places) + 1
        if additional_places:
            # Add a place to the missing day
            forced_place = additional_places[0]  # Use the best available place
            missing_day_places = [forced_place]
            print(f"DEBUG: FINAL FIX - Added missing day {empty_day_index} with place: {forced_place.get('name')}")
        else:
            missing_day_places = []
            print(f"DEBUG: FINAL FIX - Added empty day {empty_day_index} (no places available)")
        grouped_places.append(missing_day_places)
    
    print(f"DEBUG: Final grouped_places has {len(grouped_places)} days for {num_days}-day trip")
    return grouped_places


def is_place_name_similar(name1: str, name2: str) -> bool:
    """Check if two place names are similar (fuzzy matching)"""
    name1_lower = name1.lower().strip()
    name2_lower = name2.lower().strip()
    
    # Exact match
    if name1_lower == name2_lower:
        return True
    
    # One name contains the other
    if name1_lower in name2_lower or name2_lower in name1_lower:
        return True
    
    # Split into words and check for keyword overlap
    words1 = set(name1_lower.split())
    words2 = set(name2_lower.split())
    
    # Remove common words that don't help with matching
    common_words = {'the', 'de', 'la', 'el', 'di', 'da', 'basilica', 'basilica', 'church', 'museum', 'palace', 'tower', 'square', 'plaza', 'park', 'garden'}
    words1 = words1 - common_words
    words2 = words2 - common_words
    
    # Check if there's significant word overlap
    if words1 and words2:
        overlap = words1.intersection(words2)
        if len(overlap) >= min(len(words1), len(words2)) * 0.5:  # At least 50% overlap
            return True
    
    return False


def get_visit_duration(place_type, place_name, travel_style, place_data=None, current_time=None):
    """Get accurate visit duration based on place data and characteristics"""
    place_name_lower = place_name.lower()
    place_type_lower = place_type.lower() if place_type else ""
    
    # Get base duration from place characteristics
    base_duration = get_base_duration_from_characteristics(place_type_lower, place_name_lower, place_data)
    
    # Check if we got the duration from the database (most accurate)
    duration_from_db = False
    if place_data and isinstance(place_data, dict):
        duration_minutes = place_data.get("duration")
        if duration_minutes is not None:
            duration_from_db = True
    
    # ENHANCED: Smart duration adjustment for late-day activities
    if current_time and duration_from_db:
        hour = current_time.hour
        
        # For late afternoon/evening activities, cap overly long durations
        if hour >= 16:  # After 4 PM
            if base_duration > 2.5:  # More than 2.5 hours
                base_duration = min(2.0, base_duration)  # Cap at 2 hours
                print(f"DEBUG: {place_name} - Late-day duration capped to {base_duration} hours (was longer)")
        elif hour >= 14:  # After 2 PM  
            if base_duration > 3.0:  # More than 3 hours
                base_duration = min(2.5, base_duration)  # Cap at 2.5 hours
                print(f"DEBUG: {place_name} - Afternoon duration capped to {base_duration} hours (was longer)")
    
    # CRITICAL: Vatican Museums must always get 6+ hours in relaxed mode
    if travel_style == "relaxed" and "vatican" in place_name_lower:
        base_duration = max(base_duration, 6.0)
        print(f"DEBUG: {place_name} - VATICAN CRITICAL OVERRIDE: Ensured 6+ hours for relaxed style")
    
    # ENHANCED: Always apply travel style adjustment, even for database durations
    # This ensures consistent experience across all places
    if travel_style == "relaxed":
        base_duration *= 1.5  # Take significantly more time for relaxed style
        print(f"DEBUG: {place_name} - Applied relaxed travel style adjustment (×1.5)")
    elif travel_style == "accelerated":
        base_duration *= 0.8  # Rush through
        print(f"DEBUG: {place_name} - Applied accelerated travel style adjustment (×0.8)")
    
    # FINAL VATICAN CHECK: Ensure Vatican never gets less than 6 hours in relaxed mode
    if travel_style == "relaxed" and "vatican" in place_name_lower and base_duration < 6.0:
        base_duration = 6.0
        print(f"DEBUG: {place_name} - FINAL VATICAN OVERRIDE: Set to exactly 6.0 hours")
    
    # Log the source of the duration
    if duration_from_db:
        print(f"DEBUG: {place_name} - Base duration from database, adjusted for travel style")
    
    # ENHANCED: Travel style should also influence duration caps for time management
    if travel_style == "relaxed":
        max_duration = 5.0  # Relaxed can have much longer activities
        # For major museums, allow even longer based on database characteristics
        if "museum" in place_name_lower and place_data:
            # Check if it's a major museum based on database characteristics
            popularity = place_data.get("popularity", 10)  # Lower number = more popular
            price = place_data.get("price", "")
            rating = place_data.get("rating", 0)
            
            try:
                pop_value = float(popularity) if popularity else 10
                rating_value = float(rating) if rating else 0
                price_value = parse_price(price) if price else 0
                
                # Major museum indicators: high popularity (low number), high price, high rating
                is_major_museum = (pop_value <= 3 or price_value > 30 or rating_value >= 4.5)
                
                if is_major_museum:
                    max_duration = 6.0  # Major museums can take a full day for relaxed style
            except (ValueError, TypeError):
                # Fallback: if parsing fails, use moderate cap
                pass
    elif travel_style == "moderate":
        max_duration = 3.5  # Moderate has reasonable caps for regular attractions
        # For major museums in moderate style, allow 4 hours
        if "museum" in place_name_lower and place_data:
            # Check if it's a major museum based on database characteristics
            popularity = place_data.get("popularity", 10)  # Lower number = more popular
            price = place_data.get("price", "")
            rating = place_data.get("rating", 0)
            
            try:
                pop_value = float(popularity) if popularity else 10
                rating_value = float(rating) if rating else 0
                price_value = parse_price(price) if price else 0
                
                # Major museum indicators: high popularity (low number), high price, high rating
                is_major_museum = (pop_value <= 3 or price_value > 30 or rating_value >= 4.5)
                
                if is_major_museum:
                    max_duration = 4.0  # Major museums get 4 hours for moderate style
            except (ValueError, TypeError):
                # Fallback: use regular moderate cap
                pass
    else:  # accelerated
        max_duration = 2.5  # Accelerated prefers shorter activities
    
    # Ensure reasonable bounds (15 minutes to travel-style-specific max)
    return max(0.25, min(max_duration, base_duration))


def get_base_duration_from_characteristics(place_type, place_name, place_data):
    """Get accurate base duration using place characteristics and data"""
    
    # Method 1: Use place data if available (most accurate)
    if place_data and isinstance(place_data, dict):
        return get_duration_from_place_data(place_data, place_name)
    
    # Method 2: Use category and name analysis (fallback)
    return get_duration_from_analysis(place_type, place_name)


def get_duration_from_place_data(place_data, place_name):
    """Extract duration from place data using multiple indicators"""
    place_name_lower = place_name.lower()
    
    # Primary method: Use the duration field if available (most accurate)
    duration_minutes = place_data.get("duration")
    #print(f"DEBUG: {place_name} - Duration field from database: {duration_minutes}")
    if duration_minutes is not None:
        try:
            duration_hours = float(duration_minutes) / 60.0
            
            # ENHANCED: Dynamic handling for major museums based on database characteristics
            if "museum" in place_name_lower or "museums" in place_name_lower:
                # Use database characteristics to determine museum importance
                popularity = place_data.get("popularity", 10)  # Lower number = more popular
                price = place_data.get("price", "")
                rating = place_data.get("rating", 0)
                
                try:
                    pop_value = float(popularity) if popularity else 10
                    rating_value = float(rating) if rating else 0
                    price_value = parse_price(price) if price else 0
                    
                    # World-class museums: extremely popular + expensive + highly rated
                    if pop_value <= 2 and (price_value > 25 or rating_value >= 4.7):
                        duration_hours = max(duration_hours, 6.0)  # World-class museums need a full day
                    # Major museums: very popular or expensive or highly rated
                    elif pop_value <= 3 or price_value > 20 or rating_value >= 4.5:
                        duration_hours = max(duration_hours, 5.0)  # Major museums need significant time
                    # Important museums: popular or moderately priced
                    elif pop_value <= 5 or price_value > 15 or rating_value >= 4.0:
                        duration_hours = max(duration_hours, 4.0)  # Important museums
                except (ValueError, TypeError):
                    # Fallback: use moderate duration if parsing fails
                    duration_hours = max(duration_hours, 3.0)
            
            # ENHANCED: Special handling for religious complexes with multiple attractions
            if any(word in place_name_lower for word in ["vatican", "complex", "basilica", "cathedral"]) and "museum" in place_name_lower:
                duration_hours = max(duration_hours, 6.0)  # Religious complexes with museums need full day
                print(f"DEBUG: {place_name} - RELIGIOUS COMPLEX OVERRIDE: Setting to 6.0 hours")
            
            print(f"DEBUG: {place_name} - Using duration field: {duration_minutes} minutes ({duration_hours:.1f} hours)")
            return duration_hours
        except (ValueError, TypeError):
            print(f"DEBUG: {place_name} - Error converting duration: {duration_minutes}")
            pass
    
    # Fallback method: Use category analysis
    category = place_data.get("category", "").lower()
    wayfare_category = place_data.get("wayfare_category", "").lower()
    print(f"DEBUG: {place_name} - Raw category: '{category}', Wayfare category: '{wayfare_category}'")
    
    # Use wayfare_category if available, otherwise fall back to category
    category_to_use = wayfare_category if wayfare_category else category
    base_duration = get_category_base_duration(category_to_use, place_name_lower)
    
    # Indicator 2: Popularity (more popular = more to see)
    popularity = place_data.get("popularity")
    if popularity:
        try:
            pop_value = float(popularity)
            # Popularity 1-3: Major attractions (longer visits)
            if pop_value <= 3:
                base_duration *= 1.5
            # Popularity 4-6: Medium attractions
            elif pop_value <= 6:
                base_duration *= 1.0
            # Popularity 7-10: Smaller attractions
            else:
                base_duration *= 0.7
        except (ValueError, TypeError):
            pass
    
    # Indicator 3: Price (more expensive = more complex)
    price = place_data.get("price", "")
    if price and price != "":
        try:
            price_value = parse_price(price)
            if price_value > 50:
                base_duration *= 1.3  # Expensive places often take longer
            elif price_value > 20:
                base_duration *= 1.1
        except (ValueError, TypeError):
            pass
    
    # Indicator 4: Rating (higher rating = more to explore)
    rating = place_data.get("rating")
    if rating:
        try:
            rating_value = float(rating)
            if rating_value >= 4.5:
                base_duration *= 1.2  # Highly rated places often have more to offer
        except (ValueError, TypeError):
            pass
    
    # Indicator 5: Specific place name analysis
    base_duration = apply_specific_place_adjustments(base_duration, place_name_lower)
    
    print(f"DEBUG: {place_name} - Final duration: {base_duration} hours")
    return base_duration


def get_category_base_duration(category, place_name):
    """Get base duration based on category analysis without hardcoding place names"""
    
    category_lower = category.lower()
    place_name_lower = place_name.lower()
    
    # Sports & Recreation (1-3 hours)
    if any(word in category_lower for word in ["sports", "recreation", "fitness", "gym", "athletic"]):
        if any(word in category_lower for word in ["stadium", "arena", "major", "professional"]):
            return 3.0  # Major sports venues
        else:
            return 1.5  # Regular sports activities
    
    # Museums & Art Galleries (2-6 hours) - Dynamic duration based on characteristics
    if any(word in category_lower for word in ["museum", "gallery", "art", "exhibition"]):
        # Use semantic analysis instead of hardcoded names
        
        # World-class indicators in name
        if any(word in place_name_lower for word in ["national", "royal", "state", "metropolitan", "major"]):
            return 5.0  # National/Royal museums are typically major
        
        # Large complex indicators
        elif any(word in place_name_lower for word in ["complex", "center", "centre", "palace", "castle"]):
            return 4.5  # Palace/Castle museums are typically large
        
        # Specialized museum indicators
        elif any(word in category_lower for word in ["specialty", "speciality", "modern", "contemporary", "science", "history", "natural"]):
            return 3.0  # Specialized museums
        
        # Size indicators in name
        elif any(word in place_name_lower for word in ["grand", "grande", "great", "main", "principal"]):
            return 3.5  # Museums with size indicators
        
        # Regular museums
        else:
            return 2.5  # Default museum duration
    
    # Religious Sites (1.5-3 hours)
    if any(word in category_lower for word in ["church", "basilica", "cathedral", "temple", "mosque", "synagogue", "religious", "worship"]):
        if any(word in category_lower for word in ["cathedral", "basilica", "major", "historic"]):
            return 2.5  # Major religious sites
        else:
            return 1.5  # Regular religious sites
    
    # Parks & Gardens (1-3 hours)
    if any(word in category_lower for word in ["park", "garden", "botanical", "nature", "outdoor"]):
        if any(word in category_lower for word in ["national", "botanical", "large", "major"]):
            return 3.0  # Large parks
        else:
            return 2.0  # Regular parks
    
    # Historic Sites (1.5-3 hours)
    if any(word in category_lower for word in ["historic", "archaeological", "ruins", "ancient", "heritage", "historical"]):
        if any(word in category_lower for word in ["major", "national", "world heritage", "significant"]):
            return 2.5  # Major historical sites
        else:
            return 1.5  # Regular historical sites
    
    # Entertainment & Cultural Venues (2-3 hours)
    if any(word in category_lower for word in ["theater", "opera", "concert", "performance", "cultural", "entertainment"]):
        return 2.5  # Entertainment venues
    
    # Shopping & Markets (1-2 hours)
    if any(word in category_lower for word in ["market", "shopping", "mall", "bazaar", "retail", "store"]):
        return 1.5  # Shopping areas
    
    # Food & Dining (1-3 hours)
    if any(word in category_lower for word in ["restaurant", "cafe", "bar", "food", "dining", "culinary"]):
        if any(word in category_lower for word in ["fine dining", "luxury", "upscale"]):
            return 2.5  # Fine dining
        else:
            return 1.5  # Regular dining
    
    # Spas & Wellness (1-2 hours)
    if any(word in category_lower for word in ["spa", "wellness", "hammam", "thermal", "massage"]):
        return 1.5  # Spa visits
    
    # Amusement & Entertainment Centers (1-3 hours)
    if any(word in category_lower for word in ["amusement", "entertainment", "arcade", "game", "fun"]):
        if any(word in category_lower for word in ["theme park", "major", "large"]):
            return 3.0  # Major entertainment venues
        else:
            return 1.5  # Regular entertainment centers
    
    # Cooking Classes & Food Experiences (2-3 hours)
    if any(word in category_lower for word in ["cooking", "culinary", "food", "wine", "tasting"]):
        return 2.5  # Food experiences
    
    # Natural Attractions (1-2 hours)
    if any(word in category_lower for word in ["river", "lake", "water", "natural", "scenic", "view"]):
        return 1.5  # Natural attractions
    
    # Monuments & Landmarks (0.5-1.5 hours)
    if any(word in category_lower for word in ["monument", "landmark", "tower", "memorial", "statue"]):
        return 1.0  # Monuments
    
    # Squares & Plazas (0.5-1 hour)
    if any(word in category_lower for word in ["fountain", "square", "plaza", "piazza", "public space"]):
        return 0.5  # Quick visits
    
    # Points of Interest (1-2 hours)
    if any(word in category_lower for word in ["point of interest", "attraction", "sight", "tourist"]):
        return 1.0  # General attractions
    
    # Default for any other category
    return 1.0


def get_duration_from_analysis(place_type, place_name):
    """Fallback method using category and name analysis"""
    return get_category_base_duration(place_type, place_name)


def apply_specific_place_adjustments(base_duration, place_name):
    """Apply adjustments based on place characteristics, not hardcoded names"""
    
    place_name_lower = place_name.lower()
    
    # Quick visit indicators (fountains, squares, small monuments)
    quick_visit_words = ["fountain", "square", "plaza", "piazza", "small", "mini"]
    if any(word in place_name_lower for word in quick_visit_words):
        return min(base_duration, 1.0)  # Cap at 1 hour for quick visits
    
    # Large/complex indicators (major, grand, central, national)
    large_indicators = ["major", "grand", "central", "national", "royal", "imperial"]
    if any(word in place_name_lower for word in large_indicators):
        return max(base_duration, 2.0)  # At least 2 hours for major places
    
    return base_duration





async def calculate_travel_time(place1, place2, city=None):
    """Calculate travel time between two places (in minutes) with coordinate caching"""
    # Get coordinates for both places
    coords1 = None
    coords2 = None
    
    # Debug: Get place names for logging
    place1_name = place1.place_name if hasattr(place1, 'place_name') else place1.get('name', 'Unknown')
    place2_name = place2.place_name if hasattr(place2, 'place_name') else place2.get('name', 'Unknown')
    
    # OPTIMIZATION: Check if coordinates are already cached in place objects to prevent repeated geocoding
    if hasattr(place1, '_cached_coords'):
        coords1 = place1._cached_coords
        print(f"DEBUG: {place1_name} - Using cached coordinates: {coords1}")
    
    if hasattr(place2, '_cached_coords'):
        coords2 = place2._cached_coords  
        print(f"DEBUG: {place2_name} - Using cached coordinates: {coords2}")
    
    # Get coordinates for place1 (only if not cached)
    if not coords1:
        if hasattr(place1, 'coordinates') and place1.coordinates:
            coords1 = (place1.coordinates.lat, place1.coordinates.lng)
            place1._cached_coords = coords1  # Cache for future use
            print(f"DEBUG: {place1_name} - Using coordinates from place object: {coords1}")
        elif isinstance(place1, dict) and place1.get("coordinates"):
            coords_dict = place1["coordinates"]
            if isinstance(coords_dict, dict):
                coords1 = (coords_dict.get("lat", 0), coords_dict.get("lng", 0))
            else:
                coords1 = (coords_dict.lat, coords_dict.lng)
            if isinstance(place1, dict):
                place1['_cached_coords'] = coords1  # Cache for dict objects
            print(f"DEBUG: {place1_name} - Using coordinates from dict: {coords1}")
    
    # Get coordinates for place2 (only if not cached)
    if not coords2:
        if hasattr(place2, 'coordinates') and place2.coordinates:
            coords2 = (place2.coordinates.lat, place2.coordinates.lng)
            place2._cached_coords = coords2  # Cache for future use
            print(f"DEBUG: {place2_name} - Using coordinates from place object: {coords2}")
        elif isinstance(place2, dict) and place2.get("coordinates"):
            coords_dict = place2["coordinates"]
            if isinstance(coords_dict, dict):
                coords2 = (coords_dict.get("lat", 0), coords_dict.get("lng", 0))
            else:
                coords2 = (coords_dict.lat, coords_dict.lng)
            if isinstance(place2, dict):
                place2['_cached_coords'] = coords2  # Cache for dict objects
            print(f"DEBUG: {place2_name} - Using coordinates from dict: {coords2}")
    
    # If coordinates are missing, try to get them via geocoding
    if not coords1 or coords1[0] is None or coords1[1] is None:
        print(f"DEBUG: {place1_name} - No coordinates found, attempting geocoding...")
        if city:
            scraper = PlaceScraper()
            place_data = await scraper.get_place(city, place1_name)
            if place_data and place_data.latitude and place_data.longitude:
                coords1 = (place_data.latitude, place_data.longitude)
                # Cache the geocoded coordinates
                if hasattr(place1, '__dict__'):
                    place1._cached_coords = coords1
                elif isinstance(place1, dict):
                    place1['_cached_coords'] = coords1
                print(f"DEBUG: {place1_name} - Got coordinates via geocoding: {coords1}")
            else:
                print(f"DEBUG: {place1_name} - Geocoding failed, place_data: {place_data}")
                # Try dynamic fallback from database first, then legacy hardcoded
                fallback_coords = await scraper._get_dynamic_fallback_coordinates(place1_name, city)
                if not fallback_coords:
                    # Only use legacy hardcoded fallback if dynamic fails
                    fallback_coords = scraper._get_fallback_coordinates(place1_name)
                    
                if fallback_coords:
                    coords1 = fallback_coords
                    # Cache the fallback coordinates
                    if hasattr(place1, '__dict__'):
                        place1._cached_coords = coords1
                    elif isinstance(place1, dict):
                        place1['_cached_coords'] = coords1
                    print(f"DEBUG: {place1_name} - Using fallback coordinates: {coords1}")
                else:
                    print(f"DEBUG: {place1_name} - No fallback coordinates available")
    
    if not coords2 or coords2[0] is None or coords2[1] is None:
        print(f"DEBUG: {place2_name} - No coordinates found, attempting geocoding...")
        if city:
            scraper = PlaceScraper()
            place_data = await scraper.get_place(city, place2_name)
            if place_data and place_data.latitude and place_data.longitude:
                coords2 = (place_data.latitude, place_data.longitude)
                print(f"DEBUG: {place2_name} - Got coordinates via geocoding: {coords2}")
            else:
                print(f"DEBUG: {place2_name} - Geocoding failed, place_data: {place_data}")
                # Try dynamic fallback from database first, then legacy hardcoded
                fallback_coords = await scraper._get_dynamic_fallback_coordinates(place2_name, city)
                if not fallback_coords:
                    # Only use legacy hardcoded fallback if dynamic fails
                    fallback_coords = scraper._get_fallback_coordinates(place2_name)
                    
                if fallback_coords:
                    coords2 = fallback_coords
                    print(f"DEBUG: {place2_name} - Using fallback coordinates: {coords2}")
                else:
                    print(f"DEBUG: {place2_name} - No fallback coordinates available")
    
    if coords1 and coords2 and coords1[0] is not None and coords1[1] is not None and coords2[0] is not None and coords2[1] is not None:
        # Calculate distance using Haversine formula
        distance = calculate_distance(coords1[0], coords1[1], coords2[0], coords2[1])
        print(f"DEBUG: Distance between {place1_name} and {place2_name}: {distance:.2f} km")
        
        # Enhanced travel time calculation based on distance
        if distance <= 0.5:  # Very close (500m or less)
            # Walking speed: 4 km/h for short distances (includes stops, traffic lights)
            travel_time_minutes = (distance / 4.0) * 60
            speed_used = "4 km/h"
        elif distance <= 2.0:  # Close (2km or less)
            # Walking speed: 5 km/h for medium distances
            travel_time_minutes = (distance / 5.0) * 60
            speed_used = "5 km/h"
        elif distance <= 5.0:  # Medium distance (5km or less)
            # Walking speed: 6 km/h for longer distances
            travel_time_minutes = (distance / 6.0) * 60
            speed_used = "6 km/h"
        else:  # Long distance (over 5km)
            # Consider public transport or taxi
            # Assume 20 km/h average for mixed transport
            travel_time_minutes = (distance / 20.0) * 60
            speed_used = "20 km/h (transport)"
        
        # Add buffer time for city navigation (finding places, traffic lights, etc.)
        buffer_time = min(distance * 2, 10)  # 2 minutes per km, max 10 minutes
        total_time = travel_time_minutes + buffer_time
        
        print(f"DEBUG: Travel calculation - Distance: {distance:.2f}km, Speed: {speed_used}, Base time: {travel_time_minutes:.1f}min, Buffer: {buffer_time:.1f}min, Total: {total_time:.1f}min")
        
        # Cap at reasonable limits
        final_time = min(max(total_time, 5), 45)  # Minimum 5 minutes, maximum 45 minutes
        print(f"DEBUG: Final travel time: {final_time:.1f} minutes")
        return final_time
    else:
        # Default travel time when coordinates are missing or geocoding failed
        # Use a reasonable default based on typical city travel
        default_time = 25  # 25 minutes for unknown distances
        print(f"DEBUG: {place1_name} to {place2_name} - No coordinates available, using default: {default_time} minutes")
        return default_time


async def create_smart_schedule(day_places, day_date, travel_style, city, travel_counter=1):
    """Create smart schedule with realistic timing and breaks"""
    print(f"DEBUG: create_smart_schedule called for {day_date.strftime('%Y-%m-%d')} with {len(day_places)} places")
    
    if not day_places:
        print(f"DEBUG: No places provided for {day_date.strftime('%Y-%m-%d')} - returning empty schedule")
        return [], travel_counter
    
    schedule = []
    current_time = datetime.combine(day_date, datetime.strptime("09:00", "%H:%M").time())
    
    # Ensure we don't start too early (before 08:00)
    if current_time.hour < 8:
        current_time = datetime.combine(day_date, datetime.strptime("08:00", "%H:%M").time())
    
    # Ensure we don't start too late (after 18:00)
    if current_time.hour >= 18:
        current_time = datetime.combine(day_date, datetime.strptime("09:00", "%H:%M").time())
        print(f"DEBUG: Adjusted start time to 09:00 for {day_date.strftime('%Y-%m-%d')}")
    
    # Use travel_counter from parameter (continues across days)
    
    # Track if breaks have been added today
    lunch_added_today = False
    dinner_added_today = False
    
    for i, place in enumerate(day_places):
        # ENFORCE: Pre-check time constraints before processing any place
        cutoff_time = datetime.combine(day_date, datetime.strptime("20:30", "%H:%M").time())
        if current_time > cutoff_time:
            print(f"DEBUG: Time already past 20:30 ({current_time.strftime('%H:%M')}), stopping schedule")
            break
        
        # Add travel time from previous place
        if i > 0:
            travel_time = await calculate_travel_time(day_places[i-1], place, city)
            
            # Debug logging for travel time
            prev_place_name = day_places[i-1].place_name if hasattr(day_places[i-1], 'place_name') else day_places[i-1].get('name')
            current_place_name = place.place_name if hasattr(place, 'place_name') else place.get('name')
            
            # ENHANCED: Use same predictive logic as main activities for consistency
            # Travel time + buffer + potential next activity (conservative 30min estimate)
            travel_end_time = current_time + timedelta(minutes=travel_time)
            conservative_buffer = 30  # Same as main activity logic
            predicted_total_time = travel_end_time + timedelta(minutes=conservative_buffer)
            
            cutoff_time = datetime.combine(day_date, datetime.strptime("20:30", "%H:%M").time())
            
            # ENFORCE: Unified cutoff logic - travel + buffer must not exceed 20:30
            if predicted_total_time > cutoff_time:
                print(f"DEBUG: Skipping travel to {current_place_name} - would extend past 20:30 with buffer ({predicted_total_time.strftime('%H:%M')})")
                break
                
            # ENFORCE: Even stricter - no travel starting after 19:30 (same as activities)
            if current_time.hour >= 19 and current_time.minute >= 30:
                print(f"DEBUG: Skipping travel to {current_place_name} - would start after 19:30 ({current_time.strftime('%H:%M')})")
                break
                
            # ENFORCE: Add travel activity if significant (lowered threshold to show more travel activities)
            if travel_time > 5:
                # ENFORCE: Generate sequential travel ID with 3-digit format
                travel_place_id = f"travel_{travel_counter:03d}"
                travel_counter += 1

                schedule.append(Activity(
                    place_id=travel_place_id,
                    place_name=f"Travel to {place.place_name if hasattr(place, 'place_name') else place.get('name')}",
                    time=current_time.strftime("%H:%M"),
                    notes=f"Travel time: {int(travel_time)} minutes"
                ))

                current_time += timedelta(minutes=travel_time)

        
        # ENHANCED: Add lunch break with travel-style-specific timing and duration
        if 11 <= current_time.hour <= 13 and i > 0 and not lunch_added_today:
            # Relaxed style gets longer lunch breaks
            lunch_duration = timedelta(hours=2 if travel_style == "relaxed" else (1.5 if travel_style == "moderate" else 1))
            lunch_end_time = current_time + lunch_duration
            
            # ENFORCE: Lunch must end before 20:30
            cutoff_time = datetime.combine(current_time.date(), datetime.strptime("20:30", "%H:%M").time())
            if lunch_end_time <= cutoff_time:
                schedule.append(Activity(
                    place_id="break_lunch",
                    place_name="Lunch Break",
                    time=current_time.strftime("%H:%M"),
                    notes="Extended lunch break - enjoy local cuisine" if travel_style == "relaxed" else "Lunch break - enjoy local cuisine"
                ))
                current_time = lunch_end_time
                lunch_added_today = True
        
        # ENHANCED: Add afternoon tea break for relaxed style (14:00-17:00)
        tea_already_added = any(act.place_id == "break_tea" for act in schedule)
        if (travel_style == "relaxed" and 14 <= current_time.hour < 18 and 
            i > 0 and not tea_already_added):
            tea_duration = timedelta(minutes=45)
            tea_end_time = current_time + tea_duration
            cutoff_time = datetime.combine(current_time.date(), datetime.strptime("20:30", "%H:%M").time())
            
            if tea_end_time <= cutoff_time:
                schedule.append(Activity(
                    place_id="break_tea",
                    place_name="Afternoon Tea Break",
                    time=current_time.strftime("%H:%M"),
                    notes="Relaxing afternoon tea break"
                ))
                current_time = tea_end_time
                print(f"DEBUG: Added afternoon tea break at {current_time.strftime('%H:%M')} for relaxed style")
        
        # ENHANCED: Add dinner break with travel-style-specific timing
        # For relaxed style, try to add dinner earlier (16:30-19:00) to ensure it fits
        # For other styles, try normal dinner time (18:00-19:00)
        dinner_window_start = 16 if travel_style == "relaxed" else 18
        dinner_window_end = 19 if travel_style == "relaxed" else 19
        
        if (dinner_window_start <= current_time.hour < dinner_window_end + 1 and 
            not dinner_added_today and 
            i > 0):  # Don't add dinner as first activity
            
            # Longer dinner for relaxed style
            dinner_duration = timedelta(hours=2 if travel_style == "relaxed" else (1.5 if travel_style == "moderate" else 1))
            cutoff_time = datetime.combine(current_time.date(), datetime.strptime("20:30", "%H:%M").time())
            
            # Calculate when dinner would end
            dinner_end_time = current_time + dinner_duration
            
            # Add buffer for potential travel after dinner
            buffer_for_travel = timedelta(minutes=30)
            total_end_time = dinner_end_time + buffer_for_travel
            
            # Only add dinner if it would end with enough buffer before cutoff
            if total_end_time <= cutoff_time:
                schedule.append(Activity(
                    place_id="break_dinner",
                    place_name="Dinner Break", 
                    time=current_time.strftime("%H:%M"),
                    notes="Extended dinner break - enjoy fine dining" if travel_style == "relaxed" else "Dinner break - try local restaurants"
                ))
                current_time = dinner_end_time
                dinner_added_today = True
                print(f"DEBUG: Added dinner break at {current_time.strftime('%H:%M')} (ends {dinner_end_time.strftime('%H:%M')})")
            else:
                print(f"DEBUG: Skipped dinner - would end too late ({dinner_end_time.strftime('%H:%M')}) with travel buffer")
        
        # FALLBACK: If relaxed style and no dinner added yet, try to add at end of day
        if (travel_style == "relaxed" and not dinner_added_today and 
            current_time.hour >= 17 and current_time.hour < 20):
            # Try a shorter dinner if normal one doesn't fit
            short_dinner_duration = timedelta(hours=1)
            short_dinner_end = current_time + short_dinner_duration
            cutoff_time = datetime.combine(current_time.date(), datetime.strptime("20:30", "%H:%M").time())
            
            if short_dinner_end <= cutoff_time:
                schedule.append(Activity(
                    place_id="break_dinner",
                    place_name="Dinner Break",
                    time=current_time.strftime("%H:%M"),
                    notes="Dinner break - enjoy local cuisine"
                ))
                current_time = short_dinner_end
                dinner_added_today = True
                print(f"DEBUG: Added FALLBACK dinner break at {current_time.strftime('%H:%M')} for relaxed style")
        
        # Get place details
        if hasattr(place, 'place_name'):  # Must visit place
            place_name = place.place_name
            place_notes = place.notes if hasattr(place, 'notes') else ""
            place_category = "attraction"  # Default for must-visit places
            
            # Try to get place data from database for must-visit places
            #print(f"DEBUG: Looking for '{place_name}' in city '{city}' in database...")
            
            # First try exact match
            db_place = await places_collection.find_one({
                "city": {"$regex": f"^{city}$", "$options": "i"},
                "name": {"$regex": f"^{place_name}$", "$options": "i"}
            })
            
            # If not found by exact name, try smart partial matching
            if not db_place:
                #print(f"DEBUG: Exact match not found, trying smart partial matching for '{place_name}'...")
                
                # Try if must-visit name is contained in database name
                db_place = await places_collection.find_one({
                    "city": {"$regex": f"^{city}$", "$options": "i"},
                    "name": {"$regex": place_name, "$options": "i"}
                })
                
                if not db_place:
                    # Try reverse matching - if database name is contained in must-visit name
                    db_place = await places_collection.find_one({
                        "city": {"$regex": f"^{city}$", "$options": "i"},
                        "name": {"$regex": f".*{place_name}.*", "$options": "i"}
                    })
                
                if not db_place:
                    # Try word-by-word matching
                    place_words = place_name.lower().split()
                    #print(f"DEBUG: Trying word-by-word matching with words: {place_words}")
                    
                    # Get all places in the city to check manually
                    all_city_places = await places_collection.find({
                        "city": {"$regex": f"^{city}$", "$options": "i"}
                    }).to_list(length=None)
                    
                    best_match = None
                    best_score = 0
                    
                    for place in all_city_places:
                        db_name = place.get("name", "").lower()
                        score = 0
                        
                        # Count how many words from must-visit name are in database name
                        for word in place_words:
                            if word in db_name:
                                score += 1
                        
                        # Also check if database name words are in must-visit name
                        db_words = db_name.split()
                        for word in db_words:
                            if word in place_name.lower():
                                score += 0.5
                        
                        # Bonus for exact word matches
                        if place_name.lower() in db_name or db_name in place_name.lower():
                            score += 2
                        
                        if score > best_score:
                            best_score = score
                            best_match = place
                    
                    if best_match and best_score >= 1:  # At least one word match
                        db_place = best_match
                        #print(f"DEBUG: Found via word matching with score {best_score}: {best_match.get('name')}")
                    #else:
                    #    print(f"DEBUG: No word matches found")
            
            # Use database place_id if found, otherwise use the original place_id
            if db_place:
                place_id = db_place.get("place_id")
                place_data = db_place
                # Update the place object with correct place_id for consistency (only for Pydantic models)
                if hasattr(place, 'place_id'):
                    place.place_id = place_id
                #print(f"DEBUG: {place_name} - Found in database with place_id: {place_id}")
                #print(f"DEBUG: {place_name} - Database duration field: {db_place.get('duration')}")
                #print(f"DEBUG: {place_name} - Database name: {db_place.get('name')}")
            else:
                # Use original place_id if not found in DB (handle both dict and Pydantic models)
                if hasattr(place, 'place_id'):
                    place_id = place.place_id
                else:
                    place_id = place.get('place_id')
                place_data = None
                #print(f"DEBUG: {place_name} - Not found in database, using original place_id: {place_id}")
        else:  # Additional place from DB
            place_name = place.get("name")
            place_id = place.get("place_id")
            place_notes = ""
            place_category = place.get("wayfare_category", place.get("category", "attraction"))
            place_data = place  # Use the place data for duration calculation
        
        # Calculate visit duration
        duration = get_visit_duration(place_category, place_name, travel_style, place_data, current_time)
        
        #print(f"DEBUG: {place_name} - Category: {place_category}, Final Duration: {duration:.1f} hours ({duration * 60:.0f} minutes)")
        #if place_data:
        #    print(f"DEBUG: {place_name} - Place data duration field: {place_data.get('duration')} minutes")
        #    print(f"DEBUG: {place_name} - Place data wayfare_category: {place_data.get('wayfare_category')}")
        #    print(f"DEBUG: {place_name} - Place data category: {place_data.get('category')}")
        #else:
        #    print(f"DEBUG: {place_name} - No place data found in database")
        
        # Check opening hours and adjust schedule if needed
        opening_hours = place_data.get("opening_hours") if place_data else None
        if opening_hours and not is_place_open(opening_hours, current_time):
            print(f"DEBUG: {place_name} - Closed at {current_time.strftime('%H:%M')}, checking alternative times...")
            # Try to find a better time slot within opening hours and our cutoff
            adjusted_time = find_best_visit_time(opening_hours, current_time, duration)
            if adjusted_time:
                # Double-check that the adjusted time respects our cutoff
                buffer_minutes = 15 if travel_style == "relaxed" else (10 if travel_style == "moderate" else 5)
                predicted_finish_time = adjusted_time + timedelta(hours=duration) + timedelta(minutes=buffer_minutes)
                cutoff_time = datetime.combine(day_date, datetime.strptime("20:30", "%H:%M").time())
                
                if predicted_finish_time <= cutoff_time:
                    current_time = adjusted_time
                    print(f"DEBUG: {place_name} - Adjusted to {current_time.strftime('%H:%M')}")
                else:
                    print(f"DEBUG: {place_name} - Adjusted time would violate 20:30 cutoff, skipping...")
                    break
            else:
                print(f"DEBUG: {place_name} - Cannot find suitable time within constraints, skipping...")
                break
        
        # SMART PREDICTIVE APPROACH: Calculate when this activity would finish
        # Include buffer time that will be added after the activity
        buffer_minutes = 15 if travel_style == "relaxed" else (10 if travel_style == "moderate" else 5)
        
        # ENHANCED: Also predict potential travel time to next place (conservative estimate)
        estimated_next_travel = 30  # Conservative 30-minute estimate for potential next travel
        predicted_finish_time = current_time + timedelta(hours=duration) + timedelta(minutes=buffer_minutes + estimated_next_travel)
        
        # ENFORCE: Hard cutoff - activities must finish before 20:30 to ensure safety buffer before 22:00
        cutoff_time = datetime.combine(day_date, datetime.strptime("20:30", "%H:%M").time())
        if predicted_finish_time > cutoff_time:
            print(f"DEBUG: {place_name} - Would finish after 20:30 including travel ({predicted_finish_time.strftime('%H:%M')}), stopping schedule")
            break
        
        # ENHANCED: For late afternoon activities, be extra conservative
        if current_time.hour >= 17:
            # After 5 PM, be more restrictive
            conservative_cutoff = datetime.combine(day_date, datetime.strptime("19:30", "%H:%M").time())
            if predicted_finish_time > conservative_cutoff:
                print(f"DEBUG: {place_name} - Late afternoon activity would extend too long ({predicted_finish_time.strftime('%H:%M')}), stopping schedule")
                break
        
        # ENFORCE: Progressive start time restrictions based on activity duration
        # Long activities (3+ hours) cannot start after 17:30
        if duration >= 3.0 and current_time.hour >= 17 and current_time.minute >= 30:
            print(f"DEBUG: {place_name} - Long activity ({duration}h) would start too late ({current_time.strftime('%H:%M')}), stopping schedule")
            break
        
        # ENFORCE: Medium activities (2+ hours) cannot start after 18:30  
        if duration >= 2.0 and current_time.hour >= 18 and current_time.minute >= 30:
            print(f"DEBUG: {place_name} - Medium activity ({duration}h) would start too late ({current_time.strftime('%H:%M')}), stopping schedule")
            break
        
        # ENFORCE: All activities cannot start after 19:30
        if current_time.hour >= 19 and current_time.minute >= 30:
            print(f"DEBUG: {place_name} - Would start after 19:30 ({current_time.strftime('%H:%M')}), stopping schedule")
            break

        # ENFORCE: Stop scheduling if we're approaching 21:00 to ensure buffer
        if current_time.hour >= 21:
            print(f"DEBUG: Stopping schedule - approaching 21:00 ({current_time.strftime('%H:%M')})")
            break
        
        # Add place visit
        activity = Activity(
            place_id=place_id,
            place_name=place_name,
            time=current_time.strftime("%H:%M"),
            notes=f"{place_notes} (Visit duration: {duration:.1f} hours)" if place_notes else f"Visit duration: {duration:.1f} hours"
        )
        schedule.append(activity)
        
        # Move to next place
        current_time += timedelta(hours=duration)
        
        # Add buffer time (5-15 minutes depending on travel style)
        buffer_minutes = 15 if travel_style == "relaxed" else (10 if travel_style == "moderate" else 5)
        current_time += timedelta(minutes=buffer_minutes)
        
        # ENFORCE: Critical check - stop immediately if we exceed 20:30 cutoff
        # This prevents the next loop iteration from adding travel activities
        cutoff_time = datetime.combine(day_date, datetime.strptime("20:30", "%H:%M").time())
        if current_time > cutoff_time:
            print(f"DEBUG: Stopping schedule - exceeded 20:30 cutoff after activity ({current_time.strftime('%H:%M')})")
            break
            
        # ENFORCE: Additional safety - if we're at or past 20:25, stop to prevent travel overflow
        near_cutoff = datetime.combine(day_date, datetime.strptime("20:25", "%H:%M").time())
        if current_time >= near_cutoff:
            print(f"DEBUG: Stopping schedule - approaching 20:30 cutoff ({current_time.strftime('%H:%M')}), preventing travel overflow")
            break
    
    # ENFORCE: Final validation - ensure no activities extend past 22:00
    validated_schedule = []
    for activity in schedule:
        # Parse activity time
        try:
            activity_time = datetime.strptime(activity.time, "%H:%M").time()
            if activity_time.hour >= 22:
                print(f"DEBUG: Removing {activity.place_name} - starts after 22:00 ({activity.time})")
                continue
            
            # Check if activity would end after 22:00
            if "Visit duration" in activity.notes:
                try:
                    duration_match = re.search(r"Visit duration: ([\d.]+) hours", activity.notes)
                    if duration_match:
                        duration_hours = float(duration_match.group(1))
                        activity_end_time = datetime.combine(day_date, activity_time) + timedelta(hours=duration_hours)
                        if activity_end_time.hour >= 22:
                            print(f"DEBUG: Removing {activity.place_name} - would end after 22:00")
                            continue
                except:
                    pass
            
            validated_schedule.append(activity)
        except:
            # If time parsing fails, skip the activity
            print(f"DEBUG: Removing {activity.place_name} - invalid time format")
            continue
    
    print(f"DEBUG: create_smart_schedule returning {len(validated_schedule)} activities for {day_date.strftime('%Y-%m-%d')}")
    return validated_schedule, travel_counter


def validate_and_fix_schedule(schedule: List[Activity], day_date: datetime) -> List[Activity]:
    """Validate and fix schedule to ensure realistic timing"""
    if not schedule:
        return schedule
    
    fixed_schedule = []
    current_time = datetime.combine(day_date, datetime.strptime("08:00", "%H:%M").time())
    
    # Track break activities to avoid duplicates
    lunch_added = False
    dinner_added = False
    
    for activity in schedule:
        # Parse activity time
        try:
            activity_time = datetime.strptime(activity.time, "%H:%M").time()
            activity_datetime = datetime.combine(day_date, activity_time)
        except:
            # If time parsing fails, use current time
            activity_datetime = current_time
        
        # Skip activities that are too early (before 08:00)
        if activity_datetime.hour < 8:
            print(f"DEBUG: Skipping {activity.place_name} - too early ({activity.time})")
            continue
        
        # ENFORCE: Skip activities that start after 20:30 (our unified cutoff)
        cutoff_time = datetime.combine(day_date, datetime.strptime("20:30", "%H:%M").time())
        if activity_datetime > cutoff_time:
            print(f"DEBUG: Skipping {activity.place_name} - starts after 20:30 cutoff ({activity.time})")
            continue
            
        # Skip activities that are too late (after 22:00) - legacy safety check
        if activity_datetime.hour >= 22:
            print(f"DEBUG: Skipping {activity.place_name} - too late ({activity.time})")
            continue
        
        # Skip activities that would end after 22:00
        if "Visit duration" in activity.notes:
            try:
                duration_match = re.search(r"Visit duration: ([\d.]+) hours", activity.notes)
                if duration_match:
                    duration_hours = float(duration_match.group(1))
                    activity_end_time = activity_datetime + timedelta(hours=duration_hours)
                    if activity_end_time.hour >= 22:
                        print(f"DEBUG: Skipping {activity.place_name} - would end after 22:00 ({activity_end_time.strftime('%H:%M')})")
                        continue
                    # Additional safety check: stop if activity would end after 21:00
                    if activity_end_time.hour >= 21:
                        print(f"DEBUG: Skipping {activity.place_name} - would end after 21:00 ({activity_end_time.strftime('%H:%M')})")
                        continue
            except:
                pass
        
        # Skip duplicate break activities
        if "Lunch Break" in activity.place_name and lunch_added:
            print(f"DEBUG: Skipping duplicate lunch break at {activity.time}")
            continue
        if "Dinner Break" in activity.place_name and dinner_added:
            print(f"DEBUG: Skipping duplicate dinner break at {activity.time}")
            continue
        
        # Ensure activities are in chronological order
        if activity_datetime < current_time:
            # Adjust time to be after current time
            activity_datetime = current_time
            activity.time = activity_datetime.strftime("%H:%M")
        
        # Update current time for next activity
        if "Visit duration" in activity.notes:
            # Extract duration from notes
            try:
                duration_match = re.search(r"Visit duration: ([\d.]+) hours", activity.notes)
                if duration_match:
                    duration_hours = float(duration_match.group(1))
                    current_time = activity_datetime + timedelta(hours=duration_hours)
                else:
                    current_time = activity_datetime + timedelta(hours=1)  # Default 1 hour
            except:
                current_time = activity_datetime + timedelta(hours=1)
        else:
            # For travel and break activities, add reasonable time
            current_time = activity_datetime + timedelta(minutes=30)
        
        # Track break activities
        if "Lunch Break" in activity.place_name:
            lunch_added = True
        elif "Dinner Break" in activity.place_name:
            dinner_added = True
        
        fixed_schedule.append(activity)
    
    return fixed_schedule


async def search_places_endpoint(
    request: SearchPlacesRequest,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    try:
        # User authentication
        try:
            payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub") or payload.get("user_id")
            if not username:
                return SearchPlacesResponse(
                    success=False,
                    message="Invalid token: user_id missing",
                    status_code=401,
                    data=[]
                )
        except JWTError:
            return SearchPlacesResponse(
                success=False,
                message="Invalid token",
                status_code=401,
                data=[]
            )
        # Build MongoDB query (no numeric filters)
        query = {"city": {"$regex": f"^{request.city}$", "$options": "i"}}
        if request.category:
            # Search in both category and wayfare_category fields
            query["$or"] = [
                {"category": {"$regex": f"^{request.category}$", "$options": "i"}},
                {"wayfare_category": {"$regex": f"^{request.category}$", "$options": "i"}}
            ]
        if request.name:
            query["name"] = {"$regex": request.name, "$options": "i"}
        if request.country:
            query["country"] = {"$regex": f"^{request.country}$", "$options": "i"}
        if request.keywords:
            query["$text"] = {"$search": request.keywords}
        print("MongoDB query:", query)
        places = await places_collection.find(query).limit(request.limit or 10).to_list(length=None)
        print("Places returned from MongoDB:", len(places))
        for place in places:
            print(place)
        result = []
        for place in places:
            place["_id"] = str(place["_id"])
            if "coordinates" in place and place["coordinates"]:
                coords = place["coordinates"]
                if isinstance(coords, dict):
                    lat = coords.get("lat")
                    lng = coords.get("lng")
                    coords["lat"] = float(lat) if lat is not None else 0.0
                    coords["lng"] = float(lng) if lng is not None else 0.0
                    place["coordinates"] = coords
            # Updated budget filtering (Python-side)
            if request.budget:
                price_value = parse_price(place.get("price", ""))
                if request.budget == "low" and price_value >= 20:
                    print(f"Filtered out by budget (low): {place['name']} (price_value: {price_value})")
                    continue
                elif request.budget == "medium" and price_value >= 50:
                    print(f"Filtered out by budget (medium): {place['name']} (price_value: {price_value})")
                    continue
                # For 'high', do not filter out any places
            # Rating filtering (Python-side)
            if request.min_rating is not None and place.get("rating") is not None:
                try:
                    place_rating = float(place["rating"])
                    print(f"Place: {place['name']}, place_rating: {place_rating}, min_rating: {request.min_rating}")
                    if place_rating < request.min_rating:
                        print(f"Filtered out by min_rating: {place['name']} (place_rating: {place_rating}, min_rating: {request.min_rating})")
                        continue
                except Exception as e:
                    print(f"Rating conversion error for {place['name']}: {e}")
                    continue
            if request.rating is not None and place.get("rating") is not None:
                try:
                    place_rating = float(place["rating"])
                    if place_rating != request.rating:
                        print(f"Filtered out by rating: {place['name']} (place_rating: {place_rating}, rating: {request.rating})")
                        continue
                except Exception as e:
                    print(f"Rating conversion error for {place['name']}: {e}")
                    continue
            # Popularity filtering (if needed)
            if hasattr(request, "popularity") and request.popularity is not None and place.get("popularity") is not None:
                try:
                    place_popularity = float(place["popularity"])
                    if place_popularity < request.popularity:
                        print(f"Filtered out by popularity: {place['name']} (place_popularity: {place_popularity}, popularity: {request.popularity})")
                        continue
                except Exception as e:
                    print(f"Popularity conversion error for {place['name']}: {e}")
                    continue
            try:
                # Convert popularity to float if present
                if "popularity" in place:
                    try:
                        place["popularity"] = float(place["popularity"])
                    except Exception:
                        place["popularity"] = None
                # Convert rating to float if present
                if "rating" in place:
                    try:
                        place["rating"] = float(place["rating"])
                    except Exception:
                        place["rating"] = None
                # (Add similar conversion for any other numeric fields stored as string)
                result.append(PlaceInCityResponse(**place))
            except Exception as e:
                print(f"Error creating PlaceInCityResponse for {place.get('name', 'unknown')}: {e}")
        print("Final result count:", len(result))
        return SearchPlacesResponse(
            success=True,
            message="Places fetched successfully" if result else "No places found.",
            status_code=200,
            data=result
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=SearchPlacesResponse(
                success=False,
                message=f"Error: {str(e)}",
                status_code=500,
                data=[]
            ).dict()
        )


async def autocomplete_places_endpoint(
    request: AutocompletePlacesRequest,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Autocomplete endpoint for place search in UI"""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Extract validated parameters from BaseModel
    city = request.city
    search_term = request.search_term.strip()
    limit = request.limit

    if len(search_term) < 2:
        return SearchPlacesResponse(
            success=True,
            message="Search term must be at least 2 characters",
            status_code=200,
            data=[]
        )

    # Clean search term
    search_term = search_term.strip().lower()
    
    # Build search query with multiple matching strategies
    search_query = {
        "city": {"$regex": f"^{city}$", "$options": "i"},
        "$or": [
            # Exact match (highest priority)
            {"name": {"$regex": f"^{search_term}$", "$options": "i"}},
            # Starts with search term
            {"name": {"$regex": f"^{search_term}", "$options": "i"}},
            # Contains search term
            {"name": {"$regex": search_term, "$options": "i"}},
            # Word-by-word matching
            {"name": {"$regex": f".*{search_term}.*", "$options": "i"}}
        ]
    }

    # Execute search
    places = await places_collection.find(search_query).limit(limit * 2).to_list(length=None)
    
    # Sort results by relevance (exact matches first, then starts with, then contains)
    def calculate_relevance_score(place_name: str, search_term: str) -> int:
        place_name_lower = place_name.lower()
        search_term_lower = search_term.lower()
        
        if place_name_lower == search_term_lower:
            return 100  # Exact match
        elif place_name_lower.startswith(search_term_lower):
            return 80   # Starts with
        elif search_term_lower in place_name_lower:
            return 60   # Contains
        else:
            return 40   # Word match
    
    # Sort places by relevance score
    places_with_scores = []
    for place in places:
        score = calculate_relevance_score(place.get("name", ""), search_term)
        places_with_scores.append((place, score))
    
    # Sort by score (highest first) and then by popularity
    places_with_scores.sort(key=lambda x: (-x[1], float(x[0].get("popularity", "999999"))))
    
    # Convert to response format
    results = []
    for place, score in places_with_scores[:limit]:
        place_response = PlaceInCityResponse(
            _id=str(place["_id"]),
            place_id=place.get("place_id"),
            city=place.get("city"),
            name=place.get("name"),
            category=place.get("category"),
            wayfare_category=place.get("wayfare_category"),
            price=place.get("price"),
            rating=place.get("rating"),
            image=place.get("image"),
            detail_url=place.get("detail_url"),
            opening_hours=place.get("opening_hours"),
            coordinates=PlaceCoordinates(
                lat=place["coordinates"]["lat"],
                lng=place["coordinates"]["lng"]
            ) if place.get("coordinates") and place["coordinates"].get("lat") and place["coordinates"].get("lng") else None,
            address=place.get("address"),
            source=place.get("source"),
            created_at=place.get("created_at"),
            updated_at=place.get("updated_at"),
            country=place.get("country"),
            country_id=place.get("country_id"),
            city_id=place.get("city_id"),
            popularity=place.get("popularity"),
            duration=place.get("duration")
        )
        results.append(place_response)

    return SearchPlacesResponse(
        success=True,
        message=f"Found {len(results)} places matching '{search_term}' in {city}",
        status_code=200,
        data=results
    )


# ROUTE MANAGEMENT ENDPOINTS

async def get_user_routes_endpoint(token: HTTPAuthorizationCredentials):
    """Get all routes for the current user with place images (optimized)"""
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return RouteListResponse(
                success=False,
                message="Invalid credentials",
                status_code=401,
                data=[]
            )
        
        user = await user_collection.find_one({"username": username})
        if not user:
            return RouteListResponse(
                success=False,
                message="User not found",
                status_code=404,
                data=[]
            )
        
        user_id = str(user["_id"])
        routes = await route_collection.find({"user_id": user_id}).to_list(length=None)
        
        # Collect all unique place_ids from all routes to batch fetch images
        all_place_ids = set()
        for route in routes:
            if "days" in route and route["days"]:
                for day in route["days"]:
                    if "activities" in day and day["activities"]:
                        for activity in day["activities"]:
                            place_id = activity.get("place_id")
                            if place_id and not place_id.startswith(("travel_", "break_")):
                                all_place_ids.add(place_id)
        
        # Batch fetch all place images in one query
        place_images = {}
        if all_place_ids:
            places = await places_collection.find(
                {"place_id": {"$in": list(all_place_ids)}},
                {"place_id": 1, "image": 1}  # Only fetch place_id and image fields
            ).to_list(length=None)
            
            # Create a lookup dictionary for fast access
            place_images = {place["place_id"]: place.get("image") for place in places}
        
        # Process routes and add images using the lookup dictionary
        route_responses = []
        for route in routes:
            if "days" in route and route["days"]:
                for day in route["days"]:
                    if "activities" in day and day["activities"]:
                        enhanced_activities = []
                        for activity in day["activities"]:
                            # Create enhanced activity with image
                            enhanced_activity = activity.copy()
                            
                            # Add image from lookup dictionary
                            place_id = activity.get("place_id")
                            if place_id and not place_id.startswith(("travel_", "break_")):
                                enhanced_activity["image"] = place_images.get(place_id)
                            else:
                                enhanced_activity["image"] = None
                            
                            enhanced_activities.append(enhanced_activity)
                        
                        # Replace activities with enhanced activities
                        day["activities"] = enhanced_activities
            
            route["route_id"] = str(route["_id"])
            route["user_id"] = str(route["user_id"])
            route.pop("_id", None)
            route_responses.append(RouteResponse(**route))
        
        return RouteListResponse(
            success=True,
            message="Routes fetched successfully",
            status_code=200,
            data=route_responses
        )
    except JWTError:
        return RouteListResponse(
            success=False,
            message="Invalid token",
            status_code=401,
            data=[]
        )
    except Exception as e:
        return RouteListResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=500,
            data=[]
        )


async def get_route_by_id_endpoint(route_id: str, token: HTTPAuthorizationCredentials):
    """Get a specific route by ID and track view"""
    try:
        # Validate route_id format
        if not ObjectId.is_valid(route_id):
            return RouteDetailResponse(
                success=False,
                message="Invalid route ID format",
                status_code=400,
                data=None
            )
        
        # Get current user
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return RouteDetailResponse(
                success=False,
                message="Invalid credentials",
                status_code=401,
                data=None
            )
        
        user = await user_collection.find_one({"username": username})
        if not user:
            return RouteDetailResponse(
                success=False,
                message="User not found",
                status_code=404,
                data=None
            )
        
        # Get route
        route = await route_collection.find_one({"_id": ObjectId(route_id)})
        if not route:
            return RouteDetailResponse(
                success=False,
                message="Route not found",
                status_code=404,
                data=None
            )
        
        # Track view (increment view count)
        await route_collection.update_one(
            {"_id": ObjectId(route_id)},
            {"$inc": {"stats.views_count": 1}}
        )
        
        # Prepare response
        route["route_id"] = str(route["_id"])
        route["user_id"] = str(route["user_id"])
        route.pop("_id", None)
        
        return RouteDetailResponse(
            success=True,
            message="Route fetched successfully",
            status_code=200,
            data=RouteResponse(**route)
        )
    except JWTError:
        return RouteDetailResponse(
            success=False,
            message="Invalid token",
            status_code=401,
            data=None
        )
    except Exception as e:
        return RouteDetailResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=500,
            data=None
        )


async def update_route_endpoint(
    route_id: str,
    route_update: RouteUpdateInput,
    token: HTTPAuthorizationCredentials
):
    """Update a route"""
    try:
        # Validate route_id format
        if not ObjectId.is_valid(route_id):
            raise HTTPException(status_code=400, detail="Invalid route ID format")
        
        # Get current user
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Check if route exists and belongs to user
        route = await route_collection.find_one({"_id": ObjectId(route_id)})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        if str(route["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this route")
        
        # Prepare update data
        update_data = {}
        if route_update.title is not None:
            update_data["title"] = route_update.title
        if route_update.city is not None:
            update_data["city"] = route_update.city
        if route_update.start_date is not None:
            update_data["start_date"] = route_update.start_date
        if route_update.end_date is not None:
            update_data["end_date"] = route_update.end_date
        if route_update.category is not None:
            update_data["category"] = route_update.category
        if route_update.season is not None:
            update_data["season"] = route_update.season
        if route_update.must_visit is not None:
            update_data["must_visit"] = [mv.dict() for mv in route_update.must_visit]
        if route_update.days is not None:
            update_data["days"] = [day.dict() for day in route_update.days]
        
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update route
        await route_collection.update_one(
            {"_id": ObjectId(route_id)},
            {"$set": update_data}
        )
        
        return {
            "success": True,
            "message": "Route updated successfully",
            "status_code": 200
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating route: {str(e)}")


async def delete_route_endpoint(route_id: str, token: HTTPAuthorizationCredentials):
    """Delete a route"""
    try:
        # Validate route_id format
        if not ObjectId.is_valid(route_id):
            raise HTTPException(status_code=400, detail="Invalid route ID format")
        
        # Get current user
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Check if route exists and belongs to user
        route = await route_collection.find_one({"_id": ObjectId(route_id)})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        if str(route["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this route")
        
        # Delete route
        await route_collection.delete_one({"_id": ObjectId(route_id)})
        
        return {
            "success": True,
            "message": "Route deleted successfully",
            "status_code": 200
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting route: {str(e)}")


async def get_public_routes_endpoint(
    token: HTTPAuthorizationCredentials,
    category: Optional[str] = None,
    season: Optional[str] = None,
    budget: Optional[str] = None,
    limit: int = 10
):
    """Get public routes with optional filtering"""
    try:
        # Get current user
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return RouteListResponse(
                success=False,
                message="Invalid credentials",
                status_code=401,
                data=[]
            )
        
        # Build query for public routes
        query = {}
        if category:
            query["category"] = category
        if season:
            query["season"] = season
        if budget:
            query["budget"] = budget
        
        # Get routes (for now, all routes are public - you can add is_public field later)
        routes = await route_collection.find(query).limit(limit).to_list(length=None)
        
        route_responses = []
        for route in routes:
            route["route_id"] = str(route["_id"])
            route["user_id"] = str(route["user_id"])
            route.pop("_id", None)
            route_responses.append(RouteResponse(**route))
        
        return RouteListResponse(
            success=True,
            message="Public routes fetched successfully",
            status_code=200,
            data=route_responses
        )
    except JWTError:
        return RouteListResponse(
            success=False,
            message="Invalid token",
            status_code=401,
            data=[]
        )
    except Exception as e:
        return RouteListResponse(
            success=False,
            message=f"Error: {str(e)}",
            status_code=500,
            data=[]
        )


## FEEDBACK ENDPOINTS
# Place Feedback Endpoints
async def submit_place_feedback_endpoint(request: SubmitPlaceFeedbackRequest, token: HTTPAuthorizationCredentials):
    """Submit feedback for a place"""
    try:
        # Verify token and get user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user_id from username
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Check if place exists
        place = await places_collection.find_one({"place_id": request.place_id})
        if not place:
            raise HTTPException(status_code=404, detail="Place not found")
        
        # Check if user already has feedback for this place
        existing_feedback = await place_feedback_collection.find_one({
            "user_id": user_id,
            "place_id": request.place_id
        })
        
        if existing_feedback:
            raise HTTPException(status_code=409, detail="Feedback already exists for this place. Use PUT to update.")
        
        # Create feedback document
        feedback_doc = {
            "user_id": user_id,
            "place_id": request.place_id,
            "rating": request.rating,
            "comment": request.comment,
            "visited_on": request.visited_on,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert feedback
        result = await place_feedback_collection.insert_one(feedback_doc)
        feedback_id = str(result.inserted_id)
        
        return SubmitFeedbackResponse(
            success=True,
            message="Place feedback submitted successfully",
            status_code=201,
            feedback_id=feedback_id,
            created_at=feedback_doc["created_at"]
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

async def get_place_feedback_endpoint(place_id: str, token: HTTPAuthorizationCredentials):
    """Get all feedback for a specific place"""
    try:
        # Verify token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if place exists
        place = await places_collection.find_one({"place_id": place_id})
        if not place:
            raise HTTPException(status_code=404, detail="Place not found")
        
        # Get all feedback for the place
        feedback_cursor = place_feedback_collection.find({"place_id": place_id})
        feedback_list = await feedback_cursor.to_list(length=None)
        
        # Convert to response format
        feedback_responses = []
        for feedback in feedback_list:
            feedback_response = PlaceFeedbackResponse(
                feedback_id=str(feedback["_id"]),
                user_id=feedback["user_id"],
                place_id=feedback["place_id"],
                rating=feedback["rating"],
                comment=feedback.get("comment"),
                visited_on=feedback.get("visited_on"),
                created_at=feedback.get("created_at"),
                updated_at=feedback.get("updated_at")
            )
            feedback_responses.append(feedback_response)
        
        return GetPlaceFeedbackResponse(
            success=True,
            message=f"Retrieved {len(feedback_responses)} feedback entries for place",
            status_code=200,
            data=feedback_responses
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving feedback: {str(e)}")

async def get_user_place_feedback_endpoint(place_id: str, user_id: str, token: HTTPAuthorizationCredentials):
    """Get specific user's feedback for a place"""
    try:
        # Verify token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Find the feedback
        feedback = await place_feedback_collection.find_one({
            "place_id": place_id,
            "user_id": user_id
        })
        
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        feedback_response = PlaceFeedbackResponse(
            feedback_id=str(feedback["_id"]),
            user_id=feedback["user_id"],
            place_id=feedback["place_id"],
            rating=feedback["rating"],
            comment=feedback.get("comment"),
            visited_on=feedback.get("visited_on"),
            created_at=feedback.get("created_at"),
            updated_at=feedback.get("updated_at")
        )
        
        return GetPlaceFeedbackResponse(
            success=True,
            message="User feedback retrieved successfully",
            status_code=200,
            data=[feedback_response]
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user feedback: {str(e)}")

async def update_place_feedback_endpoint(feedback_id: str, request: UpdatePlaceFeedbackRequest, token: HTTPAuthorizationCredentials):
    """Update existing place feedback"""
    try:
        # Verify token and get user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user_id from username
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Validate ObjectId format
        try:
            feedback_object_id = ObjectId(feedback_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid feedback ID format")
        
        # Find existing feedback
        existing_feedback = await place_feedback_collection.find_one({"_id": feedback_object_id})
        if not existing_feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Check if user owns this feedback
        if existing_feedback["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this feedback")
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        
        if request.rating is not None:
            update_data["rating"] = request.rating
        if request.comment is not None:
            update_data["comment"] = request.comment
        if request.visited_on is not None:
            update_data["visited_on"] = request.visited_on
        
        # Update feedback
        await place_feedback_collection.update_one(
            {"_id": feedback_object_id},
            {"$set": update_data}
        )
        
        return UpdateFeedbackResponse(
            success=True,
            message="Place feedback updated successfully",
            status_code=200,
            updated_at=update_data["updated_at"]
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating feedback: {str(e)}")

async def delete_place_feedback_endpoint(feedback_id: str, token: HTTPAuthorizationCredentials):
    """Delete place feedback"""
    try:
        # Verify token and get user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user_id from username
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Validate ObjectId format
        try:
            feedback_object_id = ObjectId(feedback_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid feedback ID format")
        
        # Find existing feedback
        existing_feedback = await place_feedback_collection.find_one({"_id": feedback_object_id})
        if not existing_feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Check if user owns this feedback
        if existing_feedback["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")
        
        # Delete feedback
        await place_feedback_collection.delete_one({"_id": feedback_object_id})
        
        return DeleteFeedbackResponse(
            success=True,
            message="Place feedback deleted successfully",
            status_code=200,
            deleted_at=datetime.utcnow()
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting feedback: {str(e)}")

async def get_place_feedback_stats_endpoint(place_id: str, token: HTTPAuthorizationCredentials):
    """Get feedback statistics for a place"""
    try:
        # Verify token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if place exists
        place = await places_collection.find_one({"place_id": place_id})
        if not place:
            raise HTTPException(status_code=404, detail="Place not found")
        
        # Get all feedback for the place
        feedback_cursor = place_feedback_collection.find({"place_id": place_id})
        feedback_list = await feedback_cursor.to_list(length=None)
        
        if not feedback_list:
            stats_data = {
                "total_feedback": 0,
                "average_rating": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        else:
            # Calculate statistics
            ratings = [feedback["rating"] for feedback in feedback_list]
            total_feedback = len(ratings)
            average_rating = sum(ratings) / total_feedback
            
            # Rating distribution
            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for rating in ratings:
                rating_distribution[rating] += 1
            
            stats_data = {
                "total_feedback": total_feedback,
                "average_rating": round(average_rating, 2),
                "rating_distribution": rating_distribution
            }
        
        return FeedbackStatsResponse(
            success=True,
            message="Place feedback statistics retrieved successfully",
            status_code=200,
            data=stats_data
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

# Route Feedback Endpoints
async def submit_route_feedback_endpoint(request: SubmitRouteFeedbackRequest, token: HTTPAuthorizationCredentials):
    """Submit feedback for a route"""
    try:
        # Verify token and get user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user_id from username
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Check if route exists
        route = await route_collection.find_one({"route_id": request.route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Check if user already has feedback for this route
        existing_feedback = await route_feedback_collection.find_one({
            "user_id": user_id,
            "route_id": request.route_id
        })
        
        if existing_feedback:
            raise HTTPException(status_code=409, detail="Feedback already exists for this route. Use PUT to update.")
        
        # Create feedback document
        feedback_doc = {
            "user_id": user_id,
            "route_id": request.route_id,
            "rating": request.rating,
            "comment": request.comment,
            "visited_on": request.visited_on,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert feedback
        result = await route_feedback_collection.insert_one(feedback_doc)
        feedback_id = str(result.inserted_id)
        
        return SubmitFeedbackResponse(
            success=True,
            message="Route feedback submitted successfully",
            status_code=201,
            feedback_id=feedback_id,
            created_at=feedback_doc["created_at"]
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting route feedback: {str(e)}")

async def get_route_feedback_endpoint(route_id: str, token: HTTPAuthorizationCredentials):
    """Get all feedback for a specific route"""
    try:
        # Verify token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if route exists
        route = await route_collection.find_one({"route_id": route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Get all feedback for the route
        feedback_cursor = route_feedback_collection.find({"route_id": route_id})
        feedback_list = await feedback_cursor.to_list(length=None)
        
        # Convert to response format
        feedback_responses = []
        for feedback in feedback_list:
            feedback_response = RouteFeedbackResponse(
                feedback_id=str(feedback["_id"]),
                user_id=feedback["user_id"],
                route_id=feedback["route_id"],
                rating=feedback["rating"],
                comment=feedback.get("comment"),
                visited_on=feedback.get("visited_on"),
                created_at=feedback.get("created_at"),
                updated_at=feedback.get("updated_at")
            )
            feedback_responses.append(feedback_response)
        
        return GetRouteFeedbackResponse(
            success=True,
            message=f"Retrieved {len(feedback_responses)} feedback entries for route",
            status_code=200,
            data=feedback_responses
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving route feedback: {str(e)}")

async def get_route_feedback_stats_endpoint(route_id: str, token: HTTPAuthorizationCredentials):
    """Get feedback statistics for a route"""
    try:
        # Verify token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check if route exists
        route = await route_collection.find_one({"route_id": route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Get all feedback for the route
        feedback_cursor = route_feedback_collection.find({"route_id": route_id})
        feedback_list = await feedback_cursor.to_list(length=None)
        
        if not feedback_list:
            stats_data = {
                "total_feedback": 0,
                "average_rating": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        else:
            # Calculate statistics
            ratings = [feedback["rating"] for feedback in feedback_list]
            total_feedback = len(ratings)
            average_rating = sum(ratings) / total_feedback
            
            # Rating distribution
            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for rating in ratings:
                rating_distribution[rating] += 1
            
            stats_data = {
                "total_feedback": total_feedback,
                "average_rating": round(average_rating, 2),
                "rating_distribution": rating_distribution
            }
        
        return FeedbackStatsResponse(
            success=True,
            message="Route feedback statistics retrieved successfully",
            status_code=200,
            data=stats_data
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving route statistics: {str(e)}")

async def update_route_feedback_endpoint(feedback_id: str, request: UpdateRouteFeedbackRequest, token: HTTPAuthorizationCredentials):
    """Update existing route feedback"""
    try:
        # Verify token and get user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user_id from username
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Validate ObjectId format
        try:
            feedback_object_id = ObjectId(feedback_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid feedback ID format")
        
        # Find existing feedback
        existing_feedback = await route_feedback_collection.find_one({"_id": feedback_object_id})
        if not existing_feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Check if user owns this feedback
        if existing_feedback["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this feedback")
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        
        if request.rating is not None:
            update_data["rating"] = request.rating
        if request.comment is not None:
            update_data["comment"] = request.comment
        if request.visited_on is not None:
            update_data["visited_on"] = request.visited_on
        
        # Update feedback
        await route_feedback_collection.update_one(
            {"_id": feedback_object_id},
            {"$set": update_data}
        )
        
        return UpdateFeedbackResponse(
            success=True,
            message="Route feedback updated successfully",
            status_code=200,
            updated_at=update_data["updated_at"]
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating route feedback: {str(e)}")

async def delete_route_feedback_endpoint(feedback_id: str, token: HTTPAuthorizationCredentials):
    """Delete route feedback"""
    try:
        # Verify token and get user_id
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get user_id from username
        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user["_id"])
        
        # Validate ObjectId format
        try:
            feedback_object_id = ObjectId(feedback_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid feedback ID format")
        
        # Find existing feedback
        existing_feedback = await route_feedback_collection.find_one({"_id": feedback_object_id})
        if not existing_feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        # Check if user owns this feedback
        if existing_feedback["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this feedback")
        
        # Delete feedback
        await route_feedback_collection.delete_one({"_id": feedback_object_id})
        
        return DeleteFeedbackResponse(
            success=True,
            message="Route feedback deleted successfully",
            status_code=200,
            deleted_at=datetime.utcnow()
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting route feedback: {str(e)}")

async def get_user_route_feedback_endpoint(route_id: str, user_id: str, token: HTTPAuthorizationCredentials):
    """Get specific user's feedback for a route"""
    try:
        # Verify token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Find the feedback
        feedback = await route_feedback_collection.find_one({
            "route_id": route_id,
            "user_id": user_id
        })
        
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        feedback_response = RouteFeedbackResponse(
            feedback_id=str(feedback["_id"]),
            user_id=feedback["user_id"],
            route_id=feedback["route_id"],
            rating=feedback["rating"],
            comment=feedback.get("comment"),
            visited_on=feedback.get("visited_on"),
            created_at=feedback.get("created_at"),
            updated_at=feedback.get("updated_at")
        )
        
        return GetRouteFeedbackResponse(
            success=True,
            message="User route feedback retrieved successfully",
            status_code=200,
            data=[feedback_response]
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise  # Re-raise HTTPExceptions to preserve their status codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user route feedback: {str(e)}")

# ==================== EMAIL VERIFICATION SYSTEM ====================

# In-memory storage for verification codes (in production, use Redis or database)
verification_codes = {}

def generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

async def send_verification_email_endpoint(request: SendVerificationRequest):
    """Send verification code to email"""
    try:
        # Generate verification code
        verification_code = generate_verification_code()
        
        # Store the code with email (expires in 10 minutes)
        verification_codes[request.email] = {
            "code": verification_code,
            "created_at": datetime.utcnow()
        }
        
        # Create email message
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verification</title>
        </head>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333; text-align: center;">WayfareApp Email Verification</h2>
                <p style="font-size: 16px; color: #555;">Hello!</p>
                <p style="font-size: 16px; color: #555;">
                    Thank you for registering with WayfareApp. Please use the verification code below to complete your registration:
                </p>
                <div style="background-color: #f0f0f0; padding: 20px; text-align: center; margin: 20px 0;">
                    <h1 style="color: #007bff; font-size: 36px; margin: 0;">{verification_code}</h1>
                </div>
                <p style="font-size: 14px; color: #777;">
                    This verification code will expire in 10 minutes. If you didn't request this verification, please ignore this email.
                </p>
                <p style="font-size: 14px; color: #777;">
                    Best regards,<br>
                    The WayfareProject Team
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="WayfareProject Email Verification",
            recipients=[request.email],
            body=html_content,
            subtype=MessageType.html
        )
        
        # Send email (or suppress for development)
        await fastmail.send_message(message)
        
        # In development mode, print the verification code to console
        print(f"📧 DEVELOPMENT MODE: Verification code for {request.email}: {verification_code}")
        print(f"🔗 Use this code to test verification endpoint")
        
        return VerificationResponse(
            success=True,
            message="Code sent successfully",
            status_code=200
        )
        
    except Exception as e:
        # For development, we'll return success even if email fails
        # Print the verification code to console for testing
        print(f"📧 DEVELOPMENT MODE: Verification code for {request.email}: {verification_code}")
        print(f"🔗 Use this code to test verification endpoint")
        print(f"⚠️  Email sending failed (expected in development): {str(e)}")
        return VerificationResponse(
            success=True,
            message="Code sent successfully",
            status_code=200
        )

async def get_top_rated_places_endpoint(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    """
    Get top 5 rated places based on aggregated feedback ratings.
    Returns places with their average feedback rating and all place details.
    """
    try:
        # User authentication
        try:
            payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                return TopRatedPlacesResponse(
                    success=False,
                    message="Invalid credentials",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    data=[]
                )
        except JWTError:
            return TopRatedPlacesResponse(
                success=False,
                message="Invalid token",
                status_code=status.HTTP_401_UNAUTHORIZED,
                data=[]
            )

        # Aggregate feedback ratings for each place
        pipeline = [
            {
                "$group": {
                    "_id": "$place_id",
                    "total_rating": {"$sum": "$rating"},
                    "feedback_count": {"$sum": 1},
                    "average_rating": {"$avg": "$rating"}
                }
            },
            {
                "$sort": {
                    "average_rating": -1,  # Highest average rating first
                    "_id": 1  # Then alphabetically by place_id
                }
            },
            {
                "$limit": 5  # Get top 5 places
            }
        ]
        
        # Execute aggregation pipeline
        feedback_aggregation = await place_feedback_collection.aggregate(pipeline).to_list(length=None)
        
        if not feedback_aggregation:
            return TopRatedPlacesResponse(
                success=True,
                message="No feedback data available",
                status_code=200,
                data=[]
            )
        
        # Get place details for the top-rated places
        top_rated_places = []
        for feedback_data in feedback_aggregation:
            place_id = feedback_data["_id"]
            
            # Get place details from places collection
            place = await places_collection.find_one({"place_id": place_id})
            
            if place:
                # Create TopRatedPlaceResponse object
                top_rated_place = TopRatedPlaceResponse(
                    place_id=place_id,
                    name=place.get("name", ""),
                    city=place.get("city", ""),
                    category=place.get("category", ""),
                    wayfare_category=place.get("wayfare_category"),
                    price=place.get("price"),
                    rating=float(place.get("rating", 0) or 0),  # Original place rating
                    wayfare_rating=round(feedback_data["average_rating"], 2),  # Calculated average (renamed)
                    total_feedback_count=feedback_data["feedback_count"],
                    image=place.get("image"),
                    detail_url=place.get("detail_url"),
                    opening_hours=place.get("opening_hours"),
                    coordinates=PlaceCoordinates(
                        lat=place.get("coordinates", {}).get("lat", 0.0),
                        lng=place.get("coordinates", {}).get("lng", 0.0)
                    ) if place.get("coordinates") else None,
                    address=place.get("address"),
                    source=place.get("source"),
                    country=place.get("country"),
                    country_id=place.get("country_id"),
                    city_id=place.get("city_id"),
                    popularity=float(place.get("popularity", 0) or 0),
                    duration=place.get("duration"),
                    created_at=place.get("created_at"),
                    updated_at=place.get("updated_at")
                )
                top_rated_places.append(top_rated_place)
        
        # Sort by wayfare rating (descending) and then alphabetically by name
        top_rated_places.sort(key=lambda x: (-x.wayfare_rating, x.name.lower()))
        
        return TopRatedPlacesResponse(
            success=True,
            message="Top rated places retrieved successfully",
            status_code=200,
            data=top_rated_places
        )
        
    except Exception as e:
        return TopRatedPlacesResponse(
            success=False,
            message=f"Error retrieving top rated places: {str(e)}",
            status_code=500,
            data=[]
        )

async def verify_email_code_endpoint(request: VerifyCodeRequest):
    """Verify the email verification code"""
    try:
        # Find the verification record by code
        user_email = None
        for email, record in verification_codes.items():
            if record["code"] == request.verification_code:
                user_email = email
                break
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        # Check if code is expired (10 minutes)
        record = verification_codes[user_email]
        time_diff = datetime.utcnow() - record["created_at"]
        if time_diff.total_seconds() > 600:  # 10 minutes
            del verification_codes[user_email]
            raise HTTPException(status_code=400, detail="Verification code has expired")
        
        # Code is valid, remove it from storage
        del verification_codes[user_email]
        
        return VerificationResponse(
            success=True,
            message="Code verified successfully",
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying code: {str(e)}") 


async def search_cities_endpoint(query: str, limit: int, token: HTTPAuthorizationCredentials):
    """
    Search cities by name for autocomplete functionality.
    Returns cities that match the search query with country information.
    """
    try:
        # User authentication
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await user_collection.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Search cities with case-insensitive regex
        search_pattern = {"$regex": f"^{query}", "$options": "i"}
        cities_cursor = cities_collection.find(
            {
                "name": search_pattern,
                "active": True  # Only return active cities
            },
            {
                "_id": 1,
                "name": 1,
                "country": 1,
                "country_id": 1,
                "coordinates": 1
            }
        ).limit(limit)
        
        cities = await cities_cursor.to_list(length=None)
        
        # Format results for UI
        search_results = []
        for city in cities:
            city_result = CitySearchResult(
                city_id=str(city["_id"]),
                name=city.get("name", ""),
                country=city.get("country", ""),
                country_id=city.get("country_id", ""),
                display_text=f"{city.get('name', '')}, {city.get('country', '')}",
                coordinates=CityCoordinates(
                    lat=city.get("coordinates", {}).get("lat", 0.0),
                    lng=city.get("coordinates", {}).get("lng", 0.0)
                ) if city.get("coordinates") else None
            )
            search_results.append(city_result)
        
        # Sort results alphabetically by name
        search_results.sort(key=lambda x: x.name.lower())
        
        message = f"Found {len(search_results)} cities matching '{query}'"
        if len(search_results) == 0:
            message = f"No cities found matching '{query}'"
            
        return CitySearchResponse(
            success=True,
            message=message,
            status_code=200,
            data=search_results
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        return CitySearchResponse(
            success=False,
            message=f"Error searching cities: {str(e)}",
            status_code=500,
            data=[]
        )


# ==================== PLACE SEARCH ENDPOINT ====================
async def search_places_for_must_visit_endpoint(
    city: str,
    query: str = "",
    category: str = None,
    limit: int = 20,
    token: HTTPAuthorizationCredentials = None
):
    """
    Search/autocomplete places for must-visit selection in route creation.
    
    Args:
        city: City name to search places in
        query: Search term for place names (optional, for autocomplete)
        category: Optional category filter (museum, restaurant, etc.)
        limit: Maximum number of places to return (default: 20, max: 50)
        token: JWT authentication token
        
    Returns:
        PlaceSearchResponse with list of matching places for UI selection
    """
    try:
        # Validate authentication
        if token:
            payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Validate limit
        limit = min(max(limit, 1), 50)  # Clamp between 1-50
        
        # Build query for places collection
        search_query = {
            "city": {"$regex": f"^{city}$", "$options": "i"},
            "active": {"$ne": False}  # Exclude inactive places
        }
        
        # Add name search if query provided (for autocomplete)
        if query and len(query.strip()) > 0:
            search_query["name"] = {"$regex": query.strip(), "$options": "i"}
        
        # Add category filter if provided (search wayfare_category primarily)
        if category:
            search_query["wayfare_category"] = {"$regex": f"^{category}$", "$options": "i"}
        
        # Query places collection with sorting by rating and name
        places_cursor = places_collection.find(search_query).sort([
            ("rating", -1),  # Primary sort: highest rated first
            ("name", 1)      # Secondary sort: alphabetical for ties
        ]).limit(limit)
        
        places = await places_cursor.to_list(length=limit)
        
        if not places:
            search_info = f"in {city}"
            if query:
                search_info += f" matching '{query}'"
            if category:
                search_info += f" for category '{category}'"
                
            return PlaceSearchResponse(
                success=True,
                message=f"No places found {search_info}",
                status_code=200,
                data=[]
            )
        
        # Build response data
        search_results = []
        for place in places:
            # Build coordinates if available
            coordinates = None
            if place.get("coordinates"):
                coords = place["coordinates"]
                if isinstance(coords, dict) and coords.get("lat") is not None and coords.get("lng") is not None:
                    coordinates = PlaceCoordinates(
                        lat=float(coords["lat"]),
                        lng=float(coords["lng"])
                    )
            
            place_result = PlaceSearchResult(
                place_id=place.get("place_id", ""),
                name=place.get("name", ""),
                category=place.get("category", ""),
                wayfare_category=place.get("wayfare_category"),
                rating=float(place.get("rating", 0.0)),
                image=place.get("image"),
                coordinates=coordinates,
                address=place.get("address")
            )
            search_results.append(place_result)
        
        message = f"Found {len(search_results)} places in {city}"
        if query:
            message += f" matching '{query}'"
        if category:
            message += f" for category '{category}'"
            
        return PlaceSearchResponse(
            success=True,
            message=message,
            status_code=200,
            data=search_results
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        return PlaceSearchResponse(
            success=False,
            message=f"Error searching places: {str(e)}",
            status_code=500,
            data=[]
        )

