"""
Application configuration using pydantic-settings.

All configuration is loaded from environment variables with sensible defaults.
For production, set environment variables or use a .env file.
"""

import secrets
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "development"
    debug: bool = True

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # Database
    database_url: str = "sqlite:///./app.db"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 5
    rate_limit_api_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret is not weak in production."""
        if os.getenv('ENVIRONMENT', 'development') == 'production':
            weak_secrets = [
                'supersecretkey', 'secret', 'password', 'changeme',
                'jwt_secret', 'your-secret-key', 'secret_key'
            ]
            if v.lower() in weak_secrets or len(v) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be at least 32 characters and not a "
                    "common weak secret in production environment"
                )
        return v

    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        """Ensure CORS origins are properly formatted."""
        return v

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into a list."""
        origins = [origin.strip() for origin in self.cors_origins.split(',')]
        return [origin for origin in origins if origin]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create settings instance
# Note: In production, ensure .env file exists or environment variables are set
def get_settings() -> Settings:
    """Get application settings, with fallback for development."""
    try:
        return Settings()
    except Exception as e:
        # If JWT_SECRET_KEY is not set, generate one for development
        if os.getenv('ENVIRONMENT', 'development') == 'development':
            print(f"Warning: Using generated JWT secret for development: {e}")
            return Settings(
                jwt_secret_key=secrets.token_urlsafe(32),
                environment='development'
            )
        raise


settings = get_settings()