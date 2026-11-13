from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Overall health state")
    app_name: str = Field(default="Ruby", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment mode")
    database_connected: bool = Field(default=True, description="Database connection health")
    storage_accessible: bool = Field(default=True, description="Storage filesystem access")
    data_directory: str = Field(..., description="Configured data directory path")
    timestamp: datetime = Field(..., description="Current server time (UTC)")
