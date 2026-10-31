import unittest
from uuid import UUID
from pydantic import ValidationError
from zarry_gateway.schemas import AssistantRequest, AssistantResponse, ImageRequest, ImageResponse
class GatewayContractTests(unittest.TestCase):
    def test_assistant_request_generates_request_id(self): self.assertIsInstance(AssistantRequest(message="hello").request_id, UUID)
    def test_assistant_request_rejects_unknown_fields(self):
        with self.assertRaises(ValidationError): AssistantRequest(message="hello", user_id="spoofed")
    def test_assistant_request_rejects_oversized_message(self):
        with self.assertRaises(ValidationError): AssistantRequest(message="x" * 8001)
    def test_assistant_response_requires_trace_and_conversation_ids(self):
        with self.assertRaises(ValidationError): AssistantResponse(response="ok", provider="local")
    def test_image_prompt_is_bounded_and_extra_fields_rejected(self):
        with self.assertRaises(ValidationError): ImageRequest(prompt="x" * 2001)
        with self.assertRaises(ValidationError): ImageRequest(prompt="sunset", user_id="spoofed")
    def test_image_response_requires_reference(self):
        with self.assertRaises(ValidationError): ImageResponse(provider="hf")
if __name__ == "__main__": unittest.main()
