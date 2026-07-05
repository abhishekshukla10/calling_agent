import streamlit as st
from intent_parser import parse_intent
from response_generator import generate_response
from caller import call_driver


def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 🔐 Demo Access")
    pwd = st.text_input("Enter password", type="password")
    if st.button("Enter"):
        if pwd == "Newtrack@123":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False


if not check_password():
    st.stop()

st.set_page_config(
    page_title="Shipment Assistant",
    page_icon="🚚",
    layout="centered"
)

# Session state setup
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_shipment" not in st.session_state:
    st.session_state.current_shipment = None
if "prefill" not in st.session_state:
    st.session_state.prefill = None
if "last_shipment" not in st.session_state:
    st.session_state.last_shipment = None
if "last_call_shipment" not in st.session_state:
    st.session_state.last_call_shipment = None

# Header
st.markdown("### 🚚 Shipment Assistant")
st.caption("Hindi ya English — dono chalega · Powered by AI")
st.divider()

# Sidebar
with st.sidebar:
    st.markdown("### Try these")
    st.caption("Click any to load into chat")
    st.divider()

    scenarios = {
        "🟢 In transit — 10001": "10001 kahan hai?",
        "🟡 Delayed — 10011": "10011 ka status batao",
        "🔴 Stopped — 10021": "10021 truck update do",
        "📋 List all shipments": "mera number 9820012345 hai",
        "🔍 Search by name": "Tata Motors ka shipment kahan hai",
        "📅 ETA query": "19 June ko kaun se shipments pahuchenge",
        "🚚 Dispatch query": "18 June ko Mumbai se kya gaya",
        "❓ Vague query": "where is my shipment?"
    }

    for label, query in scenarios.items():
        if st.button(label, use_container_width=True):
            st.session_state.prefill = query

    st.divider()
    if st.button("🗑 Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.current_shipment = None
        st.session_state.prefill = None
        st.session_state.last_shipment = None
        st.session_state.last_call_shipment = None
        st.rerun()

# Welcome message
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(
            "Hello! I can help you track shipments — "
            "share a **shipment number**, **mobile number**, or **company name**. "
            "Hindi ya English — dono chalega! 🙏"
        )

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle prefill from sidebar buttons
prompt = None
if st.session_state.prefill:
    prompt = st.session_state.prefill
    st.session_state.prefill = None

# Handle manual input
manual = st.chat_input("Try: '10002 kahan hai' or your mobile number")
if manual:
    prompt = manual

# Process prompt
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Checking shipment..."):
        intent = parse_intent(prompt)

        if intent.get("shipment_no"):
            st.session_state.current_shipment = intent["shipment_no"]
        elif st.session_state.current_shipment and intent.get("intent") == "shipment_status":
            intent["shipment_no"] = st.session_state.current_shipment

        response, shipment_data = generate_response(
            intent,
            st.session_state.messages[-6:]
        )

        if shipment_data:
            st.session_state.last_shipment = shipment_data

    with st.chat_message("assistant", avatar="🚚"):
        st.markdown(response, unsafe_allow_html=False)

    st.session_state.messages.append(
        {"role": "assistant", "content": response})

    st.rerun()

# Show Call Driver button
shipment = st.session_state.get("last_shipment")
if shipment:
    status = shipment.get("status", "")
    delay_hours = shipment.get("delay_hours", 0)
    if status in ["delayed", "stopped"] and delay_hours >= 4:
        st.warning(
            f"🚨 Shipment #{shipment.get('shipment_no')} delayed by {delay_hours} hours. Do you want to call the driver?")
        if st.button("📞 Call Driver", key=f"call_{shipment.get('shipment_no')}"):
            with st.spinner("Connecting to driver..."):
                result = call_driver(
                    truck_no=shipment.get("truck_no"),
                    driver_mobile=shipment.get("driver_mobile"),
                    current_location=shipment.get("current_location"),
                    delay_hours=delay_hours,
                    destination=shipment.get("destination"),
                    shipment_no=shipment.get("shipment_no")
                )
            if result.get("success"):
                st.success("✅ Driver call initiated!")
                st.session_state.messages.append(
                    {"role": "assistant", "content": "✅ Driver call initiated. Click 'Check Call Result' after call ends."})
                st.session_state.last_call_shipment = shipment.get(
                    "shipment_no")
                st.session_state.last_shipment = None
            else:
                st.error(f"❌ Call failed: {result.get('error')}")

# Check Call Result button
if st.session_state.get("last_call_shipment"):
    if st.button("🔄 Check Call Result"):
        from db import get_latest_call_log
        call_result = get_latest_call_log(
            st.session_state.last_call_shipment)
        if call_result and call_result.get("call_status"):
            result_msg = f"""📞 **Call Completed — Result Captured**

🔍 **Reason:** {call_result.get('delay_reason', 'Unknown')}
🕐 **Updated ETA:** {call_result.get('updated_eta', 'Not provided')}
🆘 **Assistance:** {'Yes ⚠️' if call_result.get('assistance_required') else 'No ✅'}
📋 **Status:** {call_result.get('call_status')}"""
            st.success(result_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": result_msg})
            st.session_state.last_call_shipment = None
        else:
            st.warning("Call still in progress — try again in a few seconds.")
