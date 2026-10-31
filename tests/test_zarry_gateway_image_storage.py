import io
import unittest
from uuid import uuid4

from zarry_gateway.image_storage import CloudflareR2ImageStorage


class FakeS3:
    def __init__(self):
        self.calls = []
    def put_object(self, **kwargs):
        self.calls.append(kwargs)


class R2StorageTests(unittest.TestCase):
    def test_uploads_encoded_image_to_private_object_key_and_returns_https_url(self):
        client = FakeS3()
        storage = CloudflareR2ImageStorage(
            bucket="zarrry",
            public_base_url="https://pub-93af13628c2041bfb07c627e14b65ebe.r2.dev/",
            client=client,
        )
        class FakeImage:
            def save(self, buffer, format):
                self.assert_format = format
                buffer.write(b"PNGDATA")
        request_id = uuid4()
        url = storage.save(FakeImage(), request_id)
        self.assertTrue(url.startswith("https://pub-93af13628c2041bfb07c627e14b65ebe.r2.dev/zarry/"))
        self.assertTrue(url.endswith(".png"))
        self.assertEqual(len(client.calls), 1)
        upload = client.calls[0]
        self.assertEqual(upload["Bucket"], "zarrry")
        self.assertEqual(upload["Body"], b"PNGDATA")
        self.assertEqual(upload["ContentType"], "image/png")
        self.assertEqual(upload["CacheControl"], "public, max-age=31536000, immutable")
        self.assertEqual(upload["Metadata"]["request-id"], str(request_id))
        self.assertNotIn(str(request_id), upload["Key"])

    def test_rejects_non_https_public_url(self):
        with self.assertRaises(ValueError):
            CloudflareR2ImageStorage(bucket="images", public_base_url="http://images.example.com", client=FakeS3())

    def test_rejects_empty_bucket(self):
        with self.assertRaises(ValueError):
            CloudflareR2ImageStorage(bucket="", public_base_url="https://images.example.com", client=FakeS3())


if __name__ == "__main__":
    unittest.main()
