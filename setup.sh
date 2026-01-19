#!/bin/bash

# Consulting Engine Setup Script
# This script helps set up the development environment

set -e

echo "═══════════════════════════════════════════════"
echo "  Consulting Engine - Setup Script"
echo "═══════════════════════════════════════════════"
echo ""

# Check for required tools
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found"
    echo ""
    read -p "Would you like to create one now? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your OpenAI API key: " openai_key
        
        cat > .env << EOF
# OpenAI API Key (required)
OPENAI_API_KEY=$openai_key

# Database (default)
DATABASE_URL=postgresql://postgres:postgres@db:5432/consulting_engine

# Application
DEBUG=true
OPENAI_MODEL=gpt-4-turbo-preview
EOF
        
        echo "✅ .env file created"
    else
        echo ""
        echo "Please create a .env file manually with your OpenAI API key."
        echo "See ENV_SETUP.md for details."
        exit 1
    fi
else
    echo "✅ .env file exists"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  Starting Services"
echo "═══════════════════════════════════════════════"
echo ""

# Build and start services
docker-compose up --build -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "═══════════════════════════════════════════════"
    echo "  ✅ Setup Complete!"
    echo "═══════════════════════════════════════════════"
    echo ""
    echo "Services are running:"
    echo "  • Frontend:  http://localhost:3000"
    echo "  • Backend:   http://localhost:8000"
    echo "  • API Docs:  http://localhost:8000/docs"
    echo ""
    echo "Sample data available in: sample_data/"
    echo ""
    echo "To stop services:"
    echo "  docker-compose down"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f"
    echo ""
    echo "See QUICKSTART.md for a guided demo."
    echo "═══════════════════════════════════════════════"
else
    echo ""
    echo "❌ Services failed to start. Check logs with:"
    echo "   docker-compose logs"
    exit 1
fi
