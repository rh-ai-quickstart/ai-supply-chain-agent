import sys
from pymilvus import MilvusClient

# --- Configuration ---
MILVUS_URI = "http://localhost:19530" 
MILVUS_TOKEN = "root:Milvus" 

def print_separator(char='-', length=50):
    """Prints a consistent separator line."""
    print(char * length)

def list_milvus_content():
    """Connects to Milvus, lists databases, and describes all collections."""
    try:
        # 1. Establish the connection to Milvus using MilvusClient
        print(f"Connecting to Milvus at {MILVUS_URI}...")
        client = MilvusClient(
            uri=MILVUS_URI, 
            token=MILVUS_TOKEN 
        )
        print("Connection successful.")

        print_separator('=')
        print("🔍 Listing All Milvus Databases")
        print_separator('=')

        # 2. List all databases
        database_list = client.list_databases()
        
        if not database_list:
            print("No databases found.")
            return

        for db_name in database_list:
            print(f"\n--- Database: **{db_name}** ---")
            
            # Use the current database for subsequent collection operations
            client.using_database(db_name)

            # Optional: Describe database for more details
            db_details = client.describe_database(db_name=db_name)
            print(f"  Description: {db_details.get('description', 'N/A')}")
            if db_details.get('properties'):
                print(f"  Properties: {db_details['properties']}")

            # 3. List all collections within the current database
            collections = client.list_collections()
            
            if not collections:
                print("  No collections found in this database.")
                continue

            print("\n  --- Collections in Database ---")
            for collection_name in collections:
                print(f"    - **Collection: {collection_name}**")
                
                # 4. Get detailed collection schema and statistics
                
                # Retrieve collection schema (fields, dimensions, etc.)
                schema = client.describe_collection(collection_name=collection_name)
                
                # Retrieve collection statistics (number of entities, load state)
                stats = client.get_collection_stats(collection_name=collection_name)

                print(f"      Description: {schema.get('description', 'N/A')}")
                
                # Print key statistics
                entity_count = stats.get('row_count', 'N/A')
                print(f"      Entities (Rows): {entity_count}")
                
                # --- FIX APPLIED HERE ---
                # Check the type of load_state and handle it appropriately
                raw_load_state = stats.get('load_state', 'N/A')
                
                if hasattr(raw_load_state, 'value'):
                    # If it's an Enum object, use its value or name
                    load_state_str = raw_load_state.name
                else:
                    # If it's already a string, use it directly
                    load_state_str = str(raw_load_state)

                print(f"      Load State: {load_state_str}")
                # ------------------------
                
                # Print field details
                print("      Fields (Schema):")
                for field in schema.get('fields', []):
                    field_name = field['name']
                    # Use .name instead of .split() to safely get the Enum name if it's an Enum
                    field_type_raw = field.get('type')
                    field_type = field_type_raw.name if hasattr(field_type_raw, 'name') else str(field_type_raw)
                    
                    is_primary = ' (PRIMARY KEY)' if field.get('is_primary') else ''
                    
                    # Include dimension for vector fields
                    dim = ''
                    # Check for 'dim' in params dictionary safely
                    if field_type == 'FLOAT_VECTOR' and field.get('params') and 'dim' in field['params']:
                        dim = f", Dim: {field['params']['dim']}"
                    
                    print(f"        -> {field_name}: {field_type}{is_primary}{dim}")
            
            print_separator('-')

    except Exception as e:
        print(f"\n❌ An error occurred while connecting or accessing Milvus:")
        print(f"   {e}")
        print("\nPlease ensure Milvus is running and the MILVUS_URI/MILVUS_TOKEN are correct.")

if __name__ == "__main__":
    list_milvus_content()
