# Deployment Notes

## Local Development

Run both services with:

```bash
python run.py
```

The launcher chooses free local ports, starts FastAPI first, waits until it is healthy, then starts Streamlit. Use the exact Streamlit URL printed by the launcher.

## AWS EC2 Deployment

This is the simplest AWS deployment path without Docker. It runs FastAPI and Streamlit as two `systemd` services on one Ubuntu EC2 instance.

1. Create an Ubuntu EC2 instance.
2. In the EC2 security group, allow inbound TCP ports:
   - `22` from your IP for SSH
   - `8501` from your IP or the internet for Streamlit
   - `8000` from your IP or the internet for the backend OAuth/API endpoint
3. SSH into the instance.
4. Install system packages:

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git nginx
```

5. Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

6. Create a virtual environment and install dependencies:

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

7. Create production environment values:

```bash
cp .env.example .env
nano .env
```

Set these at minimum:

```text
APP_ENV=production
APP_URL=http://YOUR_EC2_PUBLIC_IP_OR_DOMAIN:8000
FRONTEND_URL=http://YOUR_EC2_PUBLIC_IP_OR_DOMAIN:8501
DEMO_MODE=true
```

For live GitHub/Groq mode, also set:

```text
DEMO_MODE=false
GROQ_API_KEY=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_PAT=...
GITHUB_WEBHOOK_SECRET=...
```

8. Create the backend service:

```bash
sudo nano /etc/systemd/system/gitreview-backend.service
```

Paste:

```ini
[Unit]
Description=GitReview AI FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/YOUR_REPO
EnvironmentFile=/home/ubuntu/YOUR_REPO/.env
ExecStart=/home/ubuntu/YOUR_REPO/venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

9. Create the frontend service:

```bash
sudo nano /etc/systemd/system/gitreview-frontend.service
```

Paste:

```ini
[Unit]
Description=GitReview AI Streamlit Frontend
After=network.target gitreview-backend.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/YOUR_REPO
EnvironmentFile=/home/ubuntu/YOUR_REPO/.env
Environment=API_BASE_URL=http://YOUR_EC2_PUBLIC_IP_OR_DOMAIN:8000/api/v1
ExecStart=/home/ubuntu/YOUR_REPO/venv/bin/streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

10. Start both services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable gitreview-backend gitreview-frontend
sudo systemctl start gitreview-backend gitreview-frontend
```

Open:

```text
http://YOUR_EC2_PUBLIC_IP_OR_DOMAIN:8501
```

Check logs:

```bash
sudo journalctl -u gitreview-backend -f
sudo journalctl -u gitreview-frontend -f
```

## AWS Production Notes

- Use a domain and HTTPS before using live GitHub OAuth/webhooks seriously.
- Do not commit `.env`; store secrets in AWS Secrets Manager, SSM Parameter Store, or EC2 environment setup.
- App Runner is convenient for two separate services, but AWS documentation currently says it is not open to new customers. Existing App Runner users can deploy the frontend and backend as two services.
- For a more production-grade AWS setup, put Nginx or an Application Load Balancer in front of the app and terminate HTTPS there.

## Streamlit Community Cloud

This project has a Streamlit frontend and a separate FastAPI backend. Streamlit Community Cloud runs the Streamlit app only, so `run.py` is not the deploy entrypoint there.

Use:

```text
frontend/app.py
```

as the Streamlit app file.

For the app to work after deployment, the FastAPI backend must be deployed separately and the Streamlit app must receive:

```text
API_BASE_URL=https://your-backend-domain.example.com/api/v1
```

Also set the backend `FRONTEND_URL` to your Streamlit app URL so GitHub OAuth redirects back to the deployed frontend.

If you do not deploy the backend separately, the Streamlit UI can load, but API-backed pages will show backend connection errors.
