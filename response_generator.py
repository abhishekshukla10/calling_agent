import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from db import get_shipment, get_events, get_shipments_by_contact

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# Data cleaning functions-


def format_datetime(dt):
    """Convert datetime object to readable string"""
    if dt is None:
        return "Not available"
    return dt.strftime("%d %b %Y, %I:%M %p")
    # Output: "12 Jun 2026, 05:48 AM"


def clean_shipment_data(shipment):
    """Make shipment dict LLM-friendly"""
    if not shipment:
        return None
    return {
        "shipment_no": shipment["shipment_no"],
        "shipper": shipment["shipper_name"],
        "customer": shipment["customer_name"],
        "origin": shipment["origin"],
        "destination": shipment["destination"],
        "status": shipment["status"],
        "truck_no": shipment["truck_no"],
        "current_location": shipment.get("current_location", "Not available"),
        "distance_remaining_km": shipment.get("distance_remaining", "Not available"),
        "eta": format_datetime(shipment.get("eta_timestamp"))
    }


def clean_events_data(events):
    if not events:
        return []

    # Step 1: Reverse to chronological order
    chronological = events[::-1]

    # Step 2: Clean each event one by one
    cleaned_events = []

    for e in chronological:
        clean_event = {
            "event": e["event_type"],
            "location": e["location"],
            "notes": e["notes"],
            "time": format_datetime(e["event_timestamp"])
        }
        cleaned_events.append(clean_event)

    return cleaned_events


def get_system_prompt():
    return """
You are intelligent shipment assistant.
You help shippers and logistics managers track their shipments.

PERSONALITY:
- Professional but warm
- Concise — maximum 4 sentences unless detail is requested
- Empathetic when shipment is delayed or stopped
- Proactive — mention important issues even if not asked

RESPONSE RULES:
- Use ONLY the data provided — never make up locations, ETAs, or status
- If shipment is delayed → acknowledge + give reason + revised ETA
- If shipment stopped > 2 hours → flag it proactively
- If ETA is within 2 hours → highlight it prominently
- If data is missing → say "information not available" — never guess
- For confidence=low queries → politely ask for shipment number or contact number
- Keep responses in the same language as user query (Hindi or English)

STATUS MEANINGS:
- in_transit → shipment is moving normally
- delayed → shipment is behind schedule
- stopped → shipment has halted unexpectedly
- delivered → shipment has reached destination
- loading → shipment is being prepared

ESCALATION:
- If user sounds frustrated across multiple messages → offer to connect to support team
"""


def generate_response(intent_data, conversation_history):

    # Step 1: Fetch and clean data based on intent
    context = build_context(intent_data)

    # Step 2: Build messages for Groq
    messages = [
        {"role": "system", "content": get_system_prompt()},
        *conversation_history[-6:],  # last 6 turns for memory
        {"role": "user", "content": f"""
        User Intent: {json.dumps(intent_data)}
        Shipment Data: {json.dumps(context)}
        """}
    ]

    # Step 3: Call Groq
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=300
    )

    return response.choices[0].message.content.strip()


def build_context(intent_data):
    """Fetch relevant data based on intent"""
    intent = intent_data.get("intent")

    if intent == "shipment_status" and intent_data.get("shipment_no"):
        shipment = get_shipment(intent_data["shipment_no"])
        events = get_events(intent_data["shipment_no"])
        return {
            "shipment": clean_shipment_data(shipment),
            "events": clean_events_data(events)
        }

    elif intent == "search_by_name" and intent_data.get("customer_name"):
        # Search by customer name — returns list
        return {
            "message": f"Searching for shipments for {intent_data['customer_name']}",
            "note": "customer name search not yet implemented in db.py"
        }

    elif intent == "list_shipments" and intent_data.get("contact_no"):
        shipments = get_shipments_by_contact(intent_data["contact_no"])
        return {"shipments": shipments}

    elif intent in ["eta_query", "dispatch_query"]:
        return {
            "message": "Date based search",
            "date_filter": intent_data.get("date_filter"),
            "origin": intent_data.get("origin"),
            "destination": intent_data.get("destination")
        }

    else:
        return {"message": "insufficient information"}


# Test block
if __name__ == "__main__":
    from intent_parser import parse_intent

    test_queries = [
        "10002 kahan hai",
        "Tata Motors ka shipment dikhao",
        "mera number 9820012345 hai",
        "where is my shipment"
    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        intent = parse_intent(query)
        print(f"Intent: {intent}")
        response = generate_response(intent, [])
        print(f"Response: {response}")
