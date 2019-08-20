from django.test import override_settings, SimpleTestCase


@override_settings(ROOT_URLCONF='view_tests.generic_urls')
class AsyncViewsTests(SimpleTestCase):

    def test_simple_async_view(self):
        response = self.client.get('/async/simple/')
        self.assertEqual(response.status_code, 200)

    def test_async_class_view(self):
        response = self.client.get('/async/class/')
        self.assertEqual(response.status_code, 200)

    def test_async_custom_class_view(self):
        response = self.client.get('/async/custom_class/')
        self.assertEqual(response.status_code, 200)
