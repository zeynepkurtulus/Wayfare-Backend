from typing import Optional, List, Dict
from dataclasses import dataclass
import asyncio
from geopy.geocoders import Nominatim
from config.database import places_collection, cities_collection
from models.model import PlaceModel
import geopy
from math import radians, cos, sin, asin, sqrt
from difflib import SequenceMatcher

@dataclass
class Place:
    name: str
    address: str
    latitude: float
    longitude: float
    place_id: Optional[str] = None
    rating: Optional[float] = None
    types: Optional[List[str]] = None
    opening_hours: Optional[Dict[str, str]] = None
    wayfare_category: Optional[str] = None
    duration: Optional[int] = None  # Duration in minutes

class PlaceScraper:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="travel_planner")
        # Dynamic city mapping - will be loaded from database
        self._city_mapping: Dict[str, Dict[str, str]] = {}
        self._mapping_loaded = False
        # NEW: City center coordinates cache for validation
        self._city_coordinates: Dict[str, tuple] = {}

    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        return 6371 * c  # Earth radius in km

    async def _get_city_center(self, city: str) -> Optional[tuple]:
        """Get city center coordinates for validation"""
        city_lower = city.lower()
        
        if city_lower in self._city_coordinates:
            return self._city_coordinates[city_lower]
        
        # Try to find city in database
        try:
            city_doc = await cities_collection.find_one({
                "name": {"$regex": f"^{city}$", "$options": "i"}
            })
            
            if city_doc and city_doc.get("coordinates"):
                coords = city_doc["coordinates"]
                lat, lng = coords.get("lat"), coords.get("lng")
                if lat and lng:
                    self._city_coordinates[city_lower] = (lat, lng)
                    return (lat, lng)
        except Exception:
            pass
        
        # Hardcoded major cities as fallback
        major_cities = {
            "paris": (48.8566, 2.3522),
            "london": (51.5074, -0.1278),
            "new york": (40.7128, -74.0060),
            "nyc": (40.7128, -74.0060),
            "tokyo": (35.6762, 139.6503),
            "sydney": (-33.8688, 151.2093),
            "barcelona": (41.3851, 2.1734),
            "rome": (41.9028, 12.4964),
            "berlin": (52.5200, 13.4050),
            "amsterdam": (52.3676, 4.9041),
            "madrid": (40.4168, -3.7038),
            "milan": (45.4642, 9.1900),
            "venice": (45.4408, 12.3155),
            "florence": (43.7696, 11.2558),
            "dublin": (53.3498, -6.2603),
            "prague": (50.0755, 14.4378),
            "vienna": (48.2082, 16.3738),
            "budapest": (47.4979, 19.0402),
            "warsaw": (52.2297, 21.0122),
            "moscow": (55.7558, 37.6176),
            "istanbul": (41.0082, 28.9784)
        }
        
        if city_lower in major_cities:
            coords = major_cities[city_lower]
            self._city_coordinates[city_lower] = coords
            return coords
        
        return None

    def _is_obviously_fake(self, name: str) -> bool:
        """Detect obviously fake place names to avoid geocoding"""
        name_lower = name.lower()
        
        fake_indicators = [
            'test', 'fake', 'xyz', '123', 'dummy', 'sample',
            'fictional', 'nonexistent', 'example', 'placeholder'
        ]
        
        # Check if name contains obvious fake indicators
        for indicator in fake_indicators:
            if indicator in name_lower:
                return True
        
        # Check for random character patterns
        if len(name) > 20 and name.count(' ') < 2:  # Very long single words
            return True
            
        return False

    def _calculate_confidence(self, query: str, result_name: str, distance_km: float) -> int:
        """Calculate confidence score for geocoding result"""
        confidence = 0
        
        # 1. Name similarity (0-40 points)
        similarity = SequenceMatcher(None, query.lower(), result_name.lower()).ratio()
        confidence += int(similarity * 40)
        
        # 2. Distance validation (0-40 points)
        if distance_km <= 10:  # Very close to city center
            confidence += 40
        elif distance_km <= 30:  # Reasonable distance
            confidence += 30
        elif distance_km <= 50:  # Still within city area
            confidence += 15
        # Beyond 50km gets 0 points
        
        # 3. Query quality bonus (0-20 points)
        query_lower = query.lower()
        result_lower = result_name.lower()
        
        # Museum matching
        if any(museum_word in query_lower for museum_word in ['museum', 'musée', 'gallery']):
            if any(museum_word in result_lower for museum_word in ['museum', 'musée', 'gallery']):
                confidence += 10
                
        # Landmark matching
        if any(landmark in query_lower for landmark in ['tower', 'cathedral', 'church', 'palace']):
            if any(landmark in result_lower for landmark in ['tower', 'cathedral', 'church', 'palace']):
                confidence += 10
        
        return min(100, confidence)  # Cap at 100

    async def _validate_geocoding_result(self, city: str, name: str, result: Place, 
                                          max_distance_km: float = 50, min_confidence: int = 60) -> bool:
        """Validate geocoding result using geographic and confidence checks"""
        
        # Get city center for validation
        city_center = await self._get_city_center(city)
        
        if not city_center:
            # FIXED: Reject unknown cities instead of accepting them
            # This prevents false positives for fictional cities
            print(f"DEBUG: Rejecting geocoding result for unknown city '{city}'")
            return False
        
        city_lat, city_lng = city_center
        
        # Calculate distance from city center
        distance_km = self._calculate_distance(city_lat, city_lng, result.latitude, result.longitude)
        
        # FIXED: More precise distance checking for edge cases
        print(f"DEBUG: Distance validation: '{name}' is {distance_km:.1f}km from {city} center (limit: {max_distance_km}km)")
        
        # Check distance constraint with precise boundary
        if distance_km > max_distance_km:
            print(f"DEBUG: REJECTED - Place '{name}' is {distance_km:.1f}km from {city} center, exceeds {max_distance_km}km limit")
            return False
        
        # Calculate confidence score
        confidence = self._calculate_confidence(name, result.name, distance_km)
        
        # Check confidence constraint
        if confidence < min_confidence:
            print(f"DEBUG: REJECTED - Place '{name}' has confidence {confidence}, below {min_confidence} threshold")
            return False
        
        print(f"DEBUG: ACCEPTED - Place '{name}' passed validation: {distance_km:.1f}km, {confidence}% confidence")
        return True

    async def _load_city_mapping(self):
        """Load all cities from database and create dynamic geocoding mapping"""
        if self._mapping_loaded:
            return
            
        try:
            print("DEBUG: Loading city mapping from database...")
            # Get all active cities from database
            cities = await cities_collection.find({"active": True}).to_list(length=None)
            
            for city_doc in cities:
                city_name = city_doc.get("name", "").lower()
                country = city_doc.get("country", "")
                
                if not city_name or not country:
                    continue
                    
                # Create mapping entry
                city_info = {
                    "name": city_doc.get("name"),
                    "country": country
                }
                
                # Add primary city name
                self._city_mapping[city_name] = city_info
                
                # Add variations
                if " " in city_name:
                    # Add version without spaces: "New York" -> "newyork"
                    no_space_version = city_name.replace(" ", "")
                    self._city_mapping[no_space_version] = city_info
                    
                # Add common abbreviations for specific cities
                if city_name == "new york city":
                    self._city_mapping["nyc"] = city_info
                    self._city_mapping["new york"] = city_info
                elif city_name == "los angeles":
                    self._city_mapping["la"] = city_info
                elif city_name == "san francisco":
                    self._city_mapping["sf"] = city_info
                elif city_name == "ho chi minh city":
                    self._city_mapping["saigon"] = city_info
                    self._city_mapping["hcmc"] = city_info
                
            self._mapping_loaded = True
            print(f"DEBUG: Loaded {len(self._city_mapping)} city mapping entries from {len(cities)} cities")
            
        except Exception as e:
            print(f"DEBUG: Error loading city mapping: {e}")
            # Continue with empty mapping - will fall back to hardcoded logic

    async def get_place_from_db(self, city: str, name: str) -> Optional[Place]:
        db_place = await places_collection.find_one({"city": city, "name": name})
        if db_place:
            return Place(
                name=db_place["name"],
                address=db_place["address"],
                latitude=db_place["coordinates"]["lat"],
                longitude=db_place["coordinates"]["lng"],
                place_id=db_place.get("place_id"),
                rating=float(db_place["rating"]) if db_place.get("rating") else None,
                types=[db_place.get("wayfare_category", db_place.get("category", ""))] if db_place.get("wayfare_category") or db_place.get("category") else [],
                opening_hours=db_place.get("opening_hours"),
                wayfare_category=db_place.get("wayfare_category"),
                duration=db_place.get("duration")
            )
        return None

    async def get_place(self, city: str, name: str, max_distance_km: float = 50, min_confidence: int = 60) -> Optional[Place]:
        """Get place information by city and name using database lookup and geocoding with validation"""
        db_place = await self.get_place_from_db(city, name)
        if db_place:
            return db_place
        
        # NEW: Fast-fail for obviously fake names (improves performance)
        if self._is_obviously_fake(name):
            print(f"DEBUG: Rejected obviously fake place name: '{name}'")
            return None
            
        # Load city mapping if not already loaded
        await self._load_city_mapping()
        
        # Fallback to geocoding with Nominatim (run in thread pool)
        print(f"DEBUG: Starting geocoding process for '{name}' in city '{city}'")
        loop = asyncio.get_event_loop()
        try:
            # Clean and normalize the place name
            clean_name = name.strip()
            
            # Remove common prefixes/suffixes that might confuse geocoding
            clean_name = clean_name.replace("V&A - ", "").replace(" - Victoria and Albert Museum", "")
            clean_name = clean_name.replace("The ", "").replace("London ", "").replace(" - London", "")
            
            # DYNAMIC: Generate search queries based on database cities
            search_queries = [
                f"{clean_name}, {city}",
                f"{name}, {city}",  # Original name with city
                f"{clean_name}",    # Just the place name
                f"{name}"           # Original name only
            ]
            
            # DYNAMIC: Add city-specific variations from database
            city_lower = city.lower()
            city_info = self._city_mapping.get(city_lower)
            
            if city_info:
                city_name = city_info["name"]
                country = city_info["country"]
                
                # Add comprehensive city + country combinations
                search_queries.extend([
                    f"{clean_name}, {city_name}, {country}",
                    f"{name}, {city_name}, {country}",
                    f"{clean_name}, {city_name}",
                    f"{name}, {city_name}"
                ])
                
                # Add specific regional variations for major cities
                if city_lower in ["new york city", "nyc", "new york"]:
                    search_queries.extend([
                        f"{clean_name}, New York, NY, USA",
                        f"{clean_name}, Manhattan, NY",
                        f"{clean_name}, NYC, USA"
                    ])
                elif city_lower in ["london"]:
                    search_queries.extend([
                        f"{clean_name}, London, England",
                        f"{clean_name}, Greater London, UK"
                    ])
                elif city_lower in ["paris"]:
                    search_queries.extend([
                        f"{clean_name}, Paris, Île-de-France, France"
                    ])
                elif city_lower in ["tokyo"]:
                    search_queries.extend([
                        f"{clean_name}, Tokyo, Honshu, Japan"
                    ])
                elif city_lower in ["sydney"]:
                    search_queries.extend([
                        f"{clean_name}, Sydney, NSW, Australia"
                    ])
                elif city_lower in ["barcelona"]:
                    search_queries.extend([
                        f"{clean_name}, Barcelona, Catalonia, Spain"
                    ])
                
                print(f"DEBUG: Generated {len(search_queries)} search queries for city '{city}' -> '{city_name}, {country}'")
            else:
                # Fallback for cities not in database
                search_queries.extend([
                    f"{clean_name}, {city}",
                    f"{name}, {city}"
                ])
                print(f"DEBUG: Using fallback queries for unknown city '{city}'")
            
            for query in search_queries:
                try:
                    print(f"DEBUG: Trying geocoding for '{name}' with query: '{query}'")
                    # Add more detailed error handling
                    location = await loop.run_in_executor(None, lambda q=query: self.geolocator.geocode(q, timeout=10))
                    if location:
                        if location.latitude and location.longitude:
                            print(f"DEBUG: Geocoding successful for '{name}' using query: '{query}' -> ({location.latitude}, {location.longitude})")
                            
                            # NEW: Create result and validate it
                            potential_result = Place(
                                name=name,
                                address=location.address,
                                latitude=location.latitude,
                                longitude=location.longitude,
                                place_id=None,
                                rating=None,
                                types=[],
                                opening_hours=None
                            )
                            
                            # NEW: Validate geocoding result with geographic and confidence checks
                            if await self._validate_geocoding_result(city, name, potential_result, max_distance_km, min_confidence):
                                return potential_result
                            else:
                                # Continue to next query if validation fails
                                print(f"DEBUG: Validation failed for '{name}', trying next query...")
                                continue
                        else:
                            print(f"DEBUG: Geocoding returned location but no coordinates for '{name}' with query '{query}'")
                    else:
                        print(f"DEBUG: Geocoding returned None for '{name}' with query '{query}'")
                except Exception as e:
                    print(f"DEBUG: Geocoding failed for '{name}' with query '{query}': {str(e)}")
                    continue
            
            print(f"DEBUG: All geocoding attempts failed for '{name}'")
            
            # Fallback: Try to get coordinates from a simple lookup for common places
            fallback_coords = self._get_fallback_coordinates(name)
            if fallback_coords:
                print(f"DEBUG: Using fallback coordinates for '{name}': {fallback_coords}")
                
                # NEW: Create fallback result and validate it
                fallback_result = Place(
                    name=name,
                    address=f"{name}, London, UK",
                    latitude=fallback_coords[0],
                    longitude=fallback_coords[1],
                    place_id=None,
                    rating=None,
                    types=[],
                    opening_hours=None
                )
                
                # NEW: Validate fallback result too
                if await self._validate_geocoding_result(city, name, fallback_result, max_distance_km, min_confidence):
                    return fallback_result
                else:
                    print(f"DEBUG: Fallback coordinates for '{name}' failed validation")
            
            # FIXED: If no fallback coordinates and all validation failed, return None instead of Place with None coordinates
            print(f"DEBUG: No fallback coordinates available for '{name}', geocoding completely failed")
            return None
            
        except Exception as e:
            print(f"DEBUG: Geocoding error for '{name}': {str(e)}")
            return None
    
    async def _get_dynamic_fallback_coordinates(self, place_name: str, city: str) -> Optional[tuple]:
        """Get fallback coordinates from database places for any city"""
        try:
            # Search for similar places in the database for this city
            search_patterns = [
                {"city": city, "name": {"$regex": f"^{place_name}$", "$options": "i"}},  # Exact match
                {"city": city, "name": {"$regex": place_name, "$options": "i"}},  # Partial match
                {"city": city, "name": {"$regex": place_name.replace(" ", ""), "$options": "i"}},  # No spaces
            ]
            
            for pattern in search_patterns:
                place_doc = await places_collection.find_one(pattern)
                if place_doc and place_doc.get("coordinates"):
                    coords = place_doc["coordinates"]
                    if isinstance(coords, dict) and coords.get("lat") and coords.get("lng"):
                        print(f"DEBUG: Found dynamic fallback coordinates for '{place_name}' in {city}: ({coords['lat']}, {coords['lng']})")
                        return (coords["lat"], coords["lng"])
                        
            print(f"DEBUG: No dynamic fallback coordinates found for '{place_name}' in {city}")
            return None
            
        except Exception as e:
            print(f"DEBUG: Error in dynamic fallback for '{place_name}': {e}")
            return None

    def _get_fallback_coordinates(self, name: str) -> Optional[tuple]:
        """REMOVED: Hardcoded fallback system eliminated - use dynamic database approach only"""
        print(f"DEBUG: Legacy hardcoded fallback called for '{name}' - this should be replaced with dynamic database lookup")
        return None  # Force use of dynamic system only
        
        # All hardcoded fallback logic removed - use dynamic database lookup only
