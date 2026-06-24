
import json
import asyncio
from app.agent import netsentinel_coordinator

mock_alert = {
    "incident_id": "INC-84729",
    "timestamp": "2026-06-24T12:50:00Z",
    "cluster": "prod-cluster-us-east1",
    "namespace": "payment-processing",
    "pod": "payment-worker-7b94c8d-abcde",
    "container": "worker",
    "reason": "OOMKilled",
    "message": "Back-off restarting failed container",
    "status": "CrashLoopBackOff",
    "resource_limits": {
        "memory": "512Mi"
    },
    "current_usage": {
        "memory": "512Mi"
    }
}

async def main():
    prompt = f"Please assess this infrastructure alert:\n\n{json.dumps(mock_alert, indent=2)}"
    print("Sending alert to the coordinator agent...")
    
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        from app.agent import app
        
        print("\n--- Agent Assessment ---")
        runner = Runner(
            app=app, 
            session_service=InMemorySessionService(),
            auto_create_session=True
        )
        
        new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        
        print("\n--- Event Stream ---")
        async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=new_message):
            event_type = type(event).__name__
            print(f"\n[{event_type}]")
            if hasattr(event, "model_dump_json"):
                print(event.model_dump_json(indent=2))
            elif hasattr(event, "__dict__"):
                print(event.__dict__)
            else:
                print(event)
            print("-" * 40)
    except Exception as e:
        print(f"\n[Error] The agent failed to run: {e}")
        print("Note: If you see a DefaultCredentialsError, you must authenticate via 'gcloud auth login --update-adc'.")

if __name__ == "__main__":
    asyncio.run(main())
