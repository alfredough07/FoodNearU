# imports
import googlemaps # https://googlemaps.github.io/google-maps-services-python/docs/index.html#googlemaps.Client.geocode
import sqlite3
import time
import os
# Load environment variables
from dotenv import load_dotenv
load_dotenv()


#Enable Geocoding API and Places API in Google Cloud Console...
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


# Query the SQL database for results
# IF SUFFICIENT RESULTS, CONTINUE WITH THOSE RESULTS
# ELSE INSUFFICIENT RESULTS, QUERY GOOGLE MAPS API
# r is in meters, so we convert miles to meters (1 mile = 1609.34 meters)
places = gmaps.places(location=geocode[0]['geometry']['location'], radius=int(r), type='restaurant')

results = places['results']
if not results:
    print("No restaurants found in the specified radius. Please try again with a larger radius.")
else:
    print(f"Found {len(results)} restaurants near {location} within {r / 1609.34:.2f} miles")
    for place in results:
        name = place.get('name', 'No name available')
        address = place.get('vicinity') or place.get('formatted_address') or 'No address available' # Use 'vicinity' or 'formatted_address' if available
        print(f"Restaurant: {name}, Address: {address}")


while 'next_page_token' in places:

    time.sleep(2)
    places = gmaps.places(page_token=places['next_page_token'])
    results.extend(places['results'])
# Add results to SQL database


# Construct output using Google GenAI