import unittest
from unittest.mock import Mock, patch

from zarry_gateway.diagnostics import main, run_general_gateway_smoke


class GeneralGatewayStartupSmokeTests(unittest.TestCase):
    def test_fast_start_script_runs_smoke_after_health_check_in_background(self):
        from pathlib import Path
        script = (Path(__file__).resolve().parents[1] / "start.sh").read_text()
        self.assertIn("python -m zarry_gateway.diagnostics &", script)
        self.assertLess(script.index("wait_for_api"), script.index("python -m zarry_gateway.diagnostics &"))

    def test_module_entrypoint_constructs_provider_and_runs_smoke(self):
        provider = Mock()
        provider.base_url = "http://zarry.railway.internal:8080"
        provider.api_key = "test-secret"
        provider.generate.return_value = "ZARRY_CONNECTION_OK"
        with patch("zarry_gateway.providers.SelfHostedZarryProvider", return_value=provider):
            result = main()
        self.assertEqual(result, "passed")
        provider.generate.assert_called_once()

    def test_diagnostic_logger_emits_info_level_status(self):
        import logging
        logger = logging.getLogger("zarry_gateway.diagnostics")
        self.assertLessEqual(logger.getEffectiveLevel(), logging.INFO)

    def test_skips_when_provider_is_not_configured(self):
        provider = Mock()
        provider.base_url = ""
        provider.api_key = ""
        with self.assertLogs("zarry_gateway.diagnostics", level="WARNING") as logs:
            result = run_general_gateway_smoke(provider)
        self.assertIn("status=skipped", " ".join(logs.output))
        self.assertEqual(result, "skipped")
        provider.generate.assert_not_called()

    def test_runs_authenticated_provider_smoke_with_bounded_timeout(self):
        provider = Mock()
        provider.name = "self-hosted-zarry"
        provider.base_url = "http://zarry.railway.internal:8080"
        provider.api_key = "test-secret"
        provider.generate.return_value = "ZARRY_CONNECTION_OK"
        with patch("zarry_gateway.diagnostics.general_gateway_enabled", return_value=True):
            with self.assertLogs("zarry_gateway.diagnostics", level="INFO") as logs:
                result = run_general_gateway_smoke(provider)
        self.assertEqual(result, "passed")
        kwargs = provider.generate.call_args.kwargs
        self.assertEqual(kwargs["message"], "Reply with exactly: ZARRY_CONNECTION_OK.")
        self.assertEqual(kwargs["timeout"], (5.0, 180.0))
        self.assertIn("ZARRY_GENERAL_GATEWAY_SMOKE status=passed", " ".join(logs.output))
        self.assertIn("transport=railway_private", " ".join(logs.output))
        self.assertIn("public_chat_enabled=True", " ".join(logs.output))

    def test_failure_logs_only_exception_type(self):
        provider = Mock()
        provider.name = "self-hosted-zarry"
        provider.base_url = "https://zarry.example"
        provider.api_key = "test-secret"
        provider.generate.side_effect = RuntimeError("private-secret-must-not-be-logged")
        with self.assertLogs("zarry_gateway.diagnostics", level="ERROR") as logs:
            result = run_general_gateway_smoke(provider)
        self.assertEqual(result, "failed")
        joined = " ".join(logs.output)
        self.assertIn("error_type=RuntimeError", joined)
        self.assertNotIn("private-secret-must-not-be-logged", joined)


if __name__ == "__main__":
    unittest.main()
