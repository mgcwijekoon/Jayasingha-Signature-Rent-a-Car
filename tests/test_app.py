"""Basic route tests: run with `python -m unittest discover -s tests`."""
from datetime import date, timedelta
import os
import tempfile
import unittest

import app as project_app


class JayasinghaAppTests(unittest.TestCase):
    def setUp(self):
        self.original_database = project_app.DATABASE
        self.temp_dir = tempfile.TemporaryDirectory()
        project_app.DATABASE = os.path.join(self.temp_dir.name, "test_bookings.db")
        project_app.app.config.update(TESTING=True)
        project_app.init_db()
        self.client = project_app.app.test_client()
        start = date.today() + timedelta(days=3)
        end = start + timedelta(days=2)
        self.pickup = start.isoformat()
        self.return_date = end.isoformat()
        self.booking_form = {
            "name": "Test Customer",
            "phone": "0771234567",
            "car": "Toyota Aqua",
            "pickup_location": "Negombo",
            "pickup": self.pickup,
            "pickup_time": "09:30",
            "return_date": self.return_date,
            "km": "120",
        }

    def tearDown(self):
        project_app.DATABASE = self.original_database
        self.temp_dir.cleanup()

    def test_home_and_fleet_pages_load(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/cars").status_code, 200)

    def test_smart_trip_planner_loads(self):
        response = self.client.get("/trip-planner")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your recommended vehicles", response.data)

    def test_available_car_can_be_checked(self):
        response = self.client.get(
            "/api/check-availability",
            query_string={
                "car": "Toyota Aqua",
                "pickup": self.pickup,
                "return_date": self.return_date,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["available"])

    def test_invalid_date_range_is_rejected(self):
        response = self.client.get(
            "/api/check-availability",
            query_string={
                "car": "Toyota Aqua",
                "pickup": self.pickup,
                "return_date": self.pickup,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["available"])

    def test_booking_is_saved_and_same_dates_become_unavailable(self):
        response = self.client.post("/booking", data=self.booking_form)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"submitted successfully", response.data)
        self.assertIn(b"https://wa.me/", response.data)

        availability = self.client.get(
            "/api/check-availability",
            query_string={
                "car": "Toyota Aqua",
                "pickup": self.pickup,
                "return_date": self.return_date,
            },
        )
        self.assertEqual(availability.status_code, 200)
        self.assertFalse(availability.get_json()["available"])

    def test_admin_login_is_required(self):
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)
        login = self.client.post(
            "/login", data={"username": "admin", "password": "12345"}
        )
        self.assertEqual(login.status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)


if __name__ == "__main__":
    unittest.main()
