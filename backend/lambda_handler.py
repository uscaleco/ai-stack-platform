import json
import logging
import os
import sys
from typing import Any, Dict

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
    from mangum import Mangum

    from main import app

    # Create Mangum handler
    handler = Mangum(
        app,
        lifespan="off",  # Disable lifespan for Lambda
        api_gateway_base_path="/",
        text_mime_types=[
            "application/json",
            "application/javascript",
            "application/xml",
            "application/vnd.api+json",
        ],
    )

except ImportError as e:
    logger.error(f"Import error: {e}")

    def handler(event, context, e):
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Import error", "message": str(e)}),
        }


def convert_alb_to_apigw(alb_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert ALB event format to API Gateway format

    Args:
        alb_event: Application Load Balancer event

    Returns:
        API Gateway formatted event
    """
    return {
        "httpMethod": alb_event.get("httpMethod", "GET"),
        "path": alb_event.get("path", "/"),
        "queryStringParameters": alb_event.get("queryStringParameters") or {},
        "headers": alb_event.get("headers") or {},
        "body": alb_event.get("body", ""),
        "isBase64Encoded": alb_event.get("isBase64Encoded", False),
        "requestContext": {
            "httpMethod": alb_event.get("httpMethod", "GET"),
            "path": alb_event.get("path", "/"),
            "stage": "prod",
            "requestId": "lambda-request",
            "identity": {
                "sourceIp": alb_event.get("headers", {}).get(
                    "x-forwarded-for", "127.0.0.1"
                )
            },
        },
    }


def convert_apigw_to_alb(apigw_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert API Gateway response format to ALB format

    Args:
        apigw_response: API Gateway response

    Returns:
        ALB formatted response
    """
    status_code = apigw_response.get("statusCode", 200)

    # Map status codes to descriptions
    status_descriptions = {
        200: "200 OK",
        201: "201 Created",
        400: "400 Bad Request",
        401: "401 Unauthorized",
        403: "403 Forbidden",
        404: "404 Not Found",
        422: "422 Unprocessable Entity",
        500: "500 Internal Server Error",
    }

    return {
        "statusCode": status_code,
        "statusDescription": status_descriptions.get(
            status_code, f"{status_code} Unknown"
        ),
        "headers": apigw_response.get("headers", {}),
        "body": apigw_response.get("body", ""),
        "isBase64Encoded": apigw_response.get("isBase64Encoded", False),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point

    Args:
        event: Lambda event (API Gateway request)
        context: Lambda context object

    Returns:
        API Gateway response format
    """
    try:
        # Log the incoming event for debugging (remove in production)
        if os.getenv("DEBUG", "false").lower() == "true":
            logger.info(f"Incoming event: {json.dumps(event, default=str)}")

        # Handle different event sources
        if "requestContext" in event:
            # API Gateway event
            if "elb" in event.get("requestContext", {}):
                # Application Load Balancer event - convert to API Gateway
                # format
                converted_event = convert_alb_to_apigw(event)
                response = handler(converted_event, context)
                return convert_apigw_to_alb(response)
            else:
                # Regular API Gateway event
                response = handler(event, context)
                return response
        elif "httpMethod" in event:
            # Direct HTTP event (testing)
            response = handler(event, context)
            return response
        else:
            # Unknown event type
            logger.warning(f"Unknown event type: {type(event)}")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "error": "Unsupported event type",
                        "event_type": str(type(event)),
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "error": "Internal server error",
                    "message": (str(e) if os.getenv("DEBUG") else "An error occurred"),
                }
            ),
        }


def optimize_lambda_performance():
    """Optimize Lambda performance by preloading modules"""
    try:
        import boto3

        if not hasattr(optimize_lambda_performance, "_initialized"):
            boto3.client("secretsmanager")
            boto3.client("rds-data")
            optimize_lambda_performance._initialized = True
            logger.info("Lambda performance optimization completed")
    except Exception as e:
        logger.warning(f"Performance optimization failed: {str(e)}")


# Initialize performance optimizations during module load
optimize_lambda_performance()

# Export the main handler
__all__ = ["lambda_handler"]