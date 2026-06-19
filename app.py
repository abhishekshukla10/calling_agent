import streamlit as st
from intent_parser import parse_intent
from response_generator import generate_response

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
        "🟡 Delayed — 10002": "10002 ka status batao",
        "🔴 Stopped — 10004": "10004 truck update do",
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
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Run pipeline
    with st.spinner("Checking shipment..."):
        intent = parse_intent(prompt)

        # Carry forward shipment number across turns
        if intent.get("shipment_no"):
            st.session_state.current_shipment = intent["shipment_no"]
        elif st.session_state.current_shipment and intent.get("intent") == "shipment_status":
            intent["shipment_no"] = st.session_state.current_shipment

        response = generate_response(
            intent,
            st.session_state.messages[-6:]
        )

    # Show bot response
    with st.chat_message("assistant", avatar="🚚"):
        st.markdown(response, unsafe_allow_html=False)
    st.session_state.messages.append(
        {"role": "assistant", "content": response})

    st.rerun()
