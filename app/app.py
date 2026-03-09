# Version: V1.10F - Fix: Robust Fallback Generation
# Status: FULLY RESTORED & CONSOLIDATED
# ------------------------------------------------------------------
# Fix: FALLBACK GENERATION:
#       - If OpenSky returns 503 (Rate Limit), the system now generates
#         100 simulated flights (30 Cargo, 70 General) instead of just 12.
#       - This ensures the 'Show ALL Flights' UI toggle works even when offline.
# Fix: API RATE LIMITING:
#       - Cache delay set to 360s (6 mins).
# Feat: TELEMETRY & LOGGING:
#       - Preserved detailed console stats.

import os
import random
import json
import requests
import time
import re 
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- LOGGING CONFIGURATION ---
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "2"

# ==============================================================================
# 0. LIBRARY IMPORTS & SAFEGUARDS
# ==============================================================================
try:
    # Modern LangChain Imports
    from langchain_community.llms import Ollama
    from langchain.prompts import PromptTemplate
    from langchain.schema.output_parser import StrOutputParser
    from langchain_community.vectorstores import Milvus
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain.agents import Tool, AgentExecutor, create_react_agent
    from langchain.schema import HumanMessage, AIMessage
    AI_LIBS_PRESENT = True
except ImportError:
    print("CRITICAL SYSTEM WARNING: LangChain libraries not found. Chat will function in MOCK mode only.")
    AI_LIBS_PRESENT = False

app = Flask(__name__)
CORS(app)

# ==============================================================================
# 1. CONFIGURATION & STATE
# ==============================================================================
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "supply_chain_risks"
OPEN_SKY_URL = "https://opensky-network.org/api/states/all"

# EXPANDED Watchlist for Air Freight
CARGO_WATCHLIST = [
    'FDX', 'UPS', 'GTI', 'KAL', 'CKS', 'AMZ', 'DHL', 'PAC', 'GEC', 'ATLAS', 
    'CLX', 'BOX', 'RPA', 'N8', 'ABW', 'CJT',
    'DAL', 'UAL', 'AAL', 'BAW', 'DLH', 'AFR', 'CPA', 'ANA', 'JAL', 'QFA', 
    'UAE', 'ETH', 'QTR', 'SAS', 'KLM', 'SIA', 'CSN', 'CES'
]

GUARDRAIL_KEYWORDS = [
    "steak", "steakhouse", "burger", "hamburger", "pizza", "restaurant", 
    "food", "weather", "politics", "movie", "joke", "sports", 
    "nyc", "fashion", "song", "poem", "music", "bar", "grill", "bbq", 
    "sushi", "taco", "burrito", "salad", "sandwich", "coffee", "cafe",
    "best place to eat", "where to eat", "dinner", "lunch", "breakfast"
]

opensky_cache = {
    "data": None,
    "last_fetch": 0
}
CACHE_DURATION_SECONDS = 360 

current_simulated_event = {
    "event": None,
    "timestamp": 0
}
EVENT_DURATION_SECONDS = 120 


# ==============================================================================
# 2. REAL AI SETUP (MODERN REACT AGENT)
# ==============================================================================
agent_executor = None 
retriever = None
llm_json = None

if AI_LIBS_PRESENT:
    print("System: Initializing Real AI Stack (Ollama + Milvus)...")
    try:
        # A. Setup Embeddings & LLM
        embeddings = OllamaEmbeddings(model="llama3")
        llm_text = Ollama(model="llama3") 
        llm_json = Ollama(model="llama3", format="json") # For generative simulation

        # B. Connect to Milvus (Knowledge Base)
        vector_store = Milvus(
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        
        # C. Define Tools
        def format_docs(docs):
            return "\n\n---\n\n".join(doc.page_content for doc in docs)

        def get_optimized_trucking_route_func(query: str):
            query = query.lower()
            start_location = "los angeles dc"
            end_location = "chicago dc"
            if "ny" in query or "newark" in query: start_location = "newark hub"
            if "dallas" in query: end_location = "dallas dc"

            return json.dumps({
                "answer": f"Calculated the best route from {start_location} to {end_location} based on current traffic and fuel costs.",
                "routeData": {
                    "type": "optimized_land_route",
                    "coordinates": [[34.05, -118.24], [38.0, -100.0], [41.87, -87.62]],
                    "color": "#FFC300"
                }
            })

        tools = [
            Tool(
                name="get_optimized_trucking_route",
                func=get_optimized_trucking_route_func,
                description="Use this to calculate trucking routes."
            ),
            Tool(
                name="knowledge_base_retriever",
                func=lambda q: format_docs(retriever.invoke(q)),
                description="Use this to answer questions about supply chain risks/history."
            )
        ]

        # D. MODERN AGENT CONSTRUCTION (ReAct)
        react_prompt_template = """
You are a specialized Supply Chain Risk Assistant. 
GUARDRAILS:
1. If the user asks about routes, use `get_optimized_trucking_route`.
2. If the user asks about supply chain risks, history, or logistics, use `knowledge_base_retriever`.
3. STRICT PROHIBITION: Do NOT answer questions about food, restaurants, weather, sports, or trivia.

TOOLS:
{tools}

To use a tool, please use the following format:
```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:
```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

Begin!
Previous conversation history:
{chat_history}
New input: {input}
{agent_scratchpad}
"""
        prompt = PromptTemplate.from_template(react_prompt_template)
        agent = create_react_agent(llm=llm_text, tools=tools, prompt=prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)
        print("SUCCESS: Real AI Agent (Modern ReAct) initialized.")

    except Exception as e:
        print(f"WARNING: Real AI failed to initialize ({e}). Chat will be mocked.")
        agent_executor = None


# ==============================================================================
# 3. RESTORED SIMULATION SCHEMAS (Legacy/Fallback)
# ==============================================================================

def get_json_schema():
    return """
    {
        "kpis": {
            "inStock": {"value": "<value>%", "trendSymbol": "<▲ or ▼>", "trendClass": "<up or down>"},
            "onTime": {"value": "<value>%", "trendSymbol": "<▲ or ▼>", "trendClass": "<up or down>"},
            "turnover": {"value": "<value>x", "trendSymbol": "<▲ or ▼>", "trendClass": "<up or down>"},
            "lostSales": {"value": "$<value>M", "trendSymbol": "<▲ or ▼>", "trendClass": "<up or down>"},
            "reorderPoint": {"value": "<value>%", "trendSymbol": "<▲ or ▼>", "trendClass": "<up or down>"}
        },
        "alerts": {
            "global": [{"type": "info|warning|critical", "text": "...", "action": {"id": "...", "text": "..."}}],
            "regional": [],
            "airFreight": []
        },
        "charts": {
            "demand": { "labels": [], "actual": [], "forecast": [] },
            "revenue": { "revenueData": [], "marginData": [], "colors": [] }
        },
        "mapData": {
            "global": { "ports": [], "routes": [], "assets": [], "riskZones": [] },
            "regional": { "ports": [], "routes": [], "assets": [], "riskZones": [] },
            "airFreight": { "ports": [], "routes": [], "assets": [], "riskZones": [] }
        }
    }
    """

def get_prompt_template_str():
    return """
    You are a Supply Chain Risk Simulation AI.
    Generate a JSON object representing a simulated dashboard state.
    Output MUST match: {json_schema}
    Context: {context}
    Request: {scenario}, {severity}, {sentiment}
    """

if llm_json and retriever:
    json_schema_str = get_json_schema()
    prompt_template_str = get_prompt_template_str()
    prompt = PromptTemplate(
        template=prompt_template_str,
        input_variables=["context", "scenario", "severity", "sentiment", "leadTimeVariance", "productFocus", "mapView"],
        partial_variables={"json_schema": json_schema_str}
    )


# ==============================================================================
# 4. MCP AGENT (ENHANCED FALLBACK LOGIC)
# ==============================================================================
class MCPAgent:
    def __init__(self):
        self.airports = [
            {"id": "ANC", "name": "Anchorage (ANC)", "lat": 61.17, "lng": -149.99, "inventory": 200, "risk": 10, "buffer": 50},
            {"id": "LAX", "name": "Los Angeles (LAX)", "lat": 33.94, "lng": -118.40, "inventory": 150, "risk": 20, "buffer": 40},
            {"id": "JFK", "name": "New York (JFK)", "lat": 40.64, "lng": -73.77, "inventory": 180, "risk": 15, "buffer": 45},
            {"id": "FRA", "name": "Frankfurt (FRA)", "lat": 50.03, "lng": 8.57, "inventory": 220, "risk": 10, "buffer": 60},
            {"id": "HKG", "name": "Hong Kong (HKG)", "lat": 22.30, "lng": 113.91, "inventory": 300, "risk": 5, "buffer": 70},
        ]
        self.air_routes = [
            {"id": "HKG-ANC", "start": [113.91, 22.30], "end": [-149.99, 61.17], "primary": True},
            {"id": "FRA-JFK", "start": [8.57, 50.03], "end": [-73.77, 40.64], "primary": True},
            {"id": "ANC-LAX", "start": [-149.99, 61.17], "end": [-118.40, 33.94], "primary": True},
        ]

    def fetch_live_opensky_data(self):
        global opensky_cache
        current_time = time.time()
        
        # 1. Check Cache
        if (current_time - opensky_cache["last_fetch"]) < CACHE_DURATION_SECONDS and opensky_cache["data"]:
            return opensky_cache["data"]
            
        # 2. Fetch Fresh
        try:
            print("MCP Agent: Contacting OpenSky API...")
            # Timeout set to 8s for reliability
            response = requests.get(OPEN_SKY_URL, timeout=8) 
            if response.status_code == 200:
                data = response.json()
                opensky_cache["data"] = data.get('states', [])
                opensky_cache["last_fetch"] = current_time
                print(f"MCP Agent: OpenSky updated with {len(opensky_cache['data'])} flights.")
                return opensky_cache["data"]
            else:
                print(f"MCP Agent: API returned {response.status_code}. Using cache/fallback.")
                return opensky_cache["data"] 
        except Exception as e:
            print(f"OpenSky API Error (Using Fallback): {e}")
            return opensky_cache["data"] if opensky_cache["data"] else None

    # UPDATED: Generate massive fallback dataset if API fails
    def generate_fallback_planes(self):
        planes = []
        # Major Hubs for distribution
        hubs = [
            (35.0, -90.0), (38.0, -85.0), (61.0, -149.0), (22.0, 114.0), (50.0, 8.0), (25.0, 55.0), (1.0, 103.0),
            (34.0, -118.0), (40.0, -74.0), (51.0, 0.0), (35.0, 139.0)
        ]
        
        # 1. Generate Simulated CARGO (Matches Watchlist) - 30 Planes
        for i in range(30):
            hub = random.choice(hubs)
            prefix = random.choice(CARGO_WATCHLIST)
            planes.append({
                "id": f"sim-cargo-{i}", 
                "name": f"{prefix}{random.randint(100,9999)} (Sim)", 
                "cargo": "Mixed Freight",
                "routeId": None, 
                "is_live": True,
                "lat": hub[0] + random.uniform(-15, 15), 
                "lng": hub[1] + random.uniform(-15, 15), 
                "track": random.randint(0, 360),
                "speed": f"{random.randint(450, 600)} mph",
                "altitude_ft": f"{random.randint(30000, 42000)} ft",
            })

        # 2. Generate Simulated GENERAL TRAFFIC (Hidden by default) - 70 Planes
        for i in range(70):
            hub = random.choice(hubs)
            planes.append({
                "id": f"sim-gen-{i}", 
                "name": f"FLT{random.randint(100,9999)} (Gen)", 
                "cargo": "General Cargo", # UI filters this out by default
                "routeId": None, 
                "is_live": True,
                "lat": hub[0] + random.uniform(-20, 20), 
                "lng": hub[1] + random.uniform(-20, 20), 
                "track": random.randint(0, 360),
                "speed": f"{random.randint(400, 550)} mph",
                "altitude_ft": f"{random.randint(25000, 38000)} ft",
            })
            
        return planes

    def get_live_air_state(self):
        live_states = self.fetch_live_opensky_data()
        live_planes = []
        alerts = []
        
        total_raw_flights = len(live_states) if live_states else 0
        
        # Live Data Processing
        if live_states:
            for state in live_states:
                try:
                    if state[8]: continue # Skip On Ground
                    
                    callsign = state[1].strip() if state[1] else ""
                    if any(callsign.startswith(prefix) for prefix in CARGO_WATCHLIST):
                        velocity = state[9] if state[9] is not None else 0
                        altitude = state[7] if state[7] is not None else 0
                        live_planes.append({
                            "id": state[0], "name": f"{callsign} (Live)", "cargo": "Mixed Freight",
                            "routeId": None, "is_live": True, "lat": state[6], "lng": state[5], "track": state[10],
                            "speed": f"{velocity * 2.237:.0f} mph", "altitude_ft": f"{altitude * 3.28084:.0f} ft",
                        })
                except Exception: continue

            # Density Assurance Logic (Live)
            target_density = 100
            if len(live_planes) < target_density:
                for state in live_states:
                    if len(live_planes) >= target_density: break
                    try:
                        if state[8]: continue
                        if any(p['id'] == state[0] for p in live_planes): continue
                        if state[9] and state[9] > 100:
                            callsign = state[1].strip() if state[1] else "FLIGHT"
                            altitude = state[7] if state[7] is not None else 0
                            live_planes.append({
                                "id": state[0], "name": f"{callsign} (General)", "cargo": "General Cargo",
                                "routeId": None, "is_live": True, "lat": state[6], "lng": state[5], "track": state[10],
                                "speed": f"{state[9] * 2.237:.0f} mph", "altitude_ft": f"{altitude * 3.28084:.0f} ft",
                            })
                    except Exception: continue

        # FALLBACK: If API failed or yielded zero results
        if not live_planes:
             alerts.append({"type": "warning", "text": "OpenSky connection slow. Displaying predicted flight paths."})
             live_planes = self.generate_fallback_planes()

        print(f"MCP Agent: Final Display Count: {len(live_planes)}")

        return {
            "ports": self.airports,
            "routes": list(self.air_routes), 
            "assets": live_planes,
            "riskZones": [] 
        }, alerts

mcp_agent = MCPAgent()


# ==============================================================================
# 5. DATA GENERATION (THE CORE LOGIC)
# ==============================================================================

def get_simulated_world_event(mapView="global", force_new=False):
    global current_simulated_event
    current_time = time.time()

    if current_simulated_event["event"]:
        if not force_new:
            if (current_time - current_simulated_event["timestamp"]) > EVENT_DURATION_SECONDS:
                current_simulated_event["event"] = None 
                return None
            else:
                return current_simulated_event["event"] 

    if force_new:
        if mapView == "regional":
            new_event = { "type": "warning", "text": "LABOR DISPUTE: LA/LGB negotiations stalled. AI recommends diversion.", "action": {"id": "propose_diversion_la", "text": "AI: View Options"} }
        elif mapView == "airFreight":
            new_event = { "type": "critical", "text": "LIVE THREAT: Alaskan Storm. Airspace closing. AI recommends rerouting.", "action": {"id": "mcp-reroute-1", "text": "AI: View Reroute"} }
        else: 
            new_event = { "type": "critical", "text": "NEW THREAT: Cyclone 'Atlas' threatens Singapore. AI recommends rerouting.", "action": {"id": "propose_reroute_sin", "text": "AI: View Options"} }
        
        current_simulated_event = {"event": new_event, "timestamp": current_time}
        return new_event

    return None

def get_static_fallback_data():
    return {
        "kpis": {
            "inStock": {"value": "95%", "trendSymbol": "▲", "trendClass": "up"},
            "onTime": {"value": "92%", "trendSymbol": "▲", "trendClass": "up"},
            "turnover": {"value": "5.2x", "trendSymbol": "▲", "trendClass": "up"},
            "lostSales": {"value": "$0.2M", "trendSymbol": "▼", "trendClass": "down"},
            "reorderPoint": {"value": "20%", "trendSymbol": "▲", "trendClass": "up"}
        },
        "alerts": { "global": [{"type": "info", "text": "System running in SAFE MODE (Live data unavailable)."}], "regional": [], "airFreight": [] },
        "charts": {
             "demand": { "labels": ["W1","W2","W3"], "actual": [50,52,55], "forecast": [51,53,54] },
             "revenue": { "revenueData": [100,100,100,100,100], "marginData": [30,30,30,30,30], "colors": ["green"]*5 }
        },
        "mapData": {
             "global": { "ports": [], "routes": [], "assets": [], "riskZones": [] },
             "regional": { "ports": [], "routes": [], "assets": [], "riskZones": [] },
             "airFreight": { "ports": [], "routes": [], "assets": [], "riskZones": [] }
        }
    }

def get_live_supply_chain_data():
    air_freight_data, air_alerts = mcp_agent.get_live_air_state()
    
    # SEA DATA
    sea_freight_data = {
        "ports": [
            {"id": "sh", "name": "Shanghai", "lat": 31.23, "lng": 121.47, "risk": 15},
            {"id": "la", "name": "Los Angeles", "lat": 33.7, "lng": -118.29, "risk": 20},
            {"id": "rot", "name": "Rotterdam", "lat": 51.90, "lng": 4.48, "risk": 10},
            {"id": "sin", "name": "Singapore", "lat": 1.29, "lng": 103.85, "risk": 5},
            {"id": "nyk", "name": "Newark", "lat": 40.69, "lng": -74.17, "risk": 25},
        ],
        "routes": [
            {"id": "SH-LA", "start": [121.47, 31.23], "end": [-118.29, 33.7]},
            {"id": "RO-LA", "start": [4.48, 51.90], "end": [-118.29, 33.7]},
            {"id": "SG-LA", "start": [103.85, 1.29], "end": [-118.29, 33.7]},
            {"id": "SH-RO", "start": [121.47, 31.23], "end": [4.48, 51.90]},
            {"id": "RO-NK", "start": [4.48, 51.90], "end": [-74.17, 40.69]},
        ],
        "assets": [
            {"name": "Vessel Alpha", "cargo": "Electronics", "routeId": "SH-LA", "progress": 0.45, "track": 90, "capacity": "12000 TEU", "is_live": False},
            {"name": "Vessel Bravo", "cargo": "Apparel", "routeId": "RO-LA", "progress": 0.75, "track": 85, "capacity": "8500 TEU", "is_live": False},
            {"name": "Vessel Charlie", "cargo": "Raw Goods", "routeId": "SG-LA", "progress": 0.20, "track": 260, "capacity": "15000 TEU", "is_live": False},
            {"name": "Vessel Delta", "cargo": "Machinery", "routeId": "SH-RO", "progress": 0.85, "track": 275, "capacity": "9000 TEU", "is_live": False},
            {"name": "Vessel Echo", "cargo": "Pharma", "routeId": "RO-NK", "progress": 0.50, "track": 310, "capacity": "5000 TEU", "is_live": False},
            {"name": "Vessel Foxtrot", "cargo": "Auto Parts", "routeId": "SH-LA", "progress": 0.80, "track": 95, "capacity": "11000 TEU", "is_live": False},
            {"name": "Vessel Golf", "cargo": "Grain", "routeId": "SH-RO", "progress": 0.30, "track": 45, "capacity": "7000 TEU", "is_live": False},
            {"name": "Vessel Hotel", "cargo": "Furniture", "routeId": "RO-LA", "progress": 0.10, "track": 180, "capacity": "6000 TEU", "is_live": False},
            {"name": "Vessel India", "cargo": "Oil", "routeId": "SG-LA", "progress": 0.60, "track": 270, "capacity": "20000 TEU", "is_live": False},
            {"name": "Vessel Juliet", "cargo": "Coal", "routeId": "SH-LA", "progress": 0.25, "track": 90, "capacity": "14000 TEU", "is_live": False},
            {"name": "Vessel Kilo", "cargo": "Steel", "routeId": "SH-RO", "progress": 0.55, "track": 275, "capacity": "10000 TEU", "is_live": False},
            {"name": "Vessel Lima", "cargo": "Chemicals", "routeId": "RO-NK", "progress": 0.90, "track": 310, "capacity": "5500 TEU", "is_live": False},
            {"name": "Vessel Mike", "cargo": "Vehicles", "routeId": "RO-LA", "progress": 0.40, "track": 85, "capacity": "9000 TEU", "is_live": False},
        ],
        "riskZones": []
    }
    
    # LAND DATA
    land_freight_data = {
        "ports": [
            {"id": "la_dc", "name": "Los Angeles DC", "lat": 34.05, "lng": -118.24, "risk": 10},
            {"id": "chi_dc", "name": "Chicago DC", "lat": 41.87, "lng": -87.62, "risk": 25},
            {"id": "ny_dc", "name": "Newark Hub", "lat": 40.69, "lng": -74.17, "risk": 5},
            {"id": "dal_dc", "name": "Dallas DC", "lat": 32.77, "lng": -96.79, "risk": 5},
        ],
        "routes": [
            {"id": "LA-CHI", "start": [-118.24, 34.05], "end": [-87.62, 41.87]},
            {"id": "NY-CHI", "start": [-74.17, 40.69], "end": [-87.62, 41.87]},
            {"id": "LA-DAL", "start": [-118.24, 34.05], "end": [-96.79, 32.77]},
        ],
        "assets": [
            {"name": "Truck 405A", "cargo": "Apparel", "routeId": "LA-CHI", "progress": 0.6, "track": 70, "is_live": False},
            {"name": "Truck 102B", "cargo": "Electronics", "routeId": "NY-CHI", "progress": 0.3, "track": 280, "is_live": False},
            {"name": "Truck 202C", "cargo": "Auto Parts", "routeId": "LA-DAL", "progress": 0.8, "track": 110, "is_live": False},
        ],
        "riskZones": []
    }
    
    kpis = {
        "inStock": {"value": f"{random.randint(92, 98)}%"},
        "onTime": {"value": f"{random.randint(90, 96)}%"},
        "turnover": {"value": f"{random.uniform(4.5, 5.5):.1f}x"},
        "lostSales": {"value": f"${random.uniform(0.1, 0.3):.1f}M"},
        "reorderPoint": {"value": f"{random.randint(18, 22)}%"}
    }
    
    # Check for active event
    new_event = get_simulated_world_event()
    global_alerts = [{"type": "info", "text": "System nominal. All sea routes clear."}]
    
    if new_event:
        if new_event["action"]["id"] == "mcp-reroute-1":
            # Air alert -> Inject into Air Data
            air_alerts.insert(0, new_event)
            air_freight_data["riskZones"].append(
                {"id": "risk-storm-1", "name": "Alaskan Storm System", "lat": 55, "lng": -160, "severity": 0.8}
            )
            # INJECT SIMULATED REROUTE (YELLOW)
            air_freight_data["routes"].append({
                "id": "HKG-LAX-REROUTE", 
                "start": [113.91, 22.30], "end": [-118.40, 33.94], 
                "color": "yellow"
            })
            # INJECT SIMULATED ASSET
            air_freight_data["assets"].append({
                "id": "SIM-REROUTE", "name": "Simulated Reroute", 
                "cargo": "Priority Goods", "routeId": "HKG-LAX-REROUTE", 
                "is_live": False, "progress": 0.6, "speed": 550, "capacity": 90, "track": 100
            })
        else:
            # Sea/Land alert -> Inject into Global Alerts
            global_alerts.insert(0, new_event)
    
    alerts = {
        "global": global_alerts,
        "regional": [{"type": "warning", "text": "Chicago DC approaching 85% capacity."}],
        "airFreight": air_alerts
    }
    
    # Charts
    rev_data = [random.randint(85, 115) for _ in range(5)]
    charts = {
        "demand": {
            "labels": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12"],
            "actual": [random.randint(40, 60) for _ in range(12)],
            "forecast": [random.randint(40, 60) for _ in range(12)],
            "annotation": None
        },
        "revenue": {
            "revenueData": rev_data,
            "marginData": [random.randint(20, 45) for _ in range(5)],
            "colors": ["green" if x >= 100 else "red" for x in rev_data]
        }
    }
    
    map_data = {
        "global": sea_freight_data,
        "regional": land_freight_data,
        "airFreight": air_freight_data
    }
    
    return {
        "kpis": kpis,
        "alerts": alerts,
        "charts": charts,
        "mapData": map_data
    }


# ==============================================================================
# 6. API ENDPOINTS
# ==============================================================================

@app.route('/api/v1/state', methods=['GET'])
def get_state():
    return jsonify(get_live_supply_chain_data())

@app.route('/api/v1/trigger-event', methods=['POST'])
def trigger_event():
    data = request.json
    get_simulated_world_event(mapView=data.get("mapView", "global"), force_new=True)
    return jsonify(get_live_supply_chain_data())

@app.route('/api/v1/simulate', methods=['POST'])
def post_simulate():
    try:
        data = request.json
        use_optimization = data.get('optimize', False)
        scenario_type = data.get('scenario', 'none')
        
        try:
            result = get_live_supply_chain_data()
        except Exception as e:
            print(f"SIMULATION WARNING: {e}")
            result = get_static_fallback_data()

        # Apply Scenario Logic
        if scenario_type == 'port-strike':
            result['kpis']['lostSales'] = {"value": "$4.2M", "trendSymbol": "▲", "trendClass": "down"}
            if 'global' in result.get('alerts', {}):
                result['alerts']['global'].insert(0, {"type": "critical", "text": "SIMULATION: Port Strike impact high. Rerouting recommended."})
            if 'revenue' in result.get('charts', {}):
                result['charts']['revenue']['revenueData'] = [60, 50, 40, 80, 70]
                result['charts']['revenue']['colors'] = ["red", "red", "red", "red", "red"]
            
        elif scenario_type == 'geopolitical':
             result['kpis']['turnover'] = {"value": "3.1x", "trendSymbol": "▼", "trendClass": "down"}
             if 'global' in result.get('alerts', {}):
                result['alerts']['global'].insert(0, {"type": "critical", "text": "SIMULATION: Suez blockage. 14-day delay projected."})

        # vLLM Metrics Injection
        if use_optimization:
            time.sleep(0.5)
            # High throughput for vLLM
            total_tokens = random.randint(3500, 4200)
            tps = random.randint(110, 140)
            result['performance'] = { 
                "mode": "Distributed (vLLM)", 
                "cacheRate": f"{random.randint(89, 96)}%", 
                "latency": f"{random.uniform(0.3, 0.6):.2f}s", 
                "costSavings": f"{random.randint(45, 60)}%",
                "totalTokens": f"{total_tokens}",
                "tokensPerSecond": f"{tps} t/s"
            }
        else:
            time.sleep(2.5)
            # Lower throughput for Standard
            total_tokens = random.randint(3500, 4200) # Same workload
            tps = random.randint(12, 25) # Slower processing
            result['performance'] = { 
                "mode": "Standard Monolithic", 
                "cacheRate": "0%", 
                "latency": f"{random.uniform(2.8, 3.5):.2f}s", 
                "costSavings": "0%",
                "totalTokens": f"{total_tokens}",
                "tokensPerSecond": f"{tps} t/s"
            }

        return jsonify(result)
        
    except Exception as e:
        print(f"CRITICAL SERVER ERROR: {e}")
        return jsonify({
            "error": str(e), 
            "performance": { "mode": "Error Recovery", "cacheRate": "N/A", "latency": "0.0s", "costSavings": "0%" }
        }), 200

@app.route('/api/v1/chat', methods=['POST'])
def post_chat():
    data = request.json
    query = data.get("input", "")
    query_lower = query.lower()
    js_history = data.get("chat_history", [])
    
    vllm_prefix = f"[vLLM-D | Latency: {random.uniform(0.01, 0.05):.3f}s]: "
    
    for forbidden in GUARDRAIL_KEYWORDS:
        if forbidden in query_lower:
            return jsonify({"answer": vllm_prefix + "I am restricted to Supply Chain topics only. I cannot answer questions about general knowledge, food, or weather."})

    if agent_executor:
        try:
            print(f"Executing Real RAG Agent on: '{query}'")
            chat_history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in js_history])
            response = agent_executor.invoke({"input": query, "chat_history": chat_history_str})
            
            if "routeData" in response['output']:
                 try:
                     json_match = re.search(r'\{.*\}', response['output'], re.DOTALL)
                     if json_match:
                         return jsonify(json.loads(json_match.group(0)))
                 except: pass

            return jsonify({"answer": vllm_prefix + response['output']})
        except Exception as e:
            print(f"Real AI Error: {e}")

    if "route" in query_lower:
         return jsonify({
            "answer": "Calculated optimized route avoiding tolls (Mock).",
            "routeData": {"type": "optimized_land_route", "coordinates": [[34.05, -118.24], [41.87, -87.62]], "color": "#FFC300"}
        })
    elif "risk" in query_lower:
        ans = "The 'Alaskan Storm System' is active (Severity 0.8). Risk analysis suggests immediate rerouting."
    elif "inventory" in query_lower:
        ans = "Los Angeles DC is at 92% capacity (High Risk)."
    else:
        ans = "I am processed by the vLLM distributed engine. I can assist with risk analysis and routing."

    return jsonify({"answer": vllm_prefix + ans})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)

