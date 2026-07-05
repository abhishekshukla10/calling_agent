import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID")
BOLNA_API_KEY = os.getenv("BOLNA_API_KEY")


def call_driver(truck_no, driver_mobile, current_location, delay_hours, destination, shipment_no=None):

    # Layer 2 — Validation
    if not all([truck_no, driver_mobile, current_location, destination]):
        return {
            "success": False,
            "error": "Mandatory information is missing"
        }

    # Layer 3 — Build payload
    payload = {
        "agent_id": BOLNA_AGENT_ID,
        "recipient_phone_number": driver_mobile,
        "user_data": {
            "shipment_no": str(shipment_no) if shipment_no else "",
            "truck_no": truck_no,
            "last_location": current_location,
            "delay_hours": delay_hours,
            "destination": destination
        }
    }

    # Layer 4 — Send + handle response
    try:
        response = requests.post(
            url="https://api.bolna.ai/call",
            headers={
                "Authorization": f"Bearer {BOLNA_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )

        data = response.json()
        print("BOLNA RESPONSE:", data)
        bolna_call_id = data.get("execution_id")
        status_code = response.status_code

        if status_code == 200:
            return {
                "success": True,
                "bolna_call_id": bolna_call_id,
                "message": "call successful"
            }
        else:
            return {
                "success": False,
                "message": "call not successful",
                "error": response.text,
                "status_code": status_code
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Connection time out"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# test block
if __name__ == "__main__":
    print("caller.py loaded successfully")
    print(f"Agent ID: {BOLNA_AGENT_ID}")
    print(f"API Key exists: {bool(BOLNA_API_KEY)}")
