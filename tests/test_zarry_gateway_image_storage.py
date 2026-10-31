import io
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from zarry_gateway.image_storage import CloudflareR2ImageStorage


class FakeS3:
    def __init__(self):
        self.calls = []
        self.objects = {}

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs):
        return {"Body": io.BytesIO(self.objects[(kwargs["Bucket"], kwargs["Key"])])}

    def delete_object(self, **kwargs):
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)


class R2StorageTests(unittest.TestCase):
    def test_uploads_encoded_image_to_private_object_key_and_returns_https_url(self):
        client = FakeS3()
        storage = CloudflareR2ImageStorage(
            bucket="zarrry",
            public_base_url="https://images.kingzarry.bid/",
            client=client,
        )
        class FakeImage:
            def save(self, buffer, format):
                self.assert_format = format
                buffer.write(b"PNGDATA")
        request_id = uuid4()
        url = storage.save(FakeImage(), request_id)
        self.assertTrue(url.startswith("https://images.kingzarry.bid/zarry/"))
        self.assertTrue(url.endswith(".png"))
        self.assertEqual(len(client.calls), 1)
        upload = client.calls[0]
        self.assertEqual(upload["Bucket"], "zarrry")
        self.assertEqual(upload["Body"], b"PNGDATA")
        self.assertEqual(upload["ContentType"], "image/png")
        self.assertEqual(upload["CacheControl"], "public, max-age=31536000, immutable")
        self.assertEqual(upload["Metadata"]["request-id"], str(request_id))
        self.assertNotIn(str(request_id), upload["Key"])

    def test_public_round_trip_uploads_reads_and_deletes_temporary_object(self):
        client = FakeS3()
        public_get = Mock(return_value=Mock(status_code=200, content=b"zarry-r2-probe"))
        storage = CloudflareR2ImageStorage(
            bucket="zarrry",
            public_base_url="https://images.kingzarry.bid",
            client=client,
            public_get=public_get,
        )
        result = storage.verify_public_round_trip()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["public_host"], "images.kingzarry.bid")
        public_get.assert_called_once()
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.objects, {})

    def test_public_round_trip_deletes_object_when_public_read_fails(self):
        client = FakeS3()
        public_get = Mock(side_effect=RuntimeError("DNS lookup failed"))
        storage = CloudflareR2ImageStorage(
            bucket="zarrry",
            public_base_url="https://images.kingzarry.bid",
            client=client,
            public_get=public_get,
        )
        with self.assertRaisesRegex(RuntimeError, "DNS lookup failed"):
            storage.verify_public_round_trip()
        self.assertEqual(client.objects, {})

    def test_rejects_non_https_public_url(self):
        with self.assertRaises(ValueError):
            CloudflareR2ImageStorage(bucket="images", public_base_url="http://images.example.com", client=FakeS3())

    def test_rejects_empty_bucket(self):
        with self.assertRaises(ValueError):
            CloudflareR2ImageStorage(bucket="", public_base_url="https://images.example.com", client=FakeS3())


if __name__ == "__main__":
    unittest.main()
