import copy
import json
import os
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "mock_db.json")
_STATE: Optional[Dict[str, Any]] = None


def _load_state() -> Dict[str, Any]:
    global _STATE
    if _STATE is None:
        with open(DB_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        payload["bookings"] = {}
        _STATE = payload
    return _STATE


def reset_state():
    """Reset in-memory bookings and seat counters for tests/demo reruns."""
    global _STATE
    _STATE = None


def _normalize_location(value: str) -> str:
    text = value.strip()
    aliases = {
        "ha noi": "HAN",
        "hanoi": "HAN",
        "hn": "HAN",
        "han": "HAN",
        "sai gon": "SGN",
        "saigon": "SGN",
        "ho chi minh": "SGN",
        "ho chi minh city": "SGN",
        "sgn": "SGN",
        "da nang": "DAD",
        "danang": "DAD",
        "dad": "DAD",
    }
    return aliases.get(text.lower(), text.upper())


def _normalize_airline_name(value: str) -> str:
    text = value.strip().lower()
    aliases = {
        "vn": "Vietnam Airlines",
        "vna": "Vietnam Airlines",
        "vietnam airlines": "Vietnam Airlines",
        "vj": "Vietjet Air",
        "vietjet": "Vietjet Air",
        "vietjet air": "Vietjet Air",
        "qh": "Bamboo Airways",
        "bamboo": "Bamboo Airways",
        "bamboo airways": "Bamboo Airways",
    }
    return aliases.get(text, value.strip())


def search_flights(origin: str, destination: str, date: str) -> Dict[str, Any]:
    state = _load_state()
    origin_code = _normalize_location(origin)
    destination_code = _normalize_location(destination)

    matches: List[Dict[str, Any]] = []
    for flight in state["flights"]:
        departure = datetime.fromisoformat(flight["departure_time"])
        if (
            flight["origin"] == origin_code
            and flight["destination"] == destination_code
            and departure.date().isoformat() == date
        ):
            matches.append(
                {
                    "flight_id": flight["flight_id"],
                    "airline": flight["airline"],
                    "origin": flight["origin"],
                    "destination": flight["destination"],
                    "departure_time": flight["departure_time"],
                    "price_usd": flight["price_usd"],
                    "available_seats": flight["available_seats"],
                }
            )

    return {
        "origin": origin_code,
        "destination": destination_code,
        "date": date,
        "count": len(matches),
        "flights": matches,
    }


def book_flight(
    flight_id: str,
    passenger_name: str,
    contact_info: Optional[str] = None,
) -> Dict[str, Any]:
    state = _load_state()
    flight = next(
        (item for item in state["flights"] if item["flight_id"].lower() == flight_id.strip().lower()),
        None,
    )
    if not flight:
        raise ValueError(f"Flight '{flight_id}' was not found.")

    if flight["available_seats"] <= 0:
        raise ValueError(f"Flight '{flight['flight_id']}' is sold out.")

    flight["available_seats"] -= 1
    pnr = _generate_pnr()
    booking = {
        "pnr": pnr,
        "flight_id": flight["flight_id"],
        "passenger_name": passenger_name,
        "contact_info": contact_info or "not_provided",
        "status": "confirmed",
    }
    state["bookings"][pnr] = booking

    return copy.deepcopy(booking)


def get_weather(location: str, date: Optional[str] = None) -> Dict[str, Any]:
    state = _load_state()
    location_code = _normalize_location(location)
    weather = state["weather"].get(location_code)
    if not weather:
        raise ValueError(f"No weather data found for '{location}'.")

    payload = copy.deepcopy(weather)
    payload["location"] = location_code
    if date:
        payload["date"] = date
    return payload


def get_baggage_policy(airline_name: str) -> Dict[str, Any]:
    state = _load_state()
    normalized_name = _normalize_airline_name(airline_name)
    policy = state["policies"].get(normalized_name)
    if not policy:
        raise ValueError(f"No baggage policy found for '{airline_name}'.")

    return {
        "airline": normalized_name,
        "policy": policy,
    }


def get_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "search_flights",
            "description": "Search available flights by origin, destination, and travel date.",
            "function": search_flights,
            "arg_schema": {
                "origin": "str",
                "destination": "str",
                "date": "YYYY-MM-DD",
            },
        },
        {
            "name": "book_flight",
            "description": "Book a flight by flight ID and passenger information.",
            "function": book_flight,
            "arg_schema": {
                "flight_id": "str",
                "passenger_name": "str",
                "contact_info": "Optional[str]",
            },
        },
        {
            "name": "get_weather",
            "description": "Look up destination weather by airport code or city name.",
            "function": get_weather,
            "arg_schema": {
                "location": "str",
                "date": "Optional[YYYY-MM-DD]",
            },
        },
        {
            "name": "get_baggage_policy",
            "description": "Retrieve baggage allowance policy by airline name.",
            "function": get_baggage_policy,
            "arg_schema": {
                "airline_name": "str",
            },
        },
    ]


def _generate_pnr(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    state = _load_state()
    while True:
        candidate = "".join(random.choice(alphabet) for _ in range(length))
        if candidate not in state["bookings"]:
            return candidate
