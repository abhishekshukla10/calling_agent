import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from groq import Groq
import psycopg2

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def classify_transcript(transcript):
    """Send transcript to Groq → extract structured call outcome"""

    system_prompt = """
You are a logistics call analyzer. 
You will receive a transcript of a call between a control room agent and a truck driver.
Extract the following information and return ONLY valid JSON, nothing else.

Return exactly this structure:
{
    "call_status": "answered_resolved | wrong_driver | unclear_audio | no_answer | help_required",
    "delay_reason": "traffic | breakdown | unloading | unclear | none",
    "assistance_required": true or false,
    "new_truck_no": "truck number if driver said wrong truck, else null",
    "updated_eta": "eta in driver's own words if mentioned, else null"
}

Rules:
- call_status = help_required if driver asked for assistance
- call_status = wrong_driver if driver said this is not their truck
- call_status = unclear_audio if conversation was unclear
- call_status = answered_resolved for all normal completed calls
- assistance_required = true only if driver explicitly asked for help
- new_truck_no = fill only if driver gave a different truck number
- updated_eta = driver's exact words about arrival time
- Return ONLY JSON, no explanation, no markdown
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript:\n{transcript}"}
            ],
            temperature=0,
            max_tokens=200
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    except Exception as e:
        return {
            "call_status": "answered_resolved",
            "delay_reason": "unclear",
            "assistance_required": False,
            "new_truck_no": None,
            "updated_eta": None
        }


def save_to_call_logs(bolna_data, classified):
    """Write call result to Supabase call_logs table"""

    # Extract from Bolna's actual field names
    shipment_no = bolna_data.get("context_details", {}).get(
        "recipient_data", {}).get("shipment_no")
    truck_no = bolna_data.get("context_details", {}).get(
        "recipient_data", {}).get("truck_no")
    driver_mobile = bolna_data.get("user_number")
    duration = bolna_data.get("telephony_data", {}).get("duration")
    transcript = bolna_data.get("transcript")
    bolna_call_id = bolna_data.get("id")

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO call_logs (
            shipment_no,
            truck_no,
            driver_mobile,
            call_status,
            delay_reason,
            assistance_required,
            call_duration_sec,
            transcript,
            bolna_call_id,
            new_truck_no,
            updated_eta
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        shipment_no,
        truck_no,
        driver_mobile,
        classified.get("call_status"),
        classified.get("delay_reason"),
        classified.get("assistance_required"),
        duration,
        transcript,
        bolna_call_id,
        classified.get("new_truck_no"),
        classified.get("updated_eta")
    ))

    conn.commit()
    cur.close()
    conn.close()


@app.route("/bolna-webhook", methods=["POST"])
def receive_call():
    """Main webhook endpoint — Bolna POSTs here after every call"""

    try:
        data = request.json

        # Only process completed calls
        status = data.get("status", "")
        if status != "completed":
            print(f"Skipping webhook — status: {status}")
            return jsonify({"status": "skipped"}), 200

        print(f"Processing completed call: {data.get('id')}")

        # Step 1: Extract transcript
        transcript = data.get("transcript", "")

        # Step 2: Classify with Groq
        classified = classify_transcript(transcript)

        # Step 3: Save to call_logs
        save_to_call_logs(data, classified)

        print(f"Saved to call_logs — classified: {classified}")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
