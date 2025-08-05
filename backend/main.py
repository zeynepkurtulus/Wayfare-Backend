from fastapi import FastAPI, HTTPException,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi
from typing import Optional

load_dotenv()  # Load environment variables from .env file

from routers.router import(
    register_user_endpoint,
    authenticate_user,
    create_access_token,
    add_user_info,
    get_current_user,
    delete_user_account_endpoint,
    change_user_password_endpoint,
    create_route_endpoint,
    get_user_routes_endpoint,
    get_route_by_id_endpoint,
    update_route_endpoint,
    delete_route_endpoint,
    get_public_routes_endpoint,
    get_cities_endpoint,
    search_cities_endpoint,
    get_cities_by_country_endpoint,
    get_all_countries_endpoint,
    get_countries_by_region_endpoint,
    search_countries_endpoint,
    get_all_regions_endpoint,
    get_places_in_city_endpoint,
    get_place_by_id_endpoint,
    search_places_endpoint,
    autocomplete_places_endpoint,
    # Feedback endpoints
    submit_place_feedback_endpoint,
    get_place_feedback_endpoint,
    get_user_place_feedback_endpoint,
    update_place_feedback_endpoint,
    delete_place_feedback_endpoint,
    get_place_feedback_stats_endpoint,
    submit_route_feedback_endpoint,
    get_route_feedback_endpoint,
    get_route_feedback_stats_endpoint,
    update_route_feedback_endpoint,
    delete_route_feedback_endpoint,
    get_user_route_feedback_endpoint,
    # Email verification endpoints
    send_verification_email_endpoint,
    verify_email_code_endpoint,
    # Top rated places endpoint
    get_top_rated_places_endpoint,
)

from models.model import (
    UserRegistration,
    UserLogin,
    UserAddInfo,
    DeleteUserRequest,
    ChangePasswordRequest,
    Route,
    RouteCreateInput,
    RouteUpdateInput,
    CityByCountryRequest,
    GetCountriesByRegionRequest,
    SearchCountriesRequest,
    GetPlacesByIdsRequest,
    SearchPlacesRequest,
    AutocompletePlacesRequest,
    SubmitPlaceFeedbackRequest,
    SubmitRouteFeedbackRequest,
    UpdatePlaceFeedbackRequest,
    UpdateRouteFeedbackRequest,
    SendVerificationRequest,
    VerifyCodeRequest
)

from config.database import (
    user_collection,        
    route_collection
)


app = FastAPI()
oauth2_scheme = HTTPBearer()
origins = ['https://localhost:3000']


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Wayfare API",
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer"
        }
    }
    openapi_schema["security"] = [{"HTTPBearer": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# USER ENDPOINTS
@app.post("/user/register", tags=["User"])
async def register_user(user_data: UserRegistration):
    response = await register_user_endpoint(user_data)
    if response:
        return response
    else:
        raise HTTPException(404, "Cannot register user")
    

@app.post("/user/login", tags=["User"])
async def login_for_access_token(user_data: UserLogin):
    user = await authenticate_user(user_data.username, user_data.password, user_collection)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"message": "User logged in successfully",
             "success": True,
            "access_token": access_token 
           }


@app.post("/user/addInfo", tags=["User"])
async def add_user_info_helper(user_info: UserAddInfo,token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    response = await add_user_info(user_info, token)
    if response:
        return response
    else:
        raise HTTPException(404, "Cannot add user info")


@app.get("/user/getCurrentUser", tags=["User"])
async def current_user_endpoint(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_current_user(token)


@app.post("/user/changePassword", tags=["User"])
async def change_password_route(
    data: ChangePasswordRequest,
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    return await change_user_password_endpoint(data, token)


@app.delete("/user/delete", tags=["User"])
async def delete_user_route(
    body: DeleteUserRequest,
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    return await delete_user_account_endpoint(body, token)


# ROUTE ENDPOINTS
@app.post("/route/create", tags=["Route"])
async def create_route_main(
    route_input: RouteCreateInput,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await create_route_endpoint(route_input, token)


@app.get("/routes/user", tags=["Route"])
async def get_user_routes_main(
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await get_user_routes_endpoint(token)


@app.get("/routes/{route_id}", tags=["Route"])
async def get_route_by_id_main(
    route_id: str,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await get_route_by_id_endpoint(route_id, token)


@app.put("/routes/{route_id}", tags=["Route"])
async def update_route_main(
    route_id: str,
    route_update: RouteUpdateInput,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await update_route_endpoint(route_id, route_update, token)


@app.delete("/routes/{route_id}", tags=["Route"])
async def delete_route_main(
    route_id: str,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await delete_route_endpoint(route_id, token)


@app.get("/routes/public", tags=["Route"])
async def get_public_routes_main(
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    category: Optional[str] = None,
    season: Optional[str] = None,
    budget: Optional[str] = None,
    limit: int = 10
):
    return await get_public_routes_endpoint(token, category, season, budget, limit)


# PLACES ENDPOINTS
@app.get("/places/city", tags=["Places"])
async def get_places_in_city(
    city: str,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await get_places_in_city_endpoint(city, token)


@app.post("/places/id", tags=["Places"])
async def get_place_by_id_main(
    request: GetPlacesByIdsRequest,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await get_place_by_id_endpoint(request, token)


@app.post("/places/search", tags=["Places"])
async def search_places_main(
    request: SearchPlacesRequest,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await search_places_endpoint(request, token)


@app.post("/places/autocomplete", tags=["Places"])
async def autocomplete_places_main(
    request: AutocompletePlacesRequest,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await autocomplete_places_endpoint(request, token)


@app.get("/places/top-rated", tags=["Places"])
async def get_top_rated_places_main(
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await get_top_rated_places_endpoint(token)


# CITIES ENDPOINTS
@app.get("/cities/search", tags=["Cities"])
async def search_cities(
    q: str,
    limit: int = 10,
    token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    return await search_cities_endpoint(q, limit, token)


@app.get("/cities/all", tags=["Cities"])
async def get_all_cities(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_cities_endpoint()


@app.post("/cities/specific", tags=["Cities"])
async def get_cities_by_name(request: CityByCountryRequest, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_cities_by_country_endpoint(request.country, token)


# COUNTRIES ENDPOINTS
@app.get("/countries/all", tags=["Countries"])
async def get_all_countries(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_all_countries_endpoint(token)

@app.post("/countries/region", tags=["Countries"])
async def get_countries_by_region(
    request: GetCountriesByRegionRequest,
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    return await get_countries_by_region_endpoint(request, token)

@app.post("/countries/search", tags=["Countries"])
async def search_countries(
    request: SearchCountriesRequest,
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
):
    return await search_countries_endpoint(request, token)

@app.get("/countries/allRegions", tags=["Countries"])
async def get_all_regions(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_all_regions_endpoint(token)


# FEEDBACK ENDPOINTS

# Place Feedback Endpoints
@app.post("/feedback/place", tags=["Feedback"])
async def submit_place_feedback(request: SubmitPlaceFeedbackRequest, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await submit_place_feedback_endpoint(request, token)

@app.get("/feedback/place/{place_id}", tags=["Feedback"]) 
async def get_place_feedback(place_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_place_feedback_endpoint(place_id, token)

@app.get("/feedback/place/{place_id}/user/{user_id}", tags=["Feedback"])
async def get_user_place_feedback(place_id: str, user_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_user_place_feedback_endpoint(place_id, user_id, token)

@app.put("/feedback/place/{feedback_id}", tags=["Feedback"])
async def update_place_feedback(feedback_id: str, request: UpdatePlaceFeedbackRequest, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await update_place_feedback_endpoint(feedback_id, request, token)

@app.delete("/feedback/place/{feedback_id}", tags=["Feedback"])
async def delete_place_feedback(feedback_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await delete_place_feedback_endpoint(feedback_id, token)

@app.get("/feedback/place/{place_id}/stats", tags=["Feedback"])
async def get_place_feedback_stats(place_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_place_feedback_stats_endpoint(place_id, token)

# Route Feedback Endpoints
@app.post("/feedback/route", tags=["Feedback"])
async def submit_route_feedback(request: SubmitRouteFeedbackRequest, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await submit_route_feedback_endpoint(request, token)

@app.get("/feedback/route/{route_id}", tags=["Feedback"])
async def get_route_feedback(route_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_route_feedback_endpoint(route_id, token)

@app.get("/feedback/route/{route_id}/stats", tags=["Feedback"])
async def get_route_feedback_stats(route_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_route_feedback_stats_endpoint(route_id, token)

@app.put("/feedback/route/{feedback_id}", tags=["Feedback"])
async def update_route_feedback(feedback_id: str, request: UpdateRouteFeedbackRequest, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await update_route_feedback_endpoint(feedback_id, request, token)

@app.delete("/feedback/route/{feedback_id}", tags=["Feedback"])
async def delete_route_feedback(feedback_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await delete_route_feedback_endpoint(feedback_id, token)

@app.get("/feedback/route/{route_id}/user/{user_id}", tags=["Feedback"])
async def get_user_route_feedback(route_id: str, user_id: str, token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    return await get_user_route_feedback_endpoint(route_id, user_id, token)

# EMAIL VERIFICATION ENDPOINTS
@app.post("/user/sendVerification", tags=["User"])
async def send_verification(request: SendVerificationRequest):
    return await send_verification_email_endpoint(request)

@app.post("/user/sendVerification/verifyCode", tags=["User"])
async def verify_code(request: VerifyCodeRequest):
    return await verify_email_code_endpoint(request)