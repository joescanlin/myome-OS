#!/bin/bash
set -e

echo "==================================="
echo "Myome Development Environment Setup"
echo "==================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python3 --version

# Setup Python virtual environment
echo -e "\n${YELLOW}Setting up Python virtual environment...${NC}"
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}Created virtual environment${NC}"
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
echo -e "${GREEN}Python dependencies installed${NC}"
cd ..

# Setup frontend
echo -e "\n${YELLOW}Installing frontend dependencies...${NC}"
cd frontend
npm install
echo -e "${GREEN}Frontend dependencies installed${NC}"
cd ..

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services (PostgreSQL + Redis)...${NC}"
docker-compose up -d db redis
echo -e "${GREEN}Database and Redis started${NC}"

# Wait for database to be ready
echo -e "\n${YELLOW}Waiting for database to be ready...${NC}"
sleep 5

# Initialize database
echo -e "\n${YELLOW}Initializing database...${NC}"
cd backend
source .venv/bin/activate
python ../scripts/init_db.py
cd ..

echo -e "\n${GREEN}==================================="
echo "Setup complete!"
echo "==================================="
echo -e "${NC}"
echo "To start development:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn myome.api.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up"
