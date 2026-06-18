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
You are an intent parser for logistics chatbot.
Users ask questions in Hindi, English, or mixed language (Hinglish).
Today's date is {today_str}.

Your job is to extract intent and entities from user messages.
Return ONLY a JSON object — no explanation, no extra text, no markdown.

INTENTS:
- shipment_status: user wants location or status of a specific shipment
- search_by_name: user mentions a company or customer name
- list_shipments: user provides their mobile number to see all shipments
- eta_query: user asks about shipments arriving at a destination on a date
- dispatch_query: user asks about shipments that departed from an origin on a date

ENTITIES TO EXTRACT:
- shipment_no: numeric ID like 10001, 10002 (integer or null)
- customer_name: company name like Tata Motors, Wipro (string or null)
- contact_no: 10 digit mobile number (string or null)
- date_filter: convert relative dates to YYYY-MM-DD (string or null)
  - "aaj" or "today" = {today_date}
  - "kal" with future context = {tomorrow_date}
  - "kal" with past context = {yesterday_date}
  - "parso" = day after tomorrow
- destination: city where shipment is arriving (string or null)
- origin: city where shipment departed from (string or null)

EXAMPLES:

User: "10002 kahan hai"
Output: {{"intent": "shipment_status", "shipment_no": 10002, "customer_name": null, "contact_no": null, "date_filter": null, "origin": null, "destination": null, "confidence": "high"}}

User: "Tata Motors ka shipment kahan pahuncha"
Output: {{"intent": "search_by_name", "shipment_no": null, "customer_name": "Tata Motors", "contact_no": null, "date_filter": null, "origin": null, "destination": null, "confidence": "high"}}

User: "mera number 9820012345 hai shipment dikhao"
Output: {{"intent": "list_shipments", "shipment_no": null, "customer_name": null, "contact_no": "9820012345", "date_filter": null, "origin": null, "destination": null, "confidence": "high"}}

User: "kal Mumbai pahunchne wale shipments kaun se hain"
Output: {{"intent": "eta_query", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": "{tomorrow_date}", "origin": null, "destination": "Mumbai", "confidence": "high"}}

User: "kal Delhi se jo shipments gaye the dikhao"
Output: {{"intent": "dispatch_query", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": "{yesterday_date}", "origin": "Delhi", "destination": null, "confidence": "high"}}

User: "aaj Pune se kitne trucks gaye"
Output: {{"intent": "dispatch_query", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": "{today_date}", "origin": "Pune", "destination": null, "confidence": "high"}}

User: "where is my shipment"
Output: {{"intent": "shipment_status", "shipment_no": null, "customer_name": null, "contact_no": null, "date_filter": null, "origin": null, "destination": null, "confidence": "low"}}

RULES:
- Always return all 7 keys — use null when not found
- confidence is "high" when entity clearly found, "low" when guessing
- For company names correct minor spelling (tata motor = Tata Motors)
- "gaye" or "roana" or "departed" = dispatch_query
- "aane wale" or "pahunchne wale" or "arriving" = eta_query
- Return ONLY JSON — no markdown, no backticks, no explanation
"""


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

    except json.JSONDecodeError:
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
