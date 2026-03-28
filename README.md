# 🚀 AI-Powered Cold Email CRM 
_Enterprise-grade Open-Source Cold Outreach automation natively integrating Mailcow & OpenAI._

Welcome to the definitive all-in-one open-source Cold Email CRM. This platform is not just a sender. It is a full **SendGrid + CRM + AI Inbox** architecture that routes through robust multi-tenant Mailcow instances.

Currently maintained by [Yakup Bulbul](https://github.com/yakupbulbul).

## 🌟 Key Features
* **Natively Multi-Tenant**: Attach infinite domains and mailboxes securely to single Mailcow infrastructures.
* **Smart Warm-up Engine**: Built-in 14-day exponential scaling volume caps (5 \u2192 10 \u2192 20) with natively injected time randomization.
* **Campaign Constraints**: Dedicated duplicate lead prevention, variable templating, and absolute daily limit enforcement.
* **Imap Thread Resolutions**: Inbound sync engine parsing strict MIME/RFC822 headers resolving cross-thread replies robustly.
* **AI Processing**: Built in `OpenAI` processing extracting lead intents, thread summarizing, and drafting contextual replies locally!
* **Enterprise Tech Stack**: Built entirely on Next.js 14 App Router, Python FastAPI, PostgreSQL (SQLAlchemy + Alembic), Celery Workers, Redis, and Mailcow.

## 🧱 Architecture Overview
1. **Frontend**: The `frontend/` directory is an expansive Next.js App router serving responsive UI built natively using sleek Tailwind CSS and Lucide React. 
2. **Backend Gateway**: The `backend/app/main.py` entrypoint. The API scales perfectly handling REST mappings, JWT tokens, Rate Limiting (`slowapi`), Database Transactions, and external network interactions. 
3. **Automations Daemon**: The `backend/workers/celery_app.py` entrypoint runs the background schedules synchronizing inbound IMAPs, outbound Campaign rules, and the Warmup constraints perfectly disjoint from the main gateway! 

## 🛠️ Quickstart

To spin up the ecosystem immediately in your dockerized environment:

\`\`\`bash
git clone https://github.com/yakupbulbul/cold-email-crm.git
cd cold-email-crm
cp backend/.env.example backend/.env

# Spin up the Database, Redis, Celery, Backend Gateway, and Frontend:
make up

# Apply PostgreSQL schemas for the 11 integrated tables
make migrate
\`\`\`

Access the Next.js Frontend precisely at `http://localhost:3000`. 
API Documentations natively live at `http://localhost:8050/api/v1/docs`. 

## 🤝 Contributing
Open source contributions are highly encouraged. Please review the `CONTRIBUTING.md` guidelines (coming soon) and feel free to submit PRs for any architectural upgrades! 

## 📄 License
This platform operates under the MIT Open Source License.

---
_Built for scale, structured for communities, and engineered for deliverability._
