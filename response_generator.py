import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

from db import (
    get_shipment,
    get_events,
    get_shipments_by_contact,
    get_shipments_by_customer_name,
    get_shipments_by_eta,
    get_shipments_by_dispatch
)


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


def clean_date_query_results(shipments, timestamp_field):
    """Format datetime field in a list of shipment dicts"""
    cleaned = []
    for s in shipments:
        clean_s = dict(s)  # copy the dict
        clean_s[timestamp_field] = format_datetime(s.get(timestamp_field))
        cleaned.append(clean_s)
    return cleaned


def get_system_prompt():
    return """
You are a smart, professional shipment tracking assistant.
You understand Hindi, English, and Hinglish equally well.

PERSONALITY:
- Professional but warm
- Concise and structured
- Empathetic when shipment is delayed or stopped
- Proactive — mention important issues even if not asked

STATUS EMOJIS:
- in_transit  → In transit ✅
- delayed     → Delayed ⚠
- stopped     → Stopped 🔴
- delivered   → Delivered ✅
- loading     → Loading 🔄

RESPONSE RULES:
- Use ONLY the data provided — never guess or make up data
- If shipments list is empty → tell user no shipments found, ask to verify
- If shipment delayed → show reason + revised ETA
- If shipment stopped > 2 hours → flag proactively
- If ETA within 2 hours → highlight prominently
- If data missing → say information not available
- For confidence=low → ask for shipment number, contact number, or company name
- Keep language same as user query — Hindi or English
- search_by_name matches shipper OR customer — if data returned it IS valid
- STRICTLY follow the output format instructions given at the end of each message
"""


def build_context(intent_data):
    intent = intent_data.get("intent")

    if intent == "shipment_status" and intent_data.get("shipment_no"):
        shipment = get_shipment(intent_data["shipment_no"])
        events = get_events(intent_data["shipment_no"])
        return {
            "shipment": clean_shipment_data(shipment),
            "events": clean_events_data(events)
        }

    elif intent == "list_shipments" and intent_data.get("contact_no"):
        shipments = get_shipments_by_contact(intent_data["contact_no"])
        return {"shipments": shipments}

    elif intent == "search_by_name" and intent_data.get("customer_name"):
        shipments = get_shipments_by_customer_name(
            intent_data["customer_name"])
        return {
            "search_term": intent_data["customer_name"],
            "note": "Search matches either shipper_name (who sent it) or customer_name (who receives it)",
            "shipments": shipments
        }

    elif intent == "eta_query":
        shipments = get_shipments_by_eta(
            intent_data.get("date_filter"),
            intent_data.get("destination")
        )
        cleaned_shipments = clean_date_query_results(
            shipments, "eta_timestamp")
        return {
            "query_type": "eta_query",
            "date_searched": intent_data.get("date_filter"),
            "destination_searched": intent_data.get("destination"),
            "note": "These shipments are predicted to arrive on this date based on current ETA. Past deliveries are not included in this search.",
            "shipments": cleaned_shipments
        }

    elif intent == "dispatch_query":
        shipments = get_shipments_by_dispatch(
            intent_data.get("date_filter"),
            intent_data.get("origin")
        )
        cleaned_shipments = clean_date_query_results(
            shipments, "event_timestamp")
        return {
            "query_type": "dispatch_query",
            "date_searched": intent_data.get("date_filter"),
            "origin_searched": intent_data.get("origin"),
            "shipments": cleaned_shipments
        }

    else:
        return {"message": "insufficient information"}


def get_format_instruction(intent_data, context):
    intent = intent_data.get("intent")
    shipments = context.get("shipments", [])

    # Multiple shipments
    if isinstance(shipments, list) and len(shipments) > 1:
        return """
        STRICT FORMAT — multiple shipments found.
        Start with: "Found X shipments. Here are the details:"
        Then list each one exactly like this:
        1. 📦 #[no] | [origin] → [destination] | [status emoji] | [shipper] → [customer]
        2. 📦 #[no] | [origin] → [destination] | [status emoji] | [shipper] → [customer]
        End with: "⚠ Shipments #[nos] need attention." (if any stopped/delayed)
        Then: "Want details on any specific shipment?"
        NEVER use paragraphs. NEVER use bullet points.
        """

    # Single shipment
    elif intent == "shipment_status" and context.get("shipment"):
        return """
        STRICT FORMAT — single shipment:

        📦 #[no] | [origin] → [destination] | [status emoji]

        📍 [current_location]
        🕐 ETA: [DD Mon YYYY, HH:MM AM/PM]
        🏢 [shipper] → [customer]

        Last update: [most recent event] — [DD Mon, HH:MM AM/PM]
        ⚠ Alerts: [reason if delayed/stopped, else None]

        Maximum 6 lines total. No extra fields. No paragraphs.
        """

    # Insufficient info / confidence low
    else:
        return """
        Politely ask for shipment number, contact number, or company name.
        Keep it to 2 lines maximum.
        """


# response_generator.py

def generate_response(intent_data, conversation_history):
    context = build_context(intent_data)

    messages = [
        {"role": "system", "content": get_system_prompt()},
        *conversation_history[-6:],
        {"role": "user", "content": f"""
        User Intent: {json.dumps(intent_data)}
        Shipment Data: {json.dumps(context)}

        {get_format_instruction(intent_data, context)}
                """}
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            return "I'm experiencing high demand right now. Please try again in a few minutes. 🙏"
        return "Something went wrong. Please try again."


# Test block
if __name__ == "__main__":
    from intent_parser import parse_intent

    test_queries = [
        "Tata Motors ka shipment dikhao",  # multiple shipments — format test
        "18 June ko Mumbai se kya gaya",


    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        intent = parse_intent(query)
        print(f"Intent: {intent}")
        response = generate_response(intent, [])
        print(f"Response: {response}")
