import os
import requests
from pymilvus import connections, utility, CollectionSchema, FieldSchema, DataType, Collection

# --- Configuration ---
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "supply_chain_risks"
KNOWLEDGE_BASE_DIR = "knowledge_base"
OLLAMA_URL = "http://localhost:11434/api/tags"
OLLAMA_MODEL = "llama3"

def setup_milvus():
    print("--- Starting Milvus Setup Script ---")

    # 1. Ensure Knowledge Base Directory Exists
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"Creating '{KNOWLEDGE_BASE_DIR}' directory...")
        os.makedirs(KNOWLEDGE_BASE_DIR)
        
        # Create a sample document if empty
        sample_file = os.path.join(KNOWLEDGE_BASE_DIR, "sample_data.txt")
        with open(sample_file, "w") as f:
            f.write("Supply chain risks include natural disasters, political instability, and shipping delays.\n")
            f.write("Mitigation strategies involve diversifying suppliers and maintaining safety stock.\n")
        print(f"Created sample data at '{sample_file}'.")
    else:
        print(f"'{KNOWLEDGE_BASE_DIR}' directory already exists.")
        if not os.listdir(KNOWLEDGE_BASE_DIR):
            sample_file = os.path.join(KNOWLEDGE_BASE_DIR, "sample_data.txt")
            with open(sample_file, "w") as f:
                f.write("Supply chain risks include natural disasters, political instability, and shipping delays.\n")
            print(f"Added sample data to empty '{KNOWLEDGE_BASE_DIR}'.")

    # 2. Check Milvus Connection
    print(f"Checking Milvus connection at {MILVUS_HOST}:{MILVUS_PORT}...")
    try:
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT, timeout=5)
        print("Connected to Milvus successfully.")
        
        # Check if collection exists
        if utility.has_collection(COLLECTION_NAME):
            print(f"Collection '{COLLECTION_NAME}' already exists.")
        else:
            print(f"Collection '{COLLECTION_NAME}' does not exist yet. ingest.py will create it.")
            
    except Exception as e:
        print(f"ERROR: Could not connect to Milvus: {e}")
        print("Please ensure your Milvus server is running.")
        print("You can try running: bash standalone_embed.sh start")
        return

    # 3. Check Ollama Connection and Model
    print(f"Checking Ollama connection at {OLLAMA_URL}...")
    try:
        response = requests.get(OLLAMA_URL, timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            if OLLAMA_MODEL in model_names or any(OLLAMA_MODEL in name for name in model_names):
                print(f"Ollama is running and '{OLLAMA_MODEL}' model is available.")
            else:
                print(f"WARNING: Ollama is running, but '{OLLAMA_MODEL}' model was not found.")
                print(f"Please run: ollama pull {OLLAMA_MODEL}")
        else:
            print(f"WARNING: Ollama returned status code {response.status_code}.")
    except Exception as e:
        print(f"WARNING: Could not connect to Ollama: {e}")
        print("Please ensure Ollama is running (run 'ollama serve' in another terminal).")

    print("\n--- Setup Check Complete ---")
    print(f"You can now run: python ingest.py")

if __name__ == "__main__":
    setup_milvus()
