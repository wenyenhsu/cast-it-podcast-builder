"""Validate deployment environment configuration."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from infrastructure.deployment.env_validation import validate_environment


class Command(BaseCommand):
    """Fail early when required deployment settings are missing."""

    help = "Validate environment variables for the current deployment target."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--environment",
            default=None,
            help="Override ENVIRONMENT variable for validation.",
        )
        parser.add_argument(
            "--warn-only",
            action="store_true",
            help="Print warnings without raising on validation errors.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        environment = options.get("environment")
        strict = not options.get("warn_only", False)
        try:
            result = validate_environment(environment=environment, strict=strict)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(f"WARNING: {warning}"))
        if result.errors:
            for error in result.errors:
                self.stderr.write(self.style.ERROR(f"ERROR: {error}"))
            if strict:
                raise CommandError("Environment validation failed.")
        self.stdout.write(
            self.style.SUCCESS(f"Environment '{result.environment}' validation passed.")
        )
