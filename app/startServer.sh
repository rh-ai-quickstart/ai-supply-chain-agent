#!/bin/bash
# Script to run the Supply Chain AI Backend using an existing Milvus install

echo "--- Supply Chain AI Backend Starter ---"
echo ""

# --- Check 1: Milvus ---
echo "[Step 1: Milvus Check]"
echo "This script assumes your local Milvus instance is already running."
echo "Please ensure Milvus is active and accessible on localhost:19530."
echo ""
echo "Press [Enter] to continue if your Milvus is running..."
read -r

# --- Check 2: Ollama ---
echo "[Step 2: Ollama Check]"
echo "This script assumes your local Ollama server is already running."
echo "If not, please open a NEW terminal and run: ollama serve"
echo ""
echo "Press [Enter] to continue if Ollama is running..."
read -r

# --- Check 3: Virtual Environment ---
echo "[Step 3: Activating Virtual Environment]"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Error: 'venv' directory not found or is incomplete."
    echo "Please run the following commands first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# --- Check 4: Data Ingestion ---
echo "[Step 4: Data Ingestion (RAG)]"
echo "We will now ingest/update the knowledge base in your Milvus collection."
echo "This will connect to Milvus and embed documents from the 'knowledge_base' folder."
python ingest.py
echo "Data ingestion complete."
echo ""

# --- Step 5: Run the Server ---
echo "[Step 5: Starting Flask Server]"
echo "Starting the main application server on http://localhost:5001"
echo "Your UI (SupplyChainDashboard.html) can now connect."
echo "Press [Ctrl+C] to stop the server."
python app.py
