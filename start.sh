#!/bin/bash
echo "====================================================="
echo " Time-Series Aggregation Tool - Startup Script"
echo "====================================================="

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing/updating dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "====================================================="
echo " Starting server at: http://localhost:5001"
echo " Open this URL in your browser (NOT the HTML file!)"
echo "====================================================="
echo ""

python app.py
