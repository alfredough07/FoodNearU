# imports
# Google Maps API docs:
# https://googlemaps.github.io/google-maps-services-python/
# docs/index.html#googlemaps.Client.geocode
import googlemaps
from google import genai
from google.genai import types
import textwrap
import time
import os
import json
import sqlite3
from dotenv import load_dotenv


def get_restaurants(
    gmaps, db, geocode: list, r: int, food_type: str, limit: int
) -> list:
    """
    Query the database first to get results defaulting
    to the Google Places API if not enough
    results are returned from the database.

    gmaps: the Google Maps Client object
    db: The local SQL database storing all of the restaurants
    geocode: The location of the user's search
    r: The search radius
    food_type: The type of food that the user is searching for
    limit: The number of results specified by the user

    Return: A list of restaurants matching the number
    specified by the user's limit
    """

    # Check cache

    # Extract zipcode and city from geocode
    city = zipcode = None
    cursor = db.cursor()
    location = geocode[0]["geometry"]["location"]
    geocode_info = gmaps.reverse_geocode((location["lat"], location["lng"]))
    if geocode_info:
        formatted = geocode_info[0].get("formatted_address", "No address available")
        geocode_parts = formatted.split(",")
        # print(geocode_parts) #['638 Uptown Blvd #120', ' Cedar Hill', ' TX
        # 75104', ' USA']
        if len(geocode_parts) >= 3:
            city = geocode_parts[-3].strip()
            # Get the last part of the second to last element
            zipcode = geocode_parts[-2].strip().split(" ")[-1]

    # Try to get restaurants from the database first
    if food_type:
        cursor.execute(
            """
                       SELECT DISTINCT
                        name, address, zipcode, city, rating, price_level
                         FROM restaurants
                         WHERE (zipcode = ? OR city = ?) AND keyword = ?
                         LIMIT ?
                       """,
            (zipcode, city, food_type, limit),
        )
    else:
        # If no food type is specified, just get all restaurants in the city
        # or zipcode
        cursor.execute(
            """
                       SELECT DISTINCT
                       name, address, zipcode, city, rating, price_level
                        FROM restaurants
                        WHERE (zipcode = ? OR city = ?) AND keyword IS NULL
                        LIMIT ?
                       """,
            (zipcode, city, limit),
        )
    cached = cursor.fetchall()
    restaurants = [
        {
            "name": row[0],
            "address": row[1],
            "zipcode": row[2],
            "city": row[3],
            "rating": row[4],
            "price_level": row[5],
        }
        for row in cached
    ]
    # List of tuples for existing restaurants to avoid duplicates
    # (name, address, zipcode)
    existing_restaurants = {
        (r["name"], r["address"], r["zipcode"]) for r in restaurants
    }
    # List of tuples for new restaurants
    new_restaurants = []
    num_cached = len(restaurants)
    if limit > 0 and num_cached > 0:
        print(f"Found {num_cached} restaurants in the database")
    if num_cached >= limit:
        return restaurants
    else:
        print(f"Fetching {limit - num_cached} places from Places API...\n")

    places = gmaps.places_nearby(
        location=geocode[0]["geometry"]["location"],
        radius=int(r),
        type="restaurant",
        keyword=food_type,
    )

    # Construct
    results = places["results"]
    while "next_page_token" in places:
        time.sleep(2)
        places = gmaps.places(page_token=places["next_page_token"])
        results.extend(places["results"])
    new_restaurants = []
    for place in results[:limit]:
        # json_data = json.dumps(place, indent=4)
        # print(json_data)
        name = place.get("name", "No name available")
        # Use 'vicinity' or 'formatted_address' if available
        address = (
            place.get("vicinity")
            or place.get("formatted_address")
            or "No address available"
        )
        if (name, address, zipcode) in existing_restaurants:
            continue
        else:

            existing_restaurants.add((name, address, zipcode))
        rating = place.get("rating", "N/A")
        price_level = place.get("price_level", "No price level available")
        # Get city and zipcode
        city = zipcode = None
        location = place["geometry"]["location"]
        geocode_info = gmaps.reverse_geocode((location["lat"], location["lng"]))
        if geocode_info:
            formatted = geocode_info[0].get("formatted_address", "No address available")
            geocode_parts = formatted.split(",")
            # print(geocode_parts) #['638 Uptown Blvd #120', ' Cedar Hill', '
            # TX 75104', ' USA']
            if len(geocode_parts) >= 3:
                city = geocode_parts[-3].strip()
                # Get the last part of the second to last element
                zipcode = geocode_parts[-2].strip().split(" ")[-1]
            else:
                print("Unexpected geocode format:", geocode_parts)
            # print(f"City: {city}, Zipcode: {zipcode}")
        # print(json.dumps(geocode_info, indent=4))
        new_restaurants.append(
            {
                "name": name,
                "address": address,
                "zipcode": zipcode,
                "city": city,
                "rating": rating,
                "price_level": price_level,
            }
        )
        cursor.execute(
            """
        INSERT OR IGNORE INTO
        restaurants(name, address, zipcode, city, rating, price_level, keyword)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (name, address, zipcode, city, rating, price_level, food_type),
        )
        if len(restaurants) + len(new_restaurants) >= limit:
            break
    db.commit()
    return restaurants + new_restaurants


def genAI_responses(limit: int, restaurants: list) -> list:
    """
    Collects the responses from the Google GenAI summary of the restaurants

    limit: The number of responses to output as defined by the user
    restaurants: The list of individual restaurants returned by the query

    Returns: A list of genAI summaries of the passed restaurants
    """
    # Construct output using Google GenAI
    # Set environment variables
    my_api_key = os.getenv("GENAI_KEY")
    client = genai.Client(api_key=my_api_key)

    # Collect the responses
    print(f"\nGenerating {min(limit, len(restaurants))} GenAI summaries...")
    responses = []
    for place in restaurants[:limit]:
        name = place.get("name", "No name available")
        address = place.get("address") or "No address available"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                system_instruction="You are a travel advisor who "
                "clearly describes restaurants briefly "
                "highlighting the atmosphere, "
                "local popularity, and popular menu items."
                "You will be given the restaurant name and location",
            ),
            contents=(
                f"Here is the data for the restaurant: "
                f"Restaurant name: {name}, Address: {address}"
            ),
        )
        responses += [response.text]
    return responses


def output(
    limit: int, restaurants: list, responses: list, location: str, r: float
) -> None:
    """
       Prints the returned restaurants from the user query
       limit: The number of responses to output as defined
    by the user
       restaurants: The list of individual restaurants returned by the query
    """

    # responses: The Google GenAI list of restaurant summaries    # Prints the
    # output
    with open("out.txt", "w") as out:
        if not restaurants:
            print("\nNo restaurants found in radius. Try with a larger radius")
            print("No restaurants found in radius. Try with a larger radius", file=out)
        else:
            print("\n" + "-" * 50 + "\n", file=out)
            print(
                f"Found {
                    len(restaurants)} restaurants near {location} within {
                    r /
                    1609.34: .2f} miles",
                file=out,
            )
            print("\n" + "-" * 50 + "\n", file=out)
            for i in range(min(limit, len(restaurants))):
                place = restaurants[i]
                name = place.get("name", "No name available")
                address = place.get("address", "No address available")
                rating = place.get("rating", "N/A")
                price_level = place.get("price_level", "No price level available")
                print(f"{i + 1}) {name}", file=out)
                print(f"{address}  |  {rating}", file=out)
                if isinstance(price_level, int):
                    price_lvl_str = "$" * price_level + "-" * (5 - price_level)
                    print(f"Cost: {price_lvl_str}", file=out)
                else:
                    print(f"Cost: {price_level}", file=out)
                print(f"\n{responses[i]}", file=out)
                print("\n" + "-" * 50 + "\n", file=out)


if __name__ == "__main__":
    load_dotenv()

    db = sqlite3.connect("restaurants.db")
    cursor = db.cursor()

    API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    gmaps = googlemaps.Client(key=API_KEY)

    print("Welcome to Food Near U!")
    geocode = None
    while not geocode:
        location = input(
            "Please enter your current location (street address, city, state): "
        )
        geocode = gmaps.geocode(location)

    r = float(input("Please enter the radius to search in miles: ")) * 1609.34

    prompt = "Food type? (e.g., sushi, pizza, etc or press enter to skip): "
    food_type = input(prompt).strip().lower() or None

    prompt = "How many results would you like? (default 60, press enter to skip): "
    limit_input = input(prompt).strip()
    limit = int(limit_input) if limit_input else 60

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurants(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, address TEXT, zipcode INTEGER,
            city TEXT, rating  REAL, price_level INTEGER,
            keyword TEXT,
            UNIQUE(name,address, zipcode)
        )
    """
    )
    db.commit()

    restaurants = get_restaurants(gmaps, db, geocode, r, food_type, limit)
    responses = genAI_responses(limit, restaurants)
    output(limit, restaurants, responses, location, r)
    db.close()
