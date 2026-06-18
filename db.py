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


# Function 4: Get all shipments by customer name (fuzzy match)
def get_shipments_by_customer_name(search_name):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT shipment_no, shipper_name, customer_name, 
               origin, destination, status, truck_no
        FROM shipment
        WHERE customer_name ILIKE %s OR shipper_name ILIKE %s
    """, (f"%{search_name}%", f"%{search_name}%"))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in results]

# Function 5: Get shipments arriving on a specific date (future-facing only)


def get_shipments_by_eta(date_filter, destination=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if destination:
        cur.execute("""
            SELECT s.shipment_no, s.shipper_name, s.customer_name,
                   s.origin, s.destination, s.status, s.truck_no,
                   t.eta_timestamp, t.current_location
            FROM shipment s
            JOIN trips t ON s.shipment_no = t.shipment_no
            WHERE DATE(t.eta_timestamp) = %s
            AND s.destination ILIKE %s
        """, (date_filter, f"%{destination}%"))
    else:
        cur.execute("""
            SELECT s.shipment_no, s.shipper_name, s.customer_name,
                   s.origin, s.destination, s.status, s.truck_no,
                   t.eta_timestamp, t.current_location
            FROM shipment s
            JOIN trips t ON s.shipment_no = t.shipment_no
            WHERE DATE(t.eta_timestamp) = %s
        """, (date_filter,))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in results]

# Function 6: Get shipments departed on a specific date (origin-facing)


def get_shipments_by_dispatch(date_filter, origin=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if origin:
        cur.execute("""
            SELECT s.shipment_no, s.shipper_name, s.customer_name,
                   s.origin, s.destination, s.status, s.truck_no,
                   te.event_timestamp, te.location
            FROM shipment s
            JOIN trip_events te ON s.shipment_no = te.shipment_no
            WHERE te.event_type = 'departed'
            AND DATE(te.event_timestamp) = %s
            AND s.origin ILIKE %s
        """, (date_filter, f"%{origin}%"))
    else:
        cur.execute("""
            SELECT s.shipment_no, s.shipper_name, s.customer_name,
                   s.origin, s.destination, s.status, s.truck_no,
                   te.event_timestamp, te.location
            FROM shipment s
            JOIN trip_events te ON s.shipment_no = te.shipment_no
            WHERE te.event_type = 'departed'
            AND DATE(te.event_timestamp) = %s
        """, (date_filter,))

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
    print("\n=== Shipments for Tata ===")
    print(get_shipments_by_customer_name('Tata'))
    print("\n=== Search 'Reliance' (should now match shipper) ===")
    print(get_shipments_by_customer_name('Reliance'))

    print("\n=== Search 'Wipro' (should still match customer) ===")
    print(get_shipments_by_customer_name('Wipro'))

    print("\n=== Shipments arriving 2026-06-12 ===")
    print(get_shipments_by_eta('2026-06-12'))

    print("\n=== Shipments arriving 2026-06-12 in Mumbai ===")
    print(get_shipments_by_eta('2026-06-12', destination='Mumbai'))

    print("\n=== Shipments departed 2026-06-11 ===")
    print(get_shipments_by_dispatch('2026-06-11'))

    print("\n=== Shipments departed from Mumbai ===")
    print(get_shipments_by_dispatch('2026-06-11', origin='Mumbai'))
