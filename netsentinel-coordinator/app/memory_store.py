import json
import os
import threading
from typing import List

# Path to the memory store JSON file, kept in the root directory
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "incident_memory.json")
_memory_lock = threading.Lock()

def _initialize_memory():
    """Initializes the JSON file with a mock record if it doesn't exist."""
    with _memory_lock:
        if not os.path.exists(MEMORY_FILE):
            mock_record = {
                "INC-00001": {
                    "symptom": "OOMKilled event on payment pod",
                    "resolution": "Increase memory limit allocation in Helm chart to 4Gi"
                }
            }
            with open(MEMORY_FILE, "w") as f:
                json.dump(mock_record, f, indent=2)

def query_past_incidents(symptom_keywords: List[str]) -> str:
    """Searches the JSON file for any past incidents matching the keywords."""
    _initialize_memory()
    
    with _memory_lock:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    
    matches = []
    # Simple keyword search (case-insensitive) against the symptom text
    for inc_id, details in data.items():
        symptom_text = details.get("symptom", "").lower()
        if any(keyword.lower() in symptom_text for keyword in symptom_keywords):
            matches.append(
                f"Incident: {inc_id}\nSymptom: {details['symptom']}\nResolution: {details['resolution']}"
            )
            
    if matches:
        return "\n\n".join(matches)
    
    return "No matching past incidents found."

def save_incident_resolution(incident_id: str, symptom: str, resolution: str):
    """Appends a new resolved incident to the JSON store safely using thread lock."""
    _initialize_memory()
    
    with _memory_lock:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            
        data[incident_id] = {
            "symptom": symptom,
            "resolution": resolution
        }
        
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2)

# Ensure the file is created with the mock data when imported or run
_initialize_memory()

