#!/usr/bin/env python3
"""
Tests for __main__ module.

Tests for CLI entry point.
"""

from __future__ import annotations

from unittest.mock import patch


class TestMainModule:
    """Tests for __main__ module."""

    def test_main_function_exists(self) -> None:
        """Test that main function exists and is callable."""
        from tmt_quantum_vault.__main__ import main

        assert callable(main)

    def test_main_calls_app(self) -> None:
        """Test that main calls app."""
        from tmt_quantum_vault.__main__ import main

        with patch("tmt_quantum_vault.__main__.app") as mock_app:
            main()
            mock_app.assert_called_once()

    def test_main_module_imports(self) -> None:
        """Test that __main__ module can be imported."""
        import tmt_quantum_vault.__main__

        assert hasattr(tmt_quantum_vault.__main__, "main")
        assert hasattr(tmt_quantum_vault.__main__, "app")


class TestMainEntrypoint:
    """Tests for main entry point behavior."""

    def test_main_with_no_args(self) -> None:
        """Test main with no arguments."""
        from tmt_quantum_vault.__main__ import main

        with patch("tmt_quantum_vault.__main__.app") as mock_app:
            main()
            # App should be called with no arguments
            mock_app.assert_called_once()

    def test_main_returns_none(self) -> None:
        """Test that main returns None."""
        from tmt_quantum_vault.__main__ import main

        with patch("tmt_quantum_vault.__main__.app"):
            result = main()

            # main() doesn't explicitly return anything, so it returns None
            assert result is None
