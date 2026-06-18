# db.py
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def get_shipment(shipment_no):
    # Returns: all fields from shipments + trips joined
    # Output: dict with everything the LLM needs

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT s.*, t.current_location, t.lat, t.long, 
               t.distance_remaining, t.eta_timestamp
        FROM shipment s
        LEFT JOIN trips t ON s.shipment_no = t.shipment_no
        WHERE s.shipment_no = %s
    """, (shipment_no,))

    result = cur.fetchone()
    cur.close()
    conn.close()
    return dict(result) if result else None


def get_events(shipment_no):
    # Returns:  5 events chronologically
    # Output: list of dicts [{event_type, time, location, notes}]

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
    SELECT event_type, location, notes, event_timestamp
    FROM trip_events
    WHERE shipment_no = %s
    ORDER BY event_timestamp DESC
    LIMIT 5
    """, (shipment_no,))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in results]


# Function 3: Get all shipments by contact number
def get_shipments_by_contact(contact_no):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT shipment_no, shipper_name, customer_name, 
               origin, destination, status, truck_no
        FROM shipment
        WHERE contact_no = %s
    """, (contact_no,))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in results]


# Quick test
if __name__ == "__main__":
    print("=== Shipment 10001 ===")
    print(get_shipment(10001))
    print("\n=== Events for 10001 ===")
    print(get_events(10001))
    print("\n=== All shipments for 9820012345 ===")
    print(get_shipments_by_contact('9820012345'))
