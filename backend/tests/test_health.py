from django.test import Client, SimpleTestCase


class HealthTests(SimpleTestCase):
    def test_public_health_response_does_not_need_database(self):
        response = Client().get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_health_is_get_only(self):
        self.assertEqual(Client().post("/health/").status_code, 405)
