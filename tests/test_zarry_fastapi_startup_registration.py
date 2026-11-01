"""Regression coverage for FastAPI startup event registration in api.py."""
import ast
from pathlib import Path
import unittest


class ZarryStartupHookRegistrationTests(unittest.TestCase):
    def test_general_gateway_startup_hook_is_registered_on_router(self):
        source = Path(__file__).resolve().parents[1].joinpath("api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        registrations = [
            node for node in calls
            if isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_event_handler"
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "app"
            and node.func.value.attr == "router"
        ]
        self.assertTrue(
            any(
                len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "startup"
                and isinstance(node.args[1], ast.Name)
                and node.args[1].id == "_schedule_zarry_general_gateway_smoke"
                for node in registrations
            ),
            "ZARRY gateway smoke must be registered via app.router.add_event_handler",
        )

    def test_startup_inference_smoke_is_opt_in_to_avoid_blocking_chat(self):
        source = Path(__file__).resolve().parents[1].joinpath("api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_schedule_zarry_general_gateway_smoke"
        )
        calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
        guarded = any(
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "getenv"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "ZARRY_STARTUP_INFERENCE_SMOKE"
            and isinstance(node.args[1], ast.Constant)
            and str(node.args[1].value).lower() in {"false", "0", "no"}
            for node in calls
        )
        self.assertTrue(
            guarded,
            "Startup inference must be disabled by default; it shares the model lock with user chat.",
        )
