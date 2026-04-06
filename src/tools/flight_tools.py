import json
import os
import random
import string
from typing import List, Dict, Any

# Load mock database (relative to this file)
BASE_DIR = os.path.dirname(__file__)
MOCK_DB_PATH = os.path.join(BASE_DIR, "mock_db.json")
with open(MOCK_DB_PATH, "r", encoding="utf-8") as f:
    MOCK_DB = json.load(f)

def _generate_booking_code() -> str:
    """Generate a random 6‑character alphanumeric booking reference (PNR)."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

def search_flights(origin: str, destination: str, date: str) -> List[Dict[str, Any]]:
    """Return a list of flights matching origin, destination and (approximate) date.
    The mock DB only stores a fixed departure_time; we simply check the date prefix.
    """
    matches = []
    for flight in MOCK_DB.get("flights", []):
        if (
            flight["origin"].upper() == origin.upper()
            and flight["destination"].upper() == destination.upper()
            and flight["departure_time"].startswith(date)
        ):
            matches.append(flight)
    return matches

def book_flight(flight_id: str, passenger_name: str, contact_info: str = "") -> str:
    """Attempt to book a seat on the given flight.
    If the flight has available seats, decrement the count and store a booking entry.
    Returns the generated booking code (PNR) or an error message.
    """
    for flight in MOCK_DB.get("flights", []):
        if flight["flight_id"] == flight_id:
            if flight["available_seats"] <= 0:
                return f"Error: Flight {flight_id} has no available seats."
            # Decrease seat count
            flight["available_seats"] -= 1
            pnr = _generate_booking_code()
            MOCK_DB.setdefault("bookings", {})[pnr] = {
                "flight_id": flight_id,
                "passenger_name": passenger_name,
                "contact_info": contact_info,
            }
            # Persist the change back to the JSON file (optional for demo)
            with open(MOCK_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(MOCK_DB, f, ensure_ascii=False, indent=2)
            return f"Booking successful. PNR: {pnr}"
    return f"Error: Flight {flight_id} not found."

def get_weather(location: str, date: str = "") -> Dict[str, Any]:
    """Return mock weather information for a given airport code.
    The `date` argument is ignored in the mock implementation.
    """
    weather = MOCK_DB.get("weather", {})
    return weather.get(location.upper(), {"condition": "Unknown", "temperature_c": None})

def get_baggage_policy(airline_code: str) -> str:
    """Return the baggage policy string for the specified airline.
    """
    policies = MOCK_DB.get("policies", {})
    return policies.get(airline_code, "Policy not found for this airline.")

# Helper to expose tool metadata for the ReActAgent
FLIGHT_TOOLS = [
    {
        "name": "search_flights",
        "description": "Search available flights given origin, destination and date (YYYY-MM-DD). Returns a list of flight objects.",
        "function": search_flights,
    },
    {
        "name": "book_flight",
        "description": "Book a seat on a flight using flight_id, passenger_name and optional contact_info. Returns a booking reference (PNR) or error.",
        "function": book_flight,
    },
    {
        "name": "get_weather",
        "description": "Get weather forecast for an airport code (e.g., SGN). Returns condition and temperature.",
        "function": get_weather,
    },
    {
        "name": "get_baggage_policy",
        "description": "Retrieve baggage allowance policy for a given airline name.",
        "function": get_baggage_policy,
    },
]
