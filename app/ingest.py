# --- Ingestion Script ---
# This script is run once to load data into Milvus.
# It uses the older, stable import paths for langchain==0.1.20.

import os
from pymilvus import MilvusException

# --- LANGCHAIN 0.1.20 IMPORTS ---
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Milvus

# --- Configuration ---
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "supply_chain_risks"
KNOWLEDGE_BASE_DIR = "knowledge_base"

print("--- Starting Ingestion Script ---")

try:
    # 1. Initialize Embeddings
    print("Initializing Ollama embeddings...")
    embeddings = OllamaEmbeddings(model="llama3")
    print("Ollama Embeddings initialized.")

    # 2. Load Documents
    print(f"Loading documents from '{KNOWLEDGE_BASE_DIR}'...")
    loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*.txt",  # Load all .txt files
        loader_cls=TextLoader,
        show_progress=True,
        use_multithreading=True  # Corrected typo
    )
    documents = loader.load()
    if not documents:
        print(f"No documents found in '{KNOWLEDGE_BASE_DIR}'.")
        print("Please create text files in this directory and try again.")
        exit(1)
    print(f"Loaded {len(documents)} documents.")

    # 3. Split Documents
    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    # 4. Connect to Milvus and Ingest
    # This will create the collection if it doesn't exist
    # and add the new documents.
    print(f"Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}...")
    vector_store = Milvus.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=True # Set to True to clear old data on every run
    )
    print(f"Successfully ingested data into Milvus collection: '{COLLECTION_NAME}'")

except FileNotFoundError:
    print(f"ERROR: Directory not found: '{KNOWLEDGE_BASE_DIR}'")
    print("Please create the 'knowledge_base' folder and add your .txt files.")
except MilvusException as e:
    print(f"ERROR: Could not connect to Milvus: {e}")
    print(f"Please ensure your Milvus server is running at {MILVUS_HOST}:{MILVUS_PORT}.")
except ImportError:
    print("ERROR: A required Python package is missing.")
    print("Please ensure your venv is active and you have run: pip install -r requirements.txt")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("--- Ingestion Script Finished ---")
