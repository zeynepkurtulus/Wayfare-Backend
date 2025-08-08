from pydantic import BaseModel 
from bson import ObjectId
from typing import List  # Import List from the typing module
from typing import Optional  # Import Optional from the typing module
from pydantic import Field
from pydantic.networks import EmailStr
from typing import Dict, Any
from datetime import datetime


class UserRegistration(BaseModel):
    username : str =Field(min_length=3)
    password : str = Field(min_length=4)
    email : EmailStr 
    first_name : str
    last_name : str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str 

class User(BaseModel):
    username : str =Field(min_length=3)
    password : str = Field(min_length=4)
    email : EmailStr 
    first_name : str
    last_name : str

class LoginData(User):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserInDB(BaseModel):
    username: str
    hashed_password: str


class Preferences(BaseModel):
    interests: List[str]
    budget: str
    travel_style: str


class UserAddInfo(BaseModel):
    preferences: Preferences
    home_city : str 



class UserInfoResponse(BaseModel):
    user_id: str
    email: EmailStr
    username: str
    name: str
    surname: str
    preferences: Preferences
    home_city: str


class DeleteUserRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=4)
    new_password: str = Field(..., min_length=4)
    confirm_password: str = Field(..., min_length=4)

class Coordinates(BaseModel):
    lat: float
    lng: float

class MustVisit(BaseModel):
    place_id: Optional[str] = None
    place_name: str
    address: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    notes: Optional[str] = None
    source: str
    opening_hours: Optional[Dict[str, str]] = None  

class Activity(BaseModel):
    place_id: Optional[str] = None
    place_name: str
    time: Optional[str] = None
    notes: Optional[str] = None
    image: Optional[str] = None  # Add image field for place images

class Day(BaseModel):
    date: str
    activities: List[Activity]

class RouteStats(BaseModel):
    views_count: int = 0
    copies_count: int = 0
    likes_count: int = 0

class Route(BaseModel):
    route_id: Optional[str] = None  # ✅ ADD route_id FIELD
    user_id: Optional[str] = None
    title: str
    city: str
    city_id: Optional[str] = None
    country: Optional[str] = None
    country_id: Optional[str] = None
    start_date: str
    end_date: str
    budget: str  # "low", "medium", "high"
    travel_style: str  # "relaxed", "moderate", "accelerated"
    category: str  # "city_break", "beach", "mountain", "road_trip"
    season: str  # "spring", "summer", "autumn", "winter"
    is_public: bool = False  # Routes are private by default
    stats: RouteStats = Field(default_factory=lambda: RouteStats())
    must_visit: List[MustVisit]
    days: List[Day]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Input-only models for route creation
class MustVisitInput(BaseModel):
    place_name: str
    notes: Optional[str] = None
    source: str
    place_id: Optional[str] = None

class RouteCreateInput(BaseModel):
    title: str
    city: str
    start_date: str
    end_date: str
    category: str = "city_break"  # Default to city_break
    season: Optional[str] = None  # Will be auto-detected if not provided
    is_public: Optional[bool] = False  # Routes are private by default
    must_visit: List[MustVisitInput]

# Response models for routes
class RouteResponse(BaseModel):
    route_id: str
    user_id: str
    title: str
    city: str
    city_id: Optional[str] = None
    country: Optional[str] = None
    country_id: Optional[str] = None
    start_date: str
    end_date: str
    budget: str
    travel_style: str
    category: str
    season: str
    is_public: bool
    stats: RouteStats
    must_visit: List[MustVisit]
    days: List[Day]
    created_at: datetime
    updated_at: datetime

class RouteListResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[RouteResponse]

class RouteDetailResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: Optional[RouteResponse] = None

class RouteCreateResponse(BaseModel):
    success: bool
    message: str
    route_id: str
    status_code: int

class RouteUpdateInput(BaseModel):
    title: Optional[str] = None
    city: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    season: Optional[str] = None
    must_visit: Optional[List[MustVisitInput]] = None
    days: Optional[List[Day]] = None

class CityCoordinates(BaseModel):
    lat: float
    lng: float

class CityResponse(BaseModel):
    city_id: str
    name: str
    country: str
    country_id: str
    active: bool
    coordinates: Optional[CityCoordinates] = None
    timezone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
   
class CityByCountryRequest(BaseModel):
    country: str

class GetAllCitiesResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: list[CityResponse]

class GetCitiesByCountryResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: list[CityResponse]

class CitySearchResult(BaseModel):
    city_id: str
    name: str
    country: str
    country_id: str
    display_text: str  # e.g., "Rome, Italy"
    coordinates: Optional[CityCoordinates] = None

class CitySearchResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[CitySearchResult]

# ==================== PLACE SEARCH MODELS ====================
# Forward reference for PlaceCoordinates - will be resolved later
class PlaceSearchResult(BaseModel):
    place_id: str
    name: str
    category: str
    wayfare_category: Optional[str] = None
    rating: float
    image: Optional[str] = None
    coordinates: Optional["PlaceCoordinates"] = None
    address: Optional[str] = None

class PlaceSearchResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[PlaceSearchResult]

class GetAllCountiesResponse(BaseModel):
    _id: str
    name: str
    country_id: str
    active: bool
    region: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GetAllCountriesListResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: list[GetAllCountiesResponse]

class GetCountriesByRegionRequest(BaseModel):
    region: str

class GetCountriesByRegionResponse(BaseModel):
    _id: str
    name: str
    country_id: str
    active: bool
    region: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GetCountriesByRegionListResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: list[GetCountriesByRegionResponse]

class SearchCountriesRequest(BaseModel):
    names: list[str]

class GetAllRegionsResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: list[str]



class PlaceCoordinates(BaseModel):
    lat: float
    lng: float

class PlaceInCityResponse(BaseModel):
    _id: str
    place_id: str
    city: str
    name: str
    category: str
    wayfare_category: Optional[str] = None
    price: Optional[str]
    rating: float
    image: Optional[str]
    detail_url: Optional[str]
    opening_hours: Optional[Dict[str, str]]
    coordinates: Optional[PlaceCoordinates]
    address: Optional[str]
    source: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    country: Optional[str]
    country_id: Optional[str]
    city_id: Optional[str]
    popularity: float
    duration: Optional[int] = None  # Duration in minutes

class GetPlacesInCityResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    datas: list[PlaceInCityResponse]


class GetPlacesByIdsRequest(BaseModel):
    place_ids: List[str]


class GetPlaceByIdResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: Optional[List[PlaceInCityResponse]]

class SearchPlacesResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[PlaceInCityResponse]

class SearchPlacesRequest(BaseModel):
    city: str
    category: Optional[str] = None
    budget: Optional[str] = None
    rating: Optional[float] = None
    name: Optional[str] = None
    country: Optional[str] = None
    min_rating: Optional[float] = None
    keywords: Optional[str] = None
    limit: Optional[int] = 10


class AutocompletePlacesRequest(BaseModel):
    city: str = Field(..., description="City to search in")
    search_term: str = Field(..., min_length=2, description="Search term (minimum 2 characters)")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results (1-50)")


# Complete place model matching the updated collection structure
class PlaceModel(BaseModel):
    _id: Optional[str] = None
    place_id: str
    city: str
    name: str
    category: str
    wayfare_category: Optional[str] = None
    price: Optional[str] = None
    rating: Optional[str] = None
    image: Optional[str] = None
    detail_url: Optional[str] = None
    opening_hours: Optional[Dict[str, str]] = None
    coordinates: Optional[PlaceCoordinates] = None
    address: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    country: Optional[str] = None
    country_id: Optional[str] = None
    city_id: Optional[str] = None
    popularity: Optional[str] = None
    duration: Optional[int] = None  # Duration in minutes


# ==================== FEEDBACK MODELS ====================

class PlaceFeedback(BaseModel):
    _id: Optional[str] = None
    user_id: str
    place_id: str  
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment about the place")
    visited_on: Optional[str] = Field(None, description="Date when the place was visited (YYYY-MM-DD)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class RouteFeedback(BaseModel):
    _id: Optional[str] = None
    user_id: str
    route_id: str
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment about the route")
    visited_on: Optional[str] = Field(None, description="Date when the route was followed (YYYY-MM-DD)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Request Models
class SubmitPlaceFeedbackRequest(BaseModel):
    place_id: str
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")
    visited_on: Optional[str] = Field(None, description="Date visited (YYYY-MM-DD)")

class SubmitRouteFeedbackRequest(BaseModel):
    route_id: str
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5") 
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")
    visited_on: Optional[str] = Field(None, description="Date visited (YYYY-MM-DD)")

class UpdatePlaceFeedbackRequest(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Updated rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Updated comment")
    visited_on: Optional[str] = Field(None, description="Updated visit date (YYYY-MM-DD)")

class UpdateRouteFeedbackRequest(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Updated rating from 1 to 5")
    comment: Optional[str] = Field(None, max_length=1000, description="Updated comment")  
    visited_on: Optional[str] = Field(None, description="Updated visit date (YYYY-MM-DD)")

# Response Models
class PlaceFeedbackResponse(BaseModel):
    feedback_id: str
    user_id: str
    place_id: str
    rating: int
    comment: Optional[str] = None
    visited_on: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class RouteFeedbackResponse(BaseModel):
    feedback_id: str
    user_id: str
    route_id: str
    rating: int
    comment: Optional[str] = None
    visited_on: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SubmitFeedbackResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    feedback_id: str
    created_at: Optional[datetime] = None

class GetPlaceFeedbackResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[PlaceFeedbackResponse]

class GetRouteFeedbackResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[RouteFeedbackResponse]

class UpdateFeedbackResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    updated_at: Optional[datetime] = None

class DeleteFeedbackResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    deleted_at: Optional[datetime] = None

class FeedbackStatsResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: Dict[str, Any]  # For average rating, total count, etc.

# ==================== EMAIL VERIFICATION MODELS ====================
class SendVerificationRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    verification_code: str

class VerificationResponse(BaseModel):
    success: bool
    message: str
    status_code: int

# ==================== TOP RATED PLACES MODELS ====================
class TopRatedPlaceResponse(BaseModel):
    place_id: str
    name: str
    city: str
    category: str
    wayfare_category: Optional[str] = None
    price: Optional[str] = None
    rating: float  # Original place rating
    wayfare_rating: float  # Calculated average from feedback (renamed)
    total_feedback_count: int  # Number of feedback entries
    image: Optional[str] = None
    detail_url: Optional[str] = None
    opening_hours: Optional[Dict[str, str]] = None
    coordinates: Optional[PlaceCoordinates] = None
    address: Optional[str] = None
    source: Optional[str] = None
    country: Optional[str] = None
    country_id: Optional[str] = None
    city_id: Optional[str] = None
    popularity: Optional[float] = None
    duration: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TopRatedPlacesResponse(BaseModel):
    success: bool
    message: str
    status_code: int
    data: List[TopRatedPlaceResponse]

