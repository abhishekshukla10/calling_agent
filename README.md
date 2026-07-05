# 🚛 Agentic Caller — AI Voice Agent for Logistics

> When a truck is delayed, AI automatically calls the driver in Hindi, captures the reason, and updates the ops dashboard — without any human intervention.

---



## 🏗️ Architecture

```
User queries delayed shipment
        ↓
app.py — Streamlit UI
        ↓
intent_parser.py — Groq LLM (temp 0)
Extracts intent + shipment number
        ↓
response_generator.py
Fetches DB data · generates Hindi/English reply
        ↓
"Call Driver" button appears (delay ≥ 4 hours)
        ↓
caller.py — Bolna API
Validates · builds payload · POST to Bolna
        ↓
Bolna AI — Kabir voice (Hindi/Hinglish)
Calls driver · manages conversation
        ↓
webhook.py — Flask
Receives transcript · Groq classifies reason
        ↓
Supabase — call_logs table
Stores: reason, ETA, assistance_required, transcript
        ↓
"Check Call Result" updates Streamlit chat
```

---

## ⚙️ Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| Voice agent | Bolna AI (Kabir · Hindi · Deepgram STT · ElevenLabs TTS) |
| LLM | Groq API — llama-3.3-70b-versatile |
| Webhook receiver | Flask |
| Database | Supabase (PostgreSQL) via psycopg2 |
| Tunneling (dev) | ngrok |
| Language | Python 3.12 |

---

## ✨ Key Features

- **Zero manual calls** — system detects delay and calls driver automatically
- **Hindi/Hinglish voice** — Kabir (ElevenLabs) speaks naturally, Deepgram STT understands Indian accents
- **Intelligent classification** — Groq extracts delay reason, updated ETA, assistance needed from raw conversation
- **6 call scenarios handled** — answered, wrong driver, unclear audio, no answer, failed, help required
- **Full audit trail** — transcript + classification + ETA stored in Supabase
- **Integrated UX** — button appears contextually inside existing shipment chatbot, not a separate tool
- **SQL injection safe** — parameterized queries throughout
- **Graceful error handling** — safe defaults if Groq or Bolna fails

---

## 📊 Business Value

| Problem | Solution | Impact |
|---|---|---|
| Manual driver calls (5-10 min each) | AI calls automatically | 80% time saved per delay |
| Language barrier with Hindi drivers | Native Hindi voice agent | Zero miscommunication |
| No structured delay reason capture | Groq classifies from transcript | Searchable ops database |
| Control tower overloaded | AI handles routine calls | Team focuses on exceptions |
| No ETA update on delay | Driver's own words captured | Accurate customer communication |
| 24/7 monitoring impossible | Automated trigger on delay flag | Round-the-clock coverage |

---

## 🗄️ Database Schema

### `call_logs` table
| Column | Type | Description |
|---|---|---|
| id | bigint | Auto-generated primary key |
| shipment_no | bigint | Foreign key to shipment table |
| truck_no | text | Vehicle number |
| driver_mobile | text | Number that was called |
| call_datetime | timestamptz | Auto-filled on insert |
| call_status | text | answered_resolved / wrong_driver / unclear_audio / no_answer / failed / help_required |
| delay_reason | text | traffic / breakdown / unloading / unclear |
| assistance_required | boolean | Driver asked for help? |
| call_duration_sec | integer | Length of call in seconds |
| transcript | text | Full conversation |
| bolna_call_id | text | Bolna's execution ID |
| new_truck_no | text | If wrong driver gave different truck number |
| updated_eta | text | Driver's exact words about arrival time |

---

## 🚀 Run Locally

### Prerequisites
- Python 3.12
- Supabase account (free tier)
- Bolna AI account ($5 free credits)
- Groq API key (free tier)
- ngrok (for webhook during development)

### Setup

```bash
# Clone repo
git clone https://github.com/yourusername/agentic-caller
cd agentic-caller

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Add your API keys to .env
```

### Environment Variables

```
DATABASE_URL=your_supabase_connection_string
GROQ_API_KEY=your_groq_api_key
BOLNA_API_KEY=your_bolna_api_key
BOLNA_AGENT_ID=your_bolna_agent_id
```

### Run

```bash
# Terminal 1 — Flask webhook receiver
python webhook.py

# Terminal 2 — ngrok tunnel
ngrok http 5000
# Copy ngrok URL → paste in Bolna dashboard → Call tab → webhook URL

# Terminal 3 — Streamlit UI
streamlit run app.py
```

---

## 📁 File Structure

```
agentic-caller/
├── app.py                  # Streamlit UI — chatbot + Call Driver button
├── caller.py               # Bolna API trigger — validates + sends call
├── webhook.py              # Flask webhook — receives transcript from Bolna
├── db.py                   # Supabase functions — 7 query functions
├── intent_parser.py        # Groq LLM — extracts intent from user query
├── response_generator.py   # Groq LLM — generates Hindi/English response
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .gitignore              # Excludes .env and pycache
```

---

## 🔗 Related Project

**Prototype 1 — Track Shipment AI Chatbot**
Live at: [trackshipment.streamlit.app](https://trackshipment.streamlit.app)
GitHub: [github.com/yourusername/track-shipment](https://github.com)

---

## 👤 Author

**Abhishek Shukla**
I don't start with AI — I start with the operational problem. With 18 years of enterprise delivery across Logistics, SCM, Finance, Sales, HR, and Manufacturing, I bring a rare combination: deep domain knowledge, hands-on AI product development, and the ability to translate complex business challenges into practical, scalable AI solutions.
Independently designed and built 6 enterprise AI products — RAG chatbots, agentic voice systems, multi-agent risk analyzers, and executive intelligence platforms — each starting with a real business problem — including a voice agent whose architecture was independently validated in production at ₹10→₹5.5 per call (45% saving). IIT Delhi certified in Data Science & Machine Learning. Proven at enterprise scale: 1→140 team, 20+ state operations, SAP TM, SAP MDG, and Salesforce CRM implementations across 7 legal entities and 5 countries.

[LinkedIn →](#) · [GitHub →](#)

---

## ⚠️ Note

This is a portfolio prototype demonstrating agentic AI capabilities for logistics operations. Not production-deployed — run locally with your own API keys. Bolna trial accounts can only call verified phone numbers.
