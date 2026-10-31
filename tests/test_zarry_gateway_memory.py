import unittest
from uuid import uuid4
from unittest.mock import Mock

from zarry_gateway.identity import AuthenticatedPrincipal
from zarry_gateway.schemas import AssistantRequest
from zarry_gateway.service import AssistantService


class MemoryServiceTests(unittest.TestCase):
    def test_opted_out_user_is_not_read_or_written(self):
        memory = Mock()
        memory.is_enabled.return_value = False
        provider = Mock()
        provider.name = "self-hosted-zarry"
        provider.generate.return_value = "Answer"
        service = AssistantService(provider, memory_store=memory)
        principal = AuthenticatedPrincipal("web:user-1", "web", "user-1")
        service.chat(principal=principal, payload=AssistantRequest(message="Hello"))
        memory.get_history.assert_not_called()
        memory.append_turn.assert_not_called()

    def test_opted_in_user_gets_only_own_conversation_history_and_turn_saved(self):
        conversation_id = uuid4()
        memory = Mock()
        memory.is_enabled.return_value = True
        memory.get_history.return_value = [{"role": "user", "content": "Earlier question"}]
        provider = Mock()
        provider.name = "self-hosted-zarry"
        provider.generate.return_value = "Answer"
        service = AssistantService(provider, memory_store=memory)
        principal = AuthenticatedPrincipal("web:user-1", "web", "user-1")
        service.chat(principal=principal, payload=AssistantRequest(message="Follow up", conversation_id=conversation_id))
        memory.get_history.assert_called_once_with(principal, conversation_id, limit=12)
        provider.generate.assert_called_once()
        self.assertEqual(provider.generate.call_args.kwargs["messages"][0]["content"], "Earlier question")
        memory.append_turn.assert_called_once()
        self.assertEqual(memory.append_turn.call_args.kwargs["conversation_id"], conversation_id)


if __name__ == "__main__":
    unittest.main()
