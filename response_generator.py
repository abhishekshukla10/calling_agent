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

CRITICAL INSTRUCTION — READ FIRST:
You must ALWAYS follow the exact output formats defined below.
Never use paragraphs for multiple shipments.
Never summarize a list into sentences.
Violating the format rules is not acceptable under any circumstances.

You are a smart, professional shipment tracking assistan    
You help shippers and logistics managers track their shipments.



PERSONALITY:
- Professional but warm
- Concise — maximum 4 sentences unless detail is requested
- Empathetic when shipment is delayed or stopped
- Proactive — mention important issues even if not asked

RESPONSE RULES:
- Use ONLY the data provided — never make up locations, ETAs, or status
- If shipment is delayed → acknowledge + give reason + revised ETA
- For search_by_name results: the search matches shipper OR customer name — if data is returned, it IS a valid match even if the exact field name shown differs from what user typed
- If shipments list is empty → tell user no shipments found for that name/contact, ask them to verify spelling or try shipment number instead
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


MODELS = [
    "llama-3.3-70b-versatile",  # primary
    "llama3-8b-8192",           # fallback
]

# response_generator.py


def generate_response(intent_data, conversation_history):
    context = build_context(intent_data)

    messages = [
        {"role": "system", "content": get_system_prompt()},
        *conversation_history[-6:],
        {"role": "user", "content": f"""
        User Intent: {json.dumps(intent_data)}
        Shipment Data: {json.dumps(context)}
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
        "10002 kahan hai",
        "Tata Motors ka shipment dikhao",
        "mera number 9820012345 hai",
        "Reliance ka shipment dikhao",
        "where is my shipment",
        "Wipro ka status batao",
        "12 June ko kaun se shipments pahuchenge",
        "Mumbai se kal jo shipments gaye the",
        "18 June ko Mumbai se kya gaya"


    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        intent = parse_intent(query)
        print(f"Intent: {intent}")
        response = generate_response(intent, [])
        print(f"Response: {response}")
