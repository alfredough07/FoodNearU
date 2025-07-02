import unittest
from unittest.mock import MagicMock
from FoodNearU import get_restaurants, output


class TestFoodNearU(unittest.TestCase):
    def test_get_restaurants_returns_cached(self):
        gmaps = MagicMock()
        db = MagicMock()
        cursor = MagicMock()
        db.cursor.return_value = cursor

        gmaps.reverse_geocode.return_value = [
            {"formatted_address": "123 Main St, City, 12345, USA"}
        ]
        cursor.fetchall.return_value = [
            ("Test", "123 Main St", "12345", "City", 4.5, 2)
        ]

        geocode = [{"geometry": {"location": {"lat": 0, "lng": 0}}}]
        result = get_restaurants(gmaps, db, geocode, 0, "pizza", 0)
        self.assertEqual(result[0]["name"], "Test")

    def test_output_no_data(self):
        output(1, [], [], "Test City", 1609)
        print("\nOutput should indicate no restaurants found")
        with open("out.txt") as f:
            self.assertIn("No restaurants found", f.read())


if __name__ == "__main__":
    unittest.main()
