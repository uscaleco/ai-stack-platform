from pydantic import BaseModel
from typing import Optional

class DeploymentRequest(BaseModel):
    template_id: str
    payment_method_id: str

class SubscriptionRequest(BaseModel):
    plan_type: str
    payment_method_id: str

class DeploymentResponse(BaseModel):
    deployment_id: str
    url: str
    status: str
    subscription_id: str

class UserProfile(BaseModel):
    user_id: str
    email: str
    created_at: Optional[str] = None
    subscription_count: int = 0
    deployment_count: int = 0

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str 