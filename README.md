# 🚀 AI-Powered Cold Email CRM

Enterprise-grade open-source cold outreach automation platform. Natively integrates with **Mailcow** for infrastructure and **OpenAI** for intelligence.

## 🏗️ Architecture Stack

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, Lucide React.
- **Backend**: FastAPI (Python), SQLAlchemy, Pydantic.
- **Database**: PostgreSQL 15.
- **Async Tasks**: Celery with Redis as the broker.
- **Mailing Infrastructure**: Mailcow (Dockerized).

---

## 🛠️ Local Setup Instructions

Follow these steps to get the full stack running on your local machine.

### 1. Prerequisites
- [Docker](https://www.docker.com/get-started) & Docker Compose.
- [Git](https://git-scm.com/).

### 2. Clone and Environment Setup
```bash
git clone https://github.com/yakupbulbul/cold-email-crm.git
cd cold-email-crm

# Copy the example environment file
cp .env.example .env
```

### 3. Configure Environment Variables
Edit your `.env` file with the following required values:

- **Security**: `SECRET_KEY` (Generate a random string).
- **AI**: `OPENAI_API_KEY` (Required for lead categorization and draft generation).
- **Mailcow API**:
  - `MAILCOW_API_URL`: `https://mail.example.com/api/v1` (or your local instance).
  - `MAILCOW_API_KEY`: Your API key from the Mailcow admin panel.

### 4. Launch the Application
The project includes a `Makefile` for simplified management:

```bash
# Build and start all services in the background
make up

# Run database migrations
make migrate
```

### 5. Initialize Admin User
To access the dashboard, you must create an initial admin user:

```bash
docker compose exec api python scripts/create_user.py --email admin@example.com --password YourSecurePassword --admin
```

---

## 📬 Mailcow Online Integration

This CRM is designed to connect to any Mailcow instance. 
1. Log in to your Mailcow Admin Panel (`https://mail.yourdomain.com`).
2. Navigate to **System -> Configuration -> API**.
3. Enable the API and generate an **API Key**.
4. Add the Key and your instance URL to the CRM's `.env` file.

Once connected, the CRM will be able to synchronize domains and provision mailboxes automatically.

---

## 💡 Common Commands (Command Prompt Reference)

| Action | Command |
| :--- | :--- |
| **Start Services** | `docker compose up -d` |
| **Stop Services** | `docker compose down` |
| **View Backend Logs** | `docker compose logs -f api` |
| **View Worker Logs** | `docker compose logs -f worker` |
| **Reset Database** | `docker compose down -v && docker compose up -d` |
| **Shell Access (API)** | `docker compose exec api bash` |

---

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements.

## 📄 License
This project is licensed under the MIT License.
