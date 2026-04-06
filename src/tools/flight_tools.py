import json
import os
import random
import string
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), 'mock_db.json')

def load_db() -> Dict[str, Any]:
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"flights": [], "weather": {}, "policies": {}, "bookings": {}}

def save_db(data: Dict[str, Any]):
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def search_flights(origin: str, destination: str, date: str) -> str:
    """
    Search for available flights based on origin, destination and date.
    """
    db = load_db()
    flights = db.get("flights", [])
    
    # In a real app we'd filter by date, but for mock db we filter mainly by origin/destination
    available = []
    for f in flights:
        if f["origin"].upper() == origin.upper() and f["destination"].upper() == destination.upper():
            available.append(f"Flight {f['flight_id']} ({f['airline']}): {f['departure_time']}, {f['price_usd']} USD, {f['available_seats']} seats left.")
            
    if not available:
        return f"No flights found from {origin} to {destination} on {date}."
    return "Available flights:\n" + "\n".join(available)

def book_flight(flight_id: str, passenger_name: str) -> str:
    """
    Book a flight using flight_id and passenger_name.
    """
    db = load_db()
    flights = db.get("flights", [])
    
    for f in flights:
        if f["flight_id"].upper() == flight_id.upper():
            if f["available_seats"] <= 0:
                return f"Error: Flight {flight_id} is fully booked."
            
            # Decrease seat count
            f["available_seats"] -= 1
            
            # Generate random PNR
            pnr = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Save booking
            db.setdefault("bookings", {})[pnr] = {
                "flight_id": f["flight_id"],
                "passenger": passenger_name,
                "status": "CONFIRMED"
            }
            save_db(db)
            return f"Successfully booked {flight_id} for {passenger_name}. Booking Reference PNR: {pnr}."
            
    return f"Error: Flight ID {flight_id} not found."

def get_weather(location: str) -> str:
    """
    Get weather information for a specific location (airport code).
    """
    db = load_db()
    weather = db.get("weather", {})
    loc_code = location.upper()
    
    if loc_code in weather:
        w = weather[loc_code]
        return f"Weather in {loc_code}: {w['condition']}, {w['temperature_c']}°C"
    
    return f"No weather data available for {location}."

def get_baggage_policy(airline: str) -> str:
    """
    Get baggage policy for a specific airline.
    """
    db = load_db()
    policies = db.get("policies", {})
    
    for key in policies:
        # Simple string matching
        if airline.lower() in key.lower():
            return f"{key} baggage policy: {policies[key]}"
            
    return f"No baggage policy found for airline '{airline}'."

def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Returns the schema of tools to be injected into the ReAct Agent's system prompt.
    """
    return [
        {
            "name": "search_flights",
            "description": "Tìm kiếm chuyến bay. Arguments format: origin, destination, date. Example: HAN, SGN, 2026-04-10"
        },
        {
            "name": "book_flight",
            "description": "Đặt vé máy bay. Arguments format: flight_id, passenger_name. Example: VN213, Nguyen Van A"
        },
        {
            "name": "get_weather",
            "description": "Kiểm tra thời tiết tại điểm đến. Arguments format: location_code. Example: SGN"
        },
        {
            "name": "get_baggage_policy",
            "description": "Kiểm tra chính sách hành lý của hãng bay. Arguments format: airline_name. Example: Vietnam Airlines"
        }
    ]
