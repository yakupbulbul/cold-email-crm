# 🚀 AI-Powered Cold Email CRM

An open-source SendGrid + CRM + AI Inbox system connecting directly to your Mailcow infrastructure.
Built for high deliverability, automated warm-ups, and AI-assisted email workflows.

## 🌟 Key Features

- **Automated Warm-up Engine**: Exchanges emails between connected mailboxes with realistic delays and AI-generated replies to build sender reputation.
- **AI Inbox Intelligence**: Uses OpenAI to automatically classify intent (Positive, Question, etc.), summarize threads in 2 sentences, and generate contextual draft replies.
- **Mailcow Integration**: Designed to work seamlessly with Mailcow via SMTP (for sending) and IMAP (for receiving).
- **Campaign Management**: Track leads, sending volumes, limits, and reply rates across your cold outreach campaigns.
- **Modern UI**: A beautiful, premium Next.js dashboard crafted with Tailwind CSS and Lucide React.

## 🏗️ Architecture

- **Frontend**: Next.js 14 App Router (React, Tailwind CSS, TypeScript)
- **Backend API**: Python FastAPI
- **Background Jobs**: Celery + Redis (Warm-up scheduler, IMAP Inbox Sync)
- **Database**: PostgreSQL (SQLAlchemy ORM)

## 🚀 Getting Started

Ensure you have Docker and Docker Compose installed.

### 1. Environment Variables
You need an OpenAI API Key for the AI features. Set it in your environment or directly in the `docker-compose.yml`.

### 2. Run the Stack
Run the entire platform (Frontend, API, Workers, DB, Cache) with one command:
```bash
docker-compose up -d --build
```

### 3. Access
- **Frontend Dashboard**: `http://localhost:3000`
- **Backend API Docs**: `http://localhost:8000/docs`

## 🤝 Contributing
We welcome contributions from the open-source community! Feel free to open issues or submit pull requests.

## 📄 License
This project is licensed under the MIT License.
