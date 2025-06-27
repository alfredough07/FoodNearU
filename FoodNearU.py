# imports
import googlemaps # https://googlemaps.github.io/google-maps-services-python/docs/index.html#googlemaps.Client.geocode
import sqlite3
import time


# Create the googlemaps API client
API_KEY = "AIzaSyB_LwvpZXu6EUZnDTkE5EudWwYwVSMvsw0"
gmaps = googlemaps.Client(key=API_KEY)


# Get the desired information from the user
print("Welcome to Food Near U!")

# Get user inputs
geocode = None
while not geocode:
    location = input("Please enter your current location (street address, cite, state): ")
    geocode = gmaps.geocode(input(location))
r = float(input("Please enter the radius to search in miles: ")) * 1609.34


# Query the SQL database for results
# IF SUFFICIENT RESULTS, CONTINUE WITH THOSE RESULTS
# ELSE INSUFFICIENT RESULTS, QUERY GOOGLE MAPS API
places = gmaps.places(location=geocode[0]['geometry']['location'], radius=r, type='restaurant')
results = places['results']
while 'next_page_token' in places:
    time.sleep(2)
    places = gmaps.places(page_token=places['next_page_token'])
    results.extend(places['results'])
# Add results to SQL database


# Construct output using Google GenAI