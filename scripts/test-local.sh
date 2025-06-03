#!/bin/bash

echo "🧪 Testing Local Development Environment"
echo "======================================="

# Test Backend Health
echo "1. Testing Backend Health..."
BACKEND_HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "error")
if [ "$BACKEND_HEALTH" = "healthy" ]; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    exit 1
fi

# Test Backend Templates
echo "2. Testing Backend Templates..."
TEMPLATES=$(curl -s http://localhost:8000/templates | jq -r '.templates | length' 2>/dev/null || echo "0")
if [ "$TEMPLATES" -gt "0" ]; then
    echo "✅ Backend templates endpoint working ($TEMPLATES templates)"
else
    echo "❌ Backend templates endpoint failed"
    exit 1
fi

# Test Frontend
echo "3. Testing Frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend is not accessible (status: $FRONTEND_STATUS)"
    exit 1
fi

# Test Database Connection
echo "4. Testing Database Connection..."
DB_TEST=$(docker exec ai-stack-postgres psql -U aistackuser -d aistackdb -c "SELECT 1;" 2>/dev/null || echo "error")
if [[ "$DB_TEST" == *"1"* ]]; then
    echo "✅ Database connection working"
else
    echo "❌ Database connection failed"
    exit 1
fi

echo ""
echo "🎉 All local tests passed!"
echo ""
echo "🔗 URLs:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Database: localhost:5432"
echo ""
