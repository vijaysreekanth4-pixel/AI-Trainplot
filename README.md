# Generative AI Interview Engineer

An advanced AI-powered technical interviewer application that conducts voice-to-voice, highly interactive, and strictly deduplicated technical interviews based on a candidate's uploaded resume. 

Built with **React (Vite)** on the frontend and **FastAPI + LangGraph** on the backend. The entire application is fully containerized using **Docker** for seamless deployment and development.

## 🚀 Architecture
- **Frontend**: React.js (Vite), CSS3, Web Speech API for voice recognition & synthesis.
- **Backend**: Python 3.10, FastAPI, LangGraph (Stateful Agentic Workflow), Langchain.
- **Infrastructure**: Docker, Docker Compose.

## 🐳 Running with Docker (Recommended)

Since this project is fully Dockerized, you don't need to manually install Node.js or Python to run it. Docker handles all the dependencies natively.

### Prerequisites
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Quick Start
1. Open your terminal in the root directory of this project.
2. Run the following command to build and start the containers:
   ```bash
   docker-compose up --build
   ```
3. The services will be available at:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8001](http://localhost:8001)

To stop the containers, press `Ctrl+C` or run:
```bash
docker-compose down
```

## 🛠 Manual Setup (Without Docker)

If you prefer to run the servers manually without Docker, follow these steps:

**1. Start Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**2. Start Frontend:**
```bash
cd frontend
npm install
npm run dev -- --port 3000
```
