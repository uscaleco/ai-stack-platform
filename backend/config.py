# backend/config.py
import os
import boto3
import json
from typing import Optional
import logging
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

logger = logging.getLogger(__name__)

class Config:
    """Configuration management with AWS Secrets Manager support"""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # Load configuration based on environment
        if self.environment == "production":
            self._load_from_aws_secrets()
        else:
            self._load_from_env()
    
    def _load_from_aws_secrets(self):
        """Load configuration from AWS Secrets Manager"""
        try:
            secret_name = f"ai-stack-platform/{self.environment}"
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=self.aws_region
            )
            
            response = client.get_secret_value(SecretId=secret_name)
            secrets = json.loads(response['SecretString'])
            
            # Aurora Serverless Data API
            self.database_cluster_arn = os.getenv("DATABASE_CLUSTER_ARN")
            self.database_secret_arn = secrets.get("DATABASE_SECRET_ARN")
            self.database_name = "aistackdb"
            
            # Traditional connection string as fallback
            self.database_url = secrets.get("DATABASE_URL")
            
            # Supabase
            self.supabase_url = secrets.get("SUPABASE_URL")
            self.supabase_anon_key = secrets.get("SUPABASE_ANON_KEY")
            self.supabase_service_key = secrets.get("SUPABASE_SERVICE_KEY")
            self.supabase_jwt_secret = secrets.get("SUPABASE_JWT_SECRET")
            
            # Stripe
            self.stripe_secret_key = secrets.get("STRIPE_SECRET_KEY")
            self.stripe_publishable_key = secrets.get("STRIPE_PUBLISHABLE_KEY")
            self.stripe_webhook_secret = secrets.get("STRIPE_WEBHOOK_SECRET")
            
            # DigitalOcean
            self.digitalocean_token = secrets.get("DIGITALOCEAN_TOKEN")
            
            # External services
            self.openai_api_key = secrets.get("OPENAI_API_KEY")
            
            # Application settings
            self.frontend_url = secrets.get("FRONTEND_URL", "https://yourdomain.com")
            self.api_gateway_url = secrets.get("API_GATEWAY_URL")
            self.allowed_origins = secrets.get("ALLOWED_ORIGINS", self.frontend_url).split(",")
            
            logger.info("Configuration loaded from AWS Secrets Manager")
            
        except Exception as e:
            logger.error(f"Failed to load AWS secrets: {str(e)}")
            self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Aurora Serverless
        self.database_cluster_arn = os.getenv("DATABASE_CLUSTER_ARN")
        self.database_secret_arn = os.getenv("DATABASE_SECRET_ARN")
        self.database_name = os.getenv("DATABASE_NAME", "aistackdb")
        
        # Fallback to traditional connection
        self.database_url = os.getenv("DATABASE_URL", "postgresql://aistackuser:aistackpassword@localhost:5432/aistackdb")
        
        # Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
        
        # Stripe
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        # DigitalOcean
        self.digitalocean_token = os.getenv("DIGITALOCEAN_TOKEN")
        
        # External services
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Application settings
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", self.frontend_url).split(",")
        
        logger.info("Configuration loaded from environment variables")
    
    @property
    def use_aurora_data_api(self):
        """Check if we should use Aurora Data API (serverless)"""
        return bool(self.database_cluster_arn and self.database_secret_arn)
    
    @property
    def cors_origins(self):
        """Get CORS origins list"""
        if self.environment == "development":
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return self.allowed_origins
    
    @property
    def is_production(self):
        """Check if running in production"""
        return self.environment == "production"
    
    @property
    def is_lambda(self):
        """Check if running in Lambda environment"""
        return bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    
    def validate(self):
        """Validate required configuration"""
        required_vars = [
            "supabase_url", "supabase_anon_key", "supabase_service_key",
            "stripe_secret_key", "digitalocean_token"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(self, var, None):
                missing_vars.append(var.upper())
        
        if missing_vars:
            raise ValueError(f"Missing required configuration: {', '.join(missing_vars)}")
        
        logger.info("Configuration validation passed")

# Database client factory for Aurora Serverless
class DatabaseClient:
    """Database client that uses Aurora Data API when available"""
    
    def __init__(self, config: Config):
        self.config = config
        self._rds_data_client = None
    
    @property
    def rds_data_client(self):
        """Get RDS Data API client (for Aurora Serverless)"""
        if not self._rds_data_client:
            self._rds_data_client = boto3.client('rds-data', region_name=self.config.aws_region)
        return self._rds_data_client
    
    def execute_statement(self, sql: str, parameters: list = None):
        """Execute SQL using Aurora Data API"""
        if not self.config.use_aurora_data_api:
            raise ValueError("Aurora Data API not configured")
        
        params = {
            'resourceArn': self.config.database_cluster_arn,
            'secretArn': self.config.database_secret_arn,
            'database': self.config.database_name,
            'sql': sql
        }
        
        if parameters:
            params['parameters'] = parameters
        
        try:
            response = self.rds_data_client.execute_statement(**params)
            return response
        except Exception as e:
            logger.error(f"Aurora Data API error: {str(e)}")
            raise

# Singleton instances
@lru_cache()
def get_config():
    """Get configuration instance (cached)"""
    config = Config()
    config.validate()
    return config

@lru_cache()
def get_database_client():
    """Get database client instance (cached)"""
    config = get_config()
    return DatabaseClient(config)

# Global config instance
config = get_config()
db_client = get_database_client()