import googlemaps
import time

API_KEY = "AIzaSyB_LwvpZXu6EUZnDTkE5EudWwYwVSMvsw0"

# Construct a client with Nick's API key
gmaps = googlemaps.Client(key=API_KEY)


# Get inputs
geocode = gmaps.geocode(
    input("Please enter your current location (street address, cite, state): ")
)  # 411 N State St, Ann Arbor, MI
rad = float(input("Please enter the radius to search in miles: ")) * 1609.34

# Search for places near a location
# 'Restaurnt' is too selective as a type


places = gmaps.places(
    location=geocode[0]["geometry"]["location"], radius=rad, type="restaurant"
)
results = places["results"]
while "next_page_token" in places:
    time.sleep(2)
    places = gmaps.places(page_token=places["next_page_token"])
    results.extend(places["results"])


for result in results:
    print(result["name"])
