# imports
import googlemaps # https://googlemaps.github.io/google-maps-services-python/docs/index.html#googlemaps.Client.geocode
from google import genai
from google.genai import types

import time
import os
import json
import sqlite3

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Setup DB connection
db = sqlite3.connect("restaurants.db")
cursor = db.cursor()

# Enable Geocoding API and Places API in Google Cloud Console...
# Create the googlemaps API client
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)


# Get the desired information from the user
print("Welcome to Food Near U!")

# Get user inputs
geocode = None
while not geocode:
    location = input("Please enter your current location (street address, city, state): ")
    geocode = gmaps.geocode(location)
r = float(input("Please enter the radius to search in miles: ")) * 1609.34 # Convert miles to meters for Google Maps API


#Optionally, we can ask for type of food
food_type = input("What type of food are you looking for? (e.g., sushi, pizza, etc.) or enter to skip: ").strip().lower()
if not food_type:
    food_type = None

#Optionally we can ask for limit of results
limit = input("How many results would you like to see? (default is 60, press enter to skip): ").strip()
if not limit:
    limit = 60
else:
    limit = int(limit)

cursor.execute('''
    CREATE TABLE IF NOT EXISTS restaurants(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT,
               address TEXT,
               rating REAL,
               price_level TEXT)

''') # Address should be TEXT, not REAL? Because we input a string address or ZIP but want a street address stored
db.commit()

# Query the SQL database for results
# IF SUFFICIENT RESULTS, CONTINUE WITH THOSE RESULTS
# ELSE INSUFFICIENT RESULTS, QUERY GOOGLE MAPS API
# r is in meters, so we convert miles to meters (1 mile = 1609.34 meters)
places = gmaps.places_nearby(location=geocode[0]['geometry']['location'], radius=int(r), type='restaurant', keyword=food_type)

# Construct
results = places['results']
while 'next_page_token' in places:
    time.sleep(2)
    places = gmaps.places(page_token=places['next_page_token'])
    results.extend(places['results'])
restaurants = []
for place in results[:limit]:
    # json_data = json.dumps(place, indent=4)
    # print(json_data)
    name = place.get('name', 'No name available')
    address = place.get('vicinity') or place.get('formatted_address') or 'No address available' # Use 'vicinity' or 'formatted_address' if available
    rating = place.get('rating', 'N/A')
    price_level = place.get('price_level', 'No price level available')
    restaurants.append({
        'name': name,
        'address': address,
        'rating': rating,
        'price_level': price_level
    })
    db.execute('''
    INSERT INTO restaurants(name, address, rating, price_level) 
                VALUES (?, ?, ?, ?)
                ''', (name, address, rating, str(price_level)))

db.commit()
db.close()


# Construct output using Google GenAI
# Set environment variables
my_api_key = os.getenv('GENAI_KEY') 
client = genai.Client(api_key=my_api_key)

# Collect the responses
responses = []
for place in restaurants[:limit]:
    name = place.get('name', 'No name available')
    address = place.get('address') or 'No address available'
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            system_instruction="You are a travel advisor who clearly describes resteraunts briefly " \
            "highlighting the atmosphere, local popularity, and popular menu items." \
            "You will be given the resteraunt name and location"
        ),
        contents=f"Here is the data for the restaurant: Restaurant name: {name}, Address: {address}",
    )
    responses += [response.text]


# Print the output
if not restaurants:
    print("No restaurants found in the specified radius. Please try again with a larger radius.")
else:
    print("\n" + "-"*50 + "\n")
    print(f"Found {len(restaurants)} restaurants near {location} within {r / 1609.34:.2f} miles")
    print("\n" + "-"*50 + "\n")
    for i in range(min(limit, len(restaurants))):
        place = restaurants[i]
        name = place.get('name', 'No name available')
        address = place.get('address') or 'No address available' # Use 'vicinity' or 'formatted_address' if available
        rating = place.get('rating', 'N/A')
        price_level = place.get('price_level', 'No price level available')
        print(f"{i+1}) {name}")
        print(f"{address}  |  {rating}")
        if isinstance(price_level, int):
            price_lvl_str = "$" * price_level + "-" * (5 - price_level)
            print(f"Cost: {price_lvl_str}")
        else:
            print(f"Cost: {price_level}")
        print(f"\n{responses[i]}")
        print("\n" + "-"*50 + "\n")