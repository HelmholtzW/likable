"""
Application settings loaded from environment variables.

This module handles loading and validation of environment variables
for the Likable application.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        """Initialize settings from environment variables."""

        self.model_id: str = os.getenv("MODEL_ID", "Qwen/Qwen2.5-Coder-32B-Instruct")
        self.api_base_url: str | None = os.getenv("API_BASE_URL")
        self.api_key: str | None = os.getenv("API_KEY")

        # Application Settings
        self.gradio_host: str = os.getenv("GRADIO_HOST", "127.0.0.1")
        self.gradio_port: int = int(os.getenv("GRADIO_PORT", "7860"))
        self.gradio_debug: bool = os.getenv("GRADIO_DEBUG", "false").lower() == "true"

        # Planning Agent Settings
        self.planning_verbosity: int = int(os.getenv("PLANNING_VERBOSITY", "1"))
        self.max_planning_steps: int = int(os.getenv("MAX_PLANNING_STEPS", "10"))

        # Validate critical settings
        self._validate()

    def _validate(self):
        """Validate critical settings and provide helpful error messages."""

        if not self.api_key:
            print("⚠️  Warning: API_KEY not set in environment variables.")
            print("   The planning agent may not work without a valid API key.")
            print("   Set it in your .env file or as an environment variable.")
            print()

        if self.planning_verbosity not in [0, 1, 2]:
            print(
                f"⚠️  Warning: PLANNING_VERBOSITY={self.planning_verbosity} is not \
in valid range [0, 1, 2]"
            )
            print("   Using default value of 1")
            self.planning_verbosity = 1

    def get_model_config(self) -> dict:
        """Get model configuration for the planning agent."""
        config = {"model_id": self.model_id, "api_key": self.api_key}

        if self.api_base_url:
            config["api_base_url"] = self.api_base_url
        if self.api_key:
            config["api_key"] = self.api_key

        return config

    def get_gradio_config(self) -> dict:
        """Get Gradio launch configuration."""
        return {
            "server_name": self.gradio_host,
            "server_port": self.gradio_port,
            "debug": self.gradio_debug,
        }

    def get_planning_config(self) -> dict:
        """Get planning agent configuration."""
        return {
            "verbosity_level": self.planning_verbosity,
            "max_steps": self.max_planning_steps,
        }

    def __repr__(self) -> str:
        """String representation of settings (excluding sensitive data)."""
        return f"""Settings(
    model_id='{self.model_id}',
    api_key={'***' if self.api_key else 'None'},
    api_base_url='{self.api_base_url}',
    gradio_host='{self.gradio_host}',
    gradio_port={self.gradio_port},
    gradio_debug={self.gradio_debug},
    planning_verbosity={self.planning_verbosity},
    max_planning_steps={self.max_planning_steps}
)"""


# Global settings instance
settings = Settings()


# Convenience functions for backward compatibility
def get_api_key() -> str | None:
    """Get API key."""
    return settings.api_key


def get_model_id() -> str:
    """Get model ID."""
    return settings.model_id


if __name__ == "__main__":
    print("Current Settings:")
    print("=" * 50)
    print(settings)
    print()
    print("Model Config:")
    print(settings.get_model_config())
    print()
    print("Gradio Config:")
    print(settings.get_gradio_config())
    print()
    print("Planning Config:")
    print(settings.get_planning_config())
