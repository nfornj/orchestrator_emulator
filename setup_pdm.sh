#!/bin/bash

# Check if PDM is installed
if ! command -v pdm &> /dev/null; then
    echo "PDM is not installed. Installing PDM..."
    pip install --user pdm
else
    echo "PDM is already installed."
fi

# Initialize a PDM project if not already initialized
if [ ! -f "pdm.lock" ]; then
    echo "Initializing PDM project..."
    pdm init -n
fi

# Install dependencies
echo "Installing dependencies with PDM..."
pdm install

echo "PDM setup complete. You can now use PDM to manage your dependencies."
echo "Run 'pdm add <package>' to add new dependencies."
echo "Run 'pdm update' to update dependencies."
echo "Run 'pdm run <command>' to run a command in the PDM environment." 