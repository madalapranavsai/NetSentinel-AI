import os
import json
import pytest
import app.memory_store

def test_query_past_incidents_finds_match(tmp_path, monkeypatch):
    # Setup temp memory file path
    temp_file = tmp_path / "incident_memory.json"
    monkeypatch.setattr(app.memory_store, "MEMORY_FILE", str(temp_file))
    
    # Pre-populate with mock data
    mock_data = {
        "INC-12345": {
            "symptom": "High database connection count on read replica",
            "resolution": "Scale up read replica capacity to db.m5.xlarge"
        }
    }
    with open(temp_file, "w") as f:
        json.dump(mock_data, f, indent=2)
        
    # Query with symptom keywords
    result = app.memory_store.query_past_incidents(["replica", "connection"])
    assert "Incident: INC-12345" in result
    assert "High database connection count" in result
    assert "Scale up read replica" in result

def test_query_past_incidents_no_match(tmp_path, monkeypatch):
    temp_file = tmp_path / "incident_memory.json"
    monkeypatch.setattr(app.memory_store, "MEMORY_FILE", str(temp_file))
    
    mock_data = {
        "INC-12345": {
            "symptom": "OOMKilled on payments pod",
            "resolution": "Increase memory limits"
        }
    }
    with open(temp_file, "w") as f:
        json.dump(mock_data, f, indent=2)
        
    result = app.memory_store.query_past_incidents(["database"])
    assert result == "No matching past incidents found."

def test_save_incident_resolution_persists(tmp_path, monkeypatch):
    temp_file = tmp_path / "incident_memory.json"
    monkeypatch.setattr(app.memory_store, "MEMORY_FILE", str(temp_file))
    
    # Save a new incident
    app.memory_store.save_incident_resolution(
        "INC-999", 
        "CPU throttle on ingress gateway", 
        "Adjust CPU limit to 2 cores"
    )
    
    # Verify file content
    with open(temp_file, "r") as f:
        data = json.load(f)
        
    assert "INC-999" in data
    assert data["INC-999"]["symptom"] == "CPU throttle on ingress gateway"
    assert data["INC-999"]["resolution"] == "Adjust CPU limit to 2 cores"
