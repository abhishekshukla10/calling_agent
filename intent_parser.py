import os
import json
from datetime import datetime, timedelta
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_system_prompt():
    today = datetime.now()
    today_str = today.strftime("%A, %d %B %Y")
    today_date = today.strftime("%Y-%m-%d")
    tomorrow_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    return f"""
You are an intent parser for a logistics chatbot.
Users ask questions in Hindi, English, or Hinglish.
Today's date is {today_str}.

Your job: extract intent and entities from user message.
Return ONLY valid JSON — no explanation, no extra text.

INTENTS:
- shipment_status: user wants status of a specific shipment
- search_by_name: user mentions a company or customer name
- list_shipments: user provides mobile number
- eta_query: user asks about shipments arriving on a date
- dispatch_query: user asks about shipments departed on a date

ENTITIES:
- shipment_no: integer like 10001 (or null)
- customer_name: company name like Tata Motors (or null)
- contact_no: 10 digit mobile number (or null)
- date_filter: resolve aaj/kal/parso to YYYY-MM-DD (or null)
  - aaj = {today_date}
  - kal future context = {tomorrow_date}
  - kal past context = {yesterday_date}
- origin: departure city (or null)
- destination: arrival city (or null)
- confidence: high or low

EXAMPLES:
User: "10002 kahan hai"
Output: {{"intent": "shipment_status", "shipment_no": 10002, "customer_name": null, "contact_no": null, "date_filter": null, "origin": null, "destination": null, "confidence": "high"}}

User: "Tata Motors ka shipment dikhao"
Output: {{"intent": "search_by_name", "shipment_no": null, "customer_name": "Tata Motors", "contact_no": null, "date_filter": null, "origin": null, "destination": null, "confidence": "high"}}

User: "where is my shipment"
Output: {{"intent": "shipment_status", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": null, "origin": null, "destination": null, "confidence": "low"}}

User: "kal Mumbai pahunchne wale shipments kaun se hain"
Output: {{"intent": "eta_query", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": "{tomorrow_date}", "origin": null, "destination": "Mumbai", "confidence": "high"}}

User: "kal Delhi se jo shipments gaye the dikhao"
Output: {{"intent": "dispatch_query", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": "{yesterday_date}", "origin": "Delhi", "destination": null, "confidence": "high"}}

RULES:
- Always return all 7 keys — null when not found
- confidence low when no entity found
- gaye/roana/departed = dispatch_query
- aane wale/pahunchne wale/arriving = eta_query
- Return ONLY JSON — no markdown, no backticks
"""

# intent_parser.py


def parse_intent(user_message):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=200
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    except Exception as e:
        return {
            "intent": "unknown",
            "shipment_no": None,
            "customer_name": None,
            "contact_no": None,
            "date_filter": None,
            "origin": None,
            "destination": None,
            "confidence": "low"
        }


# Test block
if __name__ == "__main__":
    test_queries = [
        "10002 kahan hai",
        "Tata Motors ka shipment dikhao",
        "mera number 9820012345 hai",
        "kal Mumbai pahunchne wale shipments",
        "kal Delhi se jo shipments gaye the",
        "aaj Pune se kitne trucks gaye",
        "where is my shipment"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print(f"Result: {parse_intent(query)}")
