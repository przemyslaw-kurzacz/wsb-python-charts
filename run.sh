#!/bin/bash

# Kolory do wyświetlania komunikatów
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Data Charts App - WSB Project${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Sprawdź czy istnieje venv
if [ ! -d ".venv" ]; then
    echo -e "${RED}Brak środowiska wirtualnego!${NC}"
    echo -e "${BLUE}Tworzę środowisko...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✓ Utworzono .venv${NC}"
fi

# Aktywuj venv
echo -e "${BLUE}Aktywuję środowisko wirtualne...${NC}"
source .venv/bin/activate

# Sprawdź czy są zainstalowane pakiety
if [ ! -f ".venv/installed" ]; then
    echo -e "${BLUE}Instaluję zależności...${NC}"
    pip install -r requirements.txt
    touch .venv/installed
    echo -e "${GREEN}✓ Zainstalowano zależności${NC}"
fi

# Utwórz katalogi jeśli nie istnieją
mkdir -p data uploads

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Uruchamiam aplikację...${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Aplikacja dostępna pod:${NC} http://127.0.0.1:5001"
echo -e "${BLUE}Aby zatrzymać:${NC} Ctrl+C"
echo ""

# Uruchom aplikację
python main.py

