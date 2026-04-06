import os
import sys

import pytest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

import main
from src.tools import flight_tools


@pytest.fixture(autouse=True)
def reset_tool_state():
    flight_tools.reset_state()
    yield
    flight_tools.reset_state()


def test_load_tools_from_module():
    tools, issue = main.load_tools("src.tools.flight_tools")

    assert issue is None
    assert len(tools) == 4
    assert {tool["name"] for tool in tools} == {
        "search_flights",
        "book_flight",
        "get_weather",
        "get_baggage_policy",
    }


def test_search_and_book_flight_happy_path():
    result = flight_tools.search_flights("Hà Nội", "Sài Gòn", "2026-04-10")

    assert result["count"] == 2
    assert {flight["flight_id"] for flight in result["flights"]} == {"VN213", "VJ122"}

    booking = flight_tools.book_flight("VN213", "Nguyen Van A")

    assert booking["flight_id"] == "VN213"
    assert booking["passenger_name"] == "Nguyen Van A"
    assert booking["status"] == "confirmed"

    refreshed = flight_tools.search_flights("HAN", "SGN", "2026-04-10")
    vn213 = next(flight for flight in refreshed["flights"] if flight["flight_id"] == "VN213")
    assert vn213["available_seats"] == 4


def test_book_flight_raises_for_sold_out_flight():
    with pytest.raises(ValueError, match="sold out"):
        flight_tools.book_flight("VJ122", "Nguyen Van B")


def test_lookup_helpers_normalize_inputs():
    weather = flight_tools.get_weather("Sài Gòn")
    policy = flight_tools.get_baggage_policy("vn")

    assert weather["location"] == "SGN"
    assert weather["condition"] == "Sunny"
    assert policy["airline"] == "Vietnam Airlines"
    assert "23kg" in policy["policy"]
