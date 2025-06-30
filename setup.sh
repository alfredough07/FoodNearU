#!/bin/bash

echo "Setting up the FoodNearU project environment..."
python3 -m venv ~/venvs/FoodNearU
source ~/venvs/FoodNearU/bin/activate

echo "Updating pip..."
pip install --upgrade pip

echo "Installing googlemaps..."
pip install googlemaps

echo "Installing Google GenAI..."
pip install -U google-genai

echo "Installing python-dotenv..."
pip install python-dotenv

echo "Setup Complete!"
echo "Run '''source ~/venvs/FoodNearU/bin/activate''' to activate the virtual environment."