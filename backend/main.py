# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import stripe
import digitalocean
import os
import uuid
import subprocess
from typing import Dict, List, Optional
from datetime import datetime
import time
from config import config, db_client
from auth import get_current_user, get_current_user_id, rate_limit
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI-Stack Deploy API", 
    version="1.0.0",
    description="Deploy AI applications in seconds",
    docs_url="/docs" if config.environment != "production" else None,
    redoc_url="/redoc" if config.environment != "production" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Stripe
stripe.api_key = config.stripe_secret_key

# Performance monitoring middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Pydantic models
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

# AI Stack templates
TEMPLATES = {
    "ollama-webui": {
        "name": "Private AI Chat",
        "description": "Ollama + Open WebUI for private AI conversations",
        "features": ["Private AI models", "No data sharing", "Latest models", "Auto-updates"],
        "compose_file": "ollama-webui-stack.yml",
        "port": 3000,
        "pricing": {
            "basic": {"price": 2000, "features": ["Manual updates", "Basic support"]},
            "pro": {"price": 5000, "features": ["Auto-updates", "Zero downtime", "Priority support"]},
            "enterprise": {"price": 15000, "features": ["Real-time updates", "Custom schedules", "SLA"]}
        },
        "setup_script": "setup_ollama.sh"
    },
    "rag-app": {
        "name": "Document AI Assistant",
        "description": "Upload documents and chat with AI about them",
        "features": ["Document upload", "Smart search", "Context-aware AI", "Auto-updates"],
        "compose_file": "rag-stack.yml", 
        "port": 8501,
        "pricing": {
            "basic": {"price": 3000, "features": ["Manual updates", "Basic support"]},
            "pro": {"price": 7500, "features": ["Auto-updates", "Zero downtime", "Priority support"]},
            "enterprise": {"price": 20000, "features": ["Real-time updates", "Custom schedules", "SLA"]}
        },
        "setup_script": "setup_rag.sh"
    },
    "ai-agent": {
        "name": "AI Customer Agent",
        "description": "24/7 AI customer support that never sleeps",
        "features": ["24/7 availability", "Multi-language", "CRM integration", "Auto-updates"],
        "compose_file": "agent-stack.yml",
        "port": 8000,
        "pricing": {
            "basic": {"price": 5000, "features": ["Manual updates", "Basic support"]},
            "pro": {"price": 12500, "features": ["Auto-updates", "Zero downtime", "Priority support"]},
            "enterprise": {"price": 30000, "features": ["Real-time updates", "Custom schedules", "SLA"]}
        },
        "setup_script": "setup_agent.sh"
    }
}

# Database operations
async def execute_query(sql: str, parameters: list = None):
    """Execute SQL query using Aurora Data API or traditional connection"""
    try:
        if config.use_aurora_data_api:
            response = db_client.execute_statement(sql, parameters)
            return response
        else:
            # Fallback to traditional connection for development
            # This would use asyncpg or similar for local development
            logger.warning("Using fallback database connection")
            return {"records": []}
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")

# Public endpoints (no authentication required)
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI-Stack Deploy API", 
        "version": "1.0.0", 
        "status": "operational",
        "docs": "/docs" if config.environment != "production" else "Contact support for API docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        environment=config.environment
    )

@app.get("/templates")
async def get_templates():
    """Get available AI stack templates with pricing (public endpoint)"""
    return {"templates": TEMPLATES}

# Protected endpoints (authentication required)
@app.get("/user/profile")
@rate_limit(max_requests=100, window_seconds=3600)
async def get_user_profile(current_user: dict = Depends(get_current_user)) -> UserProfile:
    """Get current user profile and statistics"""
    user_id = current_user["user_id"]
    email = current_user["email"]
    
    try:
        # Get subscription count
        subscription_sql = """
            SELECT COUNT(*) as count 
            FROM subscriptions 
            WHERE user_id = ? AND status = 'active'
        """
        subscription_result = await execute_query(subscription_sql, [{"name": "user_id", "value": {"stringValue": user_id}}])
        subscription_count = subscription_result.get("records", [{}])[0].get("count", 0) if subscription_result.get("records") else 0
        
        # Get deployment count
        deployment_sql = """
            SELECT COUNT(*) as count 
            FROM deployments 
            WHERE user_id = ?
        """
        deployment_result = await execute_query(deployment_sql, [{"name": "user_id", "value": {"stringValue": user_id}}])
        deployment_count = deployment_result.get("records", [{}])[0].get("count", 0) if deployment_result.get("records") else 0
        
        return UserProfile(
            user_id=user_id,
            email=email,
            subscription_count=subscription_count,
            deployment_count=deployment_count
        )
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving user profile")

@app.post("/create-subscription")
@rate_limit(max_requests=10, window_seconds=3600)
async def create_subscription(
    request: SubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe subscription for a deployment (protected)"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        template = TEMPLATES.get(request.plan_type.split('-')[0])
        if not template:
            raise HTTPException(status_code=400, detail="Invalid template")

        # Extract pricing tier
        tier = request.plan_type.split('-')[-1] if '-' in request.plan_type else 'basic'
        pricing = template['pricing'].get(tier, template['pricing']['basic'])

        # Create Stripe customer
        customer = stripe.Customer.create(
            email=user_email,
            payment_method=request.payment_method_id,
            invoice_settings={
                'default_payment_method': request.payment_method_id,
            },
            metadata={
                'user_id': user_id,
                'supabase_user': 'true'
            }
        )

        # Create Stripe subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"{template['name']} - {tier.title()}",
                        'description': template['description'],
                    },
                    'unit_amount': pricing['price'],
                    'recurring': {
                        'interval': 'month',
                    },
                },
            }],
            expand=['latest_invoice.payment_intent'],
            metadata={
                'user_id': user_id,
                'template_id': request.plan_type
            }
        )

        # Save to database
        subscription_id = str(uuid.uuid4())
        insert_sql = """
            INSERT INTO subscriptions (id, user_id, user_email, stripe_subscription_id, plan_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        parameters = [
            {"name": "id", "value": {"stringValue": subscription_id}},
            {"name": "user_id", "value": {"stringValue": user_id}},
            {"name": "user_email", "value": {"stringValue": user_email}},
            {"name": "stripe_subscription_id", "value": {"stringValue": subscription.id}},
            {"name": "plan_type", "value": {"stringValue": request.plan_type}},
            {"name": "status", "value": {"stringValue": subscription.status}},
            {"name": "created_at", "value": {"stringValue": datetime.now().isoformat()}}
        ]
        
        await execute_query(insert_sql, parameters)

        return {
            "subscription_id": subscription_id,
            "stripe_subscription_id": subscription.id,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
            "status": subscription.status
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"Subscription creation error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")

@app.post("/deploy", response_model=DeploymentResponse)
@rate_limit(max_requests=20, window_seconds=3600)
async def deploy_stack(
    request: DeploymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Deploy an AI stack after successful payment (protected)"""
    try:
        user_id = current_user["user_id"]
        user_email = current_user["email"]
        
        template_name = request.template_id.split('-')[0]
        template = TEMPLATES.get(template_name)
        if not template:
            raise HTTPException(status_code=400, detail="Invalid template")

        # Verify subscription exists and is active for this user
        subscription_sql = """
            SELECT id, stripe_subscription_id 
            FROM subscriptions 
            WHERE user_id = ? AND plan_type LIKE ? AND status = 'active'
        """
        subscription_result = await execute_query(subscription_sql, [
            {"name": "user_id", "value": {"stringValue": user_id}},
            {"name": "plan_type", "value": {"stringValue": f"{template_name}%"}}
        ])
        
        if not subscription_result.get("records"):
            raise HTTPException(status_code=400, detail="No active subscription found")

        subscription_record = subscription_result["records"][0]
        subscription_id = subscription_record.get("id", {}).get("stringValue")

        # Determine auto-update settings based on plan tier
        tier = request.template_id.split('-')[-1] if '-' in request.template_id else 'basic'
        auto_update_enabled = tier in ['pro', 'enterprise']
        update_schedule = 'monthly' if tier == 'pro' else 'immediate' if tier == 'enterprise' else 'manual'

        # Create DigitalOcean droplet
        manager = digitalocean.Manager(token=config.digitalocean_token)
        
        deployment_id = str(uuid.uuid4())
        droplet_name = f"ai-stack-{deployment_id[:8]}"
        
        droplet = digitalocean.Droplet(
            token=config.digitalocean_token,
            name=droplet_name,
            region='nyc1',
            image='docker-20-04',
            size_slug='s-2vcpu-2gb',
            ssh_keys=manager.get_all_sshkeys(),
            backups=False,
            ipv6=True,
            user_data=generate_cloud_init_script(template),
            tags=[f'ai-deploy-{template_name}', f'user-{user_id}', f'tier-{tier}']
        )
        
        droplet.create()
        
        # Wait for droplet to be ready
        droplet.load()
        while droplet.status != 'active':
            time.sleep(5)
            droplet.load()
        
        # Generate access URL
        access_url = f"http://{droplet.ip_address}:{template['port']}"
        
        # Save deployment to database
        deployment_sql = """
            INSERT INTO deployments (id, user_id, user_email, template_id, droplet_id, url, status, created_at, subscription_id, auto_update_enabled, update_schedule)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        deployment_parameters = [
            {"name": "id", "value": {"stringValue": deployment_id}},
            {"name": "user_id", "value": {"stringValue": user_id}},
            {"name": "user_email", "value": {"stringValue": user_email}},
            {"name": "template_id", "value": {"stringValue": request.template_id}},
            {"name": "droplet_id", "value": {"stringValue": str(droplet.id)}},
            {"name": "url", "value": {"stringValue": access_url}},
            {"name": "status", "value": {"stringValue": "deploying"}},
            {"name": "created_at", "value": {"stringValue": datetime.now().isoformat()}},
            {"name": "subscription_id", "value": {"stringValue": subscription_id}},
            {"name": "auto_update_enabled", "value": {"booleanValue": auto_update_enabled}},
            {"name": "update_schedule", "value": {"stringValue": update_schedule}}
        ]
        
        await execute_query(deployment_sql, deployment_parameters)

        return DeploymentResponse(
            deployment_id=deployment_id,
            url=access_url,
            status="deploying",
            subscription_id=subscription_id
        )

    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

@app.get("/deployments")
@rate_limit(max_requests=100, window_seconds=3600)
async def get_user_deployments(current_user: dict = Depends(get_current_user)):
    """Get all deployments for the current user (protected)"""
    user_id = current_user["user_id"]
    
    try:
        deployments_sql = """
            SELECT id, template_id, url, status, created_at, auto_update_enabled, update_schedule 
            FROM deployments 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """
        result = await execute_query(deployments_sql, [
            {"name": "user_id", "value": {"stringValue": user_id}}
        ])
        
        deployments = []
        for record in result.get("records", []):
            deployments.append({
                "id": record.get("id", {}).get("stringValue"),
                "template_id": record.get("template_id", {}).get("stringValue"),
                "url": record.get("url", {}).get("stringValue"),
                "status": record.get("status", {}).get("stringValue"),
                "created_at": record.get("created_at", {}).get("stringValue"),
                "auto_update_enabled": record.get("auto_update_enabled", {}).get("booleanValue"),
                "update_schedule": record.get("update_schedule", {}).get("stringValue")
            })
        
        return {"deployments": deployments}
    except Exception as e:
        logger.error(f"Error getting deployments: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving deployments")

@app.delete("/deployments/{deployment_id}")
@rate_limit(max_requests=50, window_seconds=3600)
async def delete_deployment(
    deployment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a deployment and cancel subscription (protected, user-scoped)"""
    try:
        user_id = current_user["user_id"]
        
        # Get deployment info (user-scoped)
        deployment_sql = """
            SELECT droplet_id, subscription_id 
            FROM deployments 
            WHERE id = ? AND user_id = ?
        """
        result = await execute_query(deployment_sql, [
            {"name": "id", "value": {"stringValue": deployment_id}},
            {"name": "user_id", "value": {"stringValue": user_id}}
        ])
        
        if not result.get("records"):
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        record = result["records"][0]
        droplet_id = record.get("droplet_id", {}).get("stringValue")
        subscription_id = record.get("subscription_id", {}).get("stringValue")
        
        # Delete DigitalOcean droplet
        if droplet_id:
            manager = digitalocean.Manager(token=config.digitalocean_token)
            droplet = manager.get_droplet(int(droplet_id))
            droplet.destroy()
        
        # Cancel Stripe subscription
        if subscription_id:
            subscription_sql = """
                SELECT stripe_subscription_id 
                FROM subscriptions 
                WHERE id = ? AND user_id = ?
            """
            sub_result = await execute_query(subscription_sql, [
                {"name": "id", "value": {"stringValue": subscription_id}},
                {"name": "user_id", "value": {"stringValue": user_id}}
            ])
            
            if sub_result.get("records"):
                stripe_sub_id = sub_result["records"][0].get("stripe_subscription_id", {}).get("stringValue")
                if stripe_sub_id:
                    stripe.Subscription.delete(stripe_sub_id)
                    
                    # Update subscription status
                    update_sql = """
                        UPDATE subscriptions 
                        SET status = 'canceled' 
                        WHERE id = ? AND user_id = ?
                    """
                    await execute_query(update_sql, [
                        {"name": "id", "value": {"stringValue": subscription_id}},
                        {"name": "user_id", "value": {"stringValue": user_id}}
                    ])
        
        # Delete from database
        delete_sql = """
            DELETE FROM deployments 
            WHERE id = ? AND user_id = ?
        """
        await execute_query(delete_sql, [
            {"name": "id", "value": {"stringValue": deployment_id}},
            {"name": "user_id", "value": {"stringValue": user_id}}
        ])
        
        return {"message": "Deployment deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete deployment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete deployment: {str(e)}")

# Stripe webhook endpoint
@app.post("/webhook/stripe")
async def stripe_webhook(request):
    """Handle Stripe webhooks"""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.stripe_webhook_secret
        )
        
        # Handle the event
        if event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            # Update subscription status in database
            logger.info(f"Subscription updated: {subscription['id']}")
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            # Handle failed payment
            logger.warning(f"Payment failed for invoice: {invoice['id']}")
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook error")

# Helper functions
def generate_cloud_init_script(template: Dict) -> str:
    """Generate cloud-init script for droplet setup"""
    return f"""#!/bin/bash
# Update system
apt-get update && apt-get upgrade -y

# Install docker-compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
mkdir -p /app
cd /app

# Download docker-compose file for template
cat > docker-compose.yml << 'EOF'
{generate_docker_compose(template)}
EOF

# Start the stack
docker-compose up -d

# Setup monitoring
cat > /etc/cron.d/ai-stack-monitor << 'EOF'
*/5 * * * * root cd /app && docker-compose ps >> /var/log/stack-status.log
EOF
"""

def generate_docker_compose(template: Dict) -> str:
    """Generate docker-compose.yml content based on template"""
    compose_configs = {
        "ollama-webui": """
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    restart: unless-stopped
    environment:
      - OLLAMA_HOST=0.0.0.0
  
  webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    restart: unless-stopped
    depends_on:
      - ollama

volumes:
  ollama:
""",
        "rag-app": """
version: '3.8'
services:
  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma:/chroma/chroma
    restart: unless-stopped
  
  rag-app:
    image: python:3.11-slim
    ports:
      - "8501:8501"
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    restart: unless-stopped
    depends_on:
      - chromadb
    command: >
      bash -c "pip install streamlit chromadb openai &&
               echo 'import streamlit as st; st.title(\"RAG Document Chat\")' > app.py &&
               streamlit run app.py --server.address 0.0.0.0 --server.port 8501"

volumes:
  chroma:
""",
        "ai-agent": """
version: '3.8'
services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
  
  agent:
    image: python:3.11-slim
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    restart: unless-stopped
    depends_on:
      - redis
    command: >
      bash -c "pip install fastapi uvicorn redis &&
               echo 'from fastapi import FastAPI; app = FastAPI(); @app.get(\"/\"); def read_root(): return {\"message\": \"AI Customer Agent Running\"}' > main.py &&
               uvicorn main:app --host 0.0.0.0 --port 8000"

volumes:
  redis_data:
"""
    }
    
    template_key = template["compose_file"].replace("-stack.yml", "")
    return compose_configs.get(template_key, compose_configs["ollama-webui"])

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found", "status_code": 404}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error: {str(exc)}")
    return {"error": "Internal server error", "status_code": 500}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)