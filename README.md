<h1>linkedin-agent</h1>
<p>
  <strong><strong>Autonomous LinkedIn Agent with real-time terminal UI and LLM-powered content generation</strong></strong>
</p>
<p>
  <em><em>An AI-driven agent that monitors GitHub repos, generates posts via LLM, and streams logs through a retro terminal interface.</em></em>
</p>
<p>

  <img src="https://img.shields.io/github/license/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=brightgreen">
  <img src="https://img.shields.io/github/stars/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=yellow">
  <img src="https://img.shields.io/github/forks/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=blue">
  <img src="https://img.shields.io/github/issues/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=red">
  <img src="https://img.shields.io/github/issues-pr/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=orange">
  <img src="https://img.shields.io/badge/Contributions-Welcome-brightgreen?style=for-the-badge">

  <img src="https://img.shields.io/github/last-commit/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=purple">
  <img src="https://img.shields.io/github/commit-activity/m/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=teal">
  <img src="https://img.shields.io/github/repo-size/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=blueviolet">
  <img src="https://img.shields.io/github/languages/code-size/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=indigo">

  <img src="https://img.shields.io/github/languages/top/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=critical">
  <img src="https://img.shields.io/github/languages/count/H0NEYP0T-466/linkedin-agent?style=for-the-badge&amp;color=success">

  <img src="https://img.shields.io/badge/Docs-Available-green?style=for-the-badge&amp;logo=readthedocs&amp;logoColor=white">
  <img src="https://img.shields.io/badge/Open%20Source-%E2%9D%A4-red?style=for-the-badge">

</p>

---

## 🔗 Quick Links

- <a href="#abstract">📄 Abstract</a>
- <a href="#key-highlights">✨ Key Highlights</a>
- <a href="#features">✨ Features</a>
- <a href="#architecture">🏗️ Architecture</a>
- <a href="#tech-stack">🛠 Tech Stack</a>
- <a href="#dependencies-packages">📦 Dependencies & Packages</a>
- <a href="#prerequisites">📋 Prerequisites</a>
- <a href="#installation">⚙️ Installation</a>
- <a href="#quick-start">🚀 Quick Start</a>
- <a href="#usage">💡 Usage</a>
- <a href="#api-endpoints">🌐 API Endpoints</a>
- <a href="#configuration">⚙️ Configuration</a>
- <a href="#environment-variables">🔧 Environment Variables</a>
- <a href="#project-structure">📂 Project Structure</a>
- <a href="#license">📜 License</a>

---

## 📑 Table of Contents

1. <a href="#abstract">Abstract</a>
2. <a href="#key-highlights">Key Highlights</a>
3. <a href="#features">Features</a>
4. <a href="#architecture">Architecture</a>
5. <a href="#tech-stack">Tech Stack</a>
6. <a href="#dependencies-packages">Dependencies & Packages</a>
7. <a href="#prerequisites">Prerequisites</a>
8. <a href="#installation">Installation</a>
9. <a href="#quick-start">Quick Start</a>
10. <a href="#usage">Usage</a>
11. <a href="#api-endpoints">API Endpoints</a>
12. <a href="#configuration">Configuration</a>
13. <a href="#environment-variables">Environment Variables</a>
14. <a href="#project-structure">Project Structure</a>
15. <a href="#license">License</a>

---

## Abstract

This repository hosts **H0NEYP0T-466/linkedin-agent**, an intelligent automation system that autonomously monitors GitHub repositories and generates LinkedIn posts using AI. The project features a real-time terminal-style web interface built with React and Vite, allowing users to monitor agent activity through live log streaming. At its core, the agent leverages FastAPI for backend services, including asynchronous LLM interactions via LongCat API, RSS-based web scraping for tech news, and Telegram bot integration for approval workflows. Data persistence is handled through JSON and Markdown storage, while the frontend provides an interactive command-line experience with WebSocket-powered updates. The architecture supports full lifecycle management of autonomous posting tasks, from repository discovery to content generation and social media publishing.

## Key Highlights

This project is an **autonomous LinkedIn Agent** that monitors GitHub repositories, generates AI-powered content, and manages a real-time terminal interface. 🤖 The system combines web scraping, LLM integration, and Telegram notifications to create a seamless content pipeline for tech professionals.

Key capabilities include: **real-time log streaming** via WebSocket connections, **RSS feed monitoring** for AI/ML news, and **GitHub activity tracking** with README parsing. The agent uses LongCat's OpenAI-compatible API to generate LinkedIn posts from repository data, with approval workflows handled through Telegram bot integration.

Built with a modern React frontend featuring a retro terminal UI, the application provides live status updates, command-line-like interaction, and responsive design. All operations run asynchronously in FastAPI, ensuring smooth performance while managing storage, message queuing, and network resilience.

## Features

The LinkedIn Agent project delivers a fully autonomous social media automation platform with real-time monitoring and interactive control capabilities.

🔍 **GitHub Repository Monitoring**: Continuously tracks public repositories, commit activity, and README content for configured GitHub users through the `github_service.py`.

🤖 **AI-Powered Content Generation**: Leverages LongCat OpenAI-format LLM service (`llm_service.py`) to generate engaging LinkedIn posts and repository descriptions from GitHub data.

📰 **Web Scraping Integration**: Fetches latest AI/ML/tech news from multiple RSS feeds with optional Cloudflare support for JavaScript-heavy pages via `scraper_service.py`.

💬 **Telegram-Based Approval Workflow**: Implements bot-driven notification system (`telegram_service.py`) allowing users to review and approve generated content before posting.

🖥️ **Real-Time Terminal UI**: Features live log streaming and status monitoring through WebSocket connections with a retro-styled command-line interface in React (`App.tsx`).

💾 **Persistent Data Management**: Stores logs, repository tracking, todo lists, and post files using JSON/Markdown formats via dedicated storage service (`storage.py`).

⚡ **Asynchronous Architecture**: Built on FastAPI with async/await patterns for efficient concurrent task handling and real-time communication.

## Architecture

The LinkedIn Agent is architected as a **full-stack autonomous system** with a clear separation between frontend and backend components. The **FastAPI backend** serves as the central orchestrator, managing agent lifecycle, real-time communication, and service coordination through asynchronous event loops. It exposes REST APIs for status monitoring and WebSocket endpoints for live log streaming. The **React-based frontend** provides a terminal-style interface that connects via WebSocket to display real-time agent activity, featuring auto-scrolling logs and interactive controls.

Core services include: 🤖 **GitHub monitoring** for repository tracking and README parsing, 🧠 **LLM integration** via LongCat API for content generation, 📰 **RSS scraper** for AI/ML news aggregation, 💾 **JSON/Markdown storage** for persistent data management, and 📱 **Telegram bot** for approval workflows and notifications. All services run asynchronously within the main agent loop, enabling concurrent operations like scraping, LLM processing, and message queuing. The architecture supports real-time updates through WebSocket connections while maintaining stateless API endpoints for external integration.

## Tech Stack

This project is built using a modern, full-stack architecture combining Python for backend services and React with TypeScript for the frontend interface.

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
</p>

The backend leverages **FastAPI** for high-performance API endpoints, async HTTP handling via `httpx`, and real-time communication through WebSockets. It integrates with external services including Telegram bots, RSS feed scraping, GitHub API, and LLM inference via LongCat OpenAI-compatible endpoints. Data persistence is managed through JSON-based storage with Markdown support.

<p>
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/Uvicorn-4998A1?style=for-the-badge&logo=uvicorn&logoColor=white" alt="Uvicorn">
  <img src="https://img.shields.io/badge/WebSocket-010101?style=for-the-badge&logo=socketdotio&logoColor=white" alt="WebSocket">
  <img src="https://img.shields.io/badge/CORS-FF6B6B?style=for-the-badge&logo=cors&logoColor=white" alt="CORS">
</p>

The frontend is a **React** application powered by **Vite** for fast development, featuring a terminal-style UI with real-time log streaming and interactive command-line aesthetics. It communicates with the backend via REST APIs and WebSocket connections for live updates.

## Dependencies & Packages

The project relies on several key dependencies defined in two main files: `backend/requirements.txt` for the Python backend and `package.json` (with `package-lock.json`) for the React frontend.

**Backend Dependencies (Python)** – Defined in `backend/requirements.txt`:  
- **FastAPI** – Web framework for building APIs with automatic OpenAPI documentation.  
- **Uvicorn** – ASGI server to run FastAPI applications asynchronously.  
- **httpx** – Async HTTP client for making requests to external services like RSS feeds and APIs.  
- **python-telegram-bot** – Library for integrating Telegram bot functionality, including message sending and callback handling.  
- **feedparser** – Parser for RSS and Atom feeds, used by the scraper service to fetch news content.  

**Frontend Dependencies (JavaScript/TypeScript)** – Defined in `package.json`:  
- **React 19** – Core library for building the user interface.  
- **Vite** – Build tool and development server optimized for fast HMR and optimized production builds.  
- **TypeScript** – Type-safe superset of JavaScript, configured via `tsconfig.json`, `tsconfig.app.json`, and `tsconfig.node.json`.  
- **ESLint** – Linting tool enforcing code quality with React, React Refresh, and TypeScript support.  

These packages enable real-time terminal-style UI, agent orchestration, LLM integration, GitHub/Telegram/web scraping, and persistent storage as evidenced by the codebase structure and implementation files.

## Prerequisites

Before setting up the **H0NEYP0T-466/linkedin-agent**, ensure your system meets the following requirements:

<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"> 
  <img src="https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node.js">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
</p>

- **Python 3.10+** is required to run the backend services (FastAPI, agent orchestration, LLM integration).
- **Node.js 18+** and **npm** are needed for the frontend React application built with Vite.
- The project uses **TypeScript** across both frontend and backend components.
- A modern web browser is required to access the terminal-like UI at `http://localhost:5173`.

> 💡 No Docker or database dependencies are present in the current codebase — everything runs natively via Python virtual environments and Node.js tooling.

## Installation

This project requires both **Python 3.9+** for the backend and **Node.js 18+** with npm for the frontend.

### Backend Setup
1. Navigate to the `backend` directory
2. Create a virtual environment:  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup
1. Ensure you're in the project root
2. Install frontend dependencies:  
   ```bash
   npm install
   ```

### Running the Application
- Start the backend server:  
  ```bash
  cd backend && uvicorn main:app --host 0.0.0.0 --port 8006 --reload
  ```
- Start the frontend development server:  
  ```bash
  npm run dev
  ```

The application will be available at `http://localhost:5173` (frontend) and `http://localhost:8006` (backend API).

## Quick Start

Get your LinkedIn Agent up and running in minutes! 🚀

First, install the frontend dependencies:
```bash
npm install
```

Then start the backend server:
```bash
cd backend && python -m venv venv && source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8006
```

In a new terminal, launch the React frontend:
```bash
npm run dev
```

Open your browser to `http://localhost:5173` to see the real-time terminal interface monitoring your agent's activities. The app automatically connects via WebSocket to stream logs and status updates.

**Important**: Ensure environment variables (e.g., API keys) are configured as needed in a `.env` file in the `backend/` directory for services like Telegram bot and LLM integration to function properly.

## Usage

Once the application is running, access the real-time terminal interface at `http://localhost:5173` to monitor and interact with your LinkedIn Agent. The interface provides a retro-style command-line experience showing live logs, agent status, and interactive controls.

Connect via WebSocket to receive continuous updates from the backend agent. Use the REST API endpoints to check agent status, retrieve stored data, or trigger actions like fetching GitHub repositories or generating posts. The Telegram bot integration allows remote approval of generated LinkedIn content through chat commands.

The agent autonomously monitors configured GitHub repositories, scrapes relevant tech news, generates AI-powered posts using the LLM service, and notifies you via Telegram for review before posting. All activity logs stream in real-time through the terminal UI.

Key interactions include starting/stopping the agent, viewing current tasks, checking repository status, and managing post drafts — all accessible through the web interface or Telegram bot commands.

## API Endpoints

The FastAPI backend exposes several RESTful endpoints and WebSocket connections for managing the LinkedIn Agent's lifecycle and retrieving data:

- **`POST /agent/start`** — Initiates the agent's autonomous workflow, triggering GitHub repository monitoring, AI-powered post generation, and Telegram-based approval notifications.
- **`GET /agent/status`** — Returns real-time status of the agent including current task, progress percentage, and active services.
- **`GET /posts`** — Retrieves generated LinkedIn post drafts stored in Markdown format, typically awaiting user approval via Telegram.
- **`GET /logs`** — Provides access to historical execution logs for debugging and monitoring purposes.
- **WebSocket `/ws/logs`** — Enables real-time streaming of live logs from the agent to the frontend terminal interface.

These endpoints support CORS-enabled communication with the React frontend running on port 8000, forming a complete autonomous content generation pipeline.

## Configuration

The LinkedIn Agent is configured primarily through environment variables that control core functionality across its modular services. The system uses a centralized configuration approach where critical parameters are loaded from the environment during runtime.

Key configuration areas include:

- **Telegram Integration**: Requires `TELEGRAM_BOT_TOKEN` for bot authentication and optional proxy settings for restricted regions
- **LLM Service**: Needs `LLM_API_KEY` to authenticate with the LongCat OpenAI-format API for content generation
- **GitHub Monitoring**: Uses `GITHUB_USERNAME` to specify which user's repositories should be tracked
- **Backend Port**: Configured via `UVICORN_PORT` (default: 8006) for the FastAPI server

Environment variables are accessed throughout the backend code using standard Python methods, ensuring secure credential management. While the system includes error handling for network failures in the Telegram service, it attempts direct retries rather than implementing a full message queueing mechanism. The storage layer persists data in JSON and Markdown formats but doesn't currently support customizable retention policies.

For local development, create a `.env` file in the `backend/` directory with the required variables before starting the application.

## Environment Variables

The LinkedIn Agent backend relies on several environment variables to configure its behavior and integrations. These include:

- `TELEGRAM_BOT_TOKEN`: Required for the Telegram bot service to authenticate and send notifications.
- `LLM_API_KEY`: Needed for the LLM service to access the LongCat OpenAI-format API for content generation.
- `GITHUB_USERNAME`: Specifies the GitHub user whose repositories are monitored by the GitHub service.
- `CLOUDFLARE_TOKEN`: Optional, used by the scraper service to bypass Cloudflare protection on JavaScript-heavy pages.
- `PORT`: Defines the port on which the FastAPI server runs (default: 8006).

These variables should be set in your environment or a `.env` file before running the application. The backend uses these values to initialize services like Telegram messaging, AI content generation, and data scraping.

## Project Structure

The project follows a **monorepo** structure with clear separation between frontend and backend components:

- **Frontend (`src/`)**: Built with React and Vite, featuring a terminal-style UI for real-time agent monitoring
  - `App.tsx` - Main React component handling WebSocket connections and log streaming
  - `main.tsx` - Application entry point with StrictMode wrapper
  - `App.css` & `index.css` - Terminal-inspired styling with dark theme and green monospace text

- **Backend (`backend/`)**: FastAPI-based microservices architecture
  - `main.py` - Core API server with WebSocket support and CORS configuration
  - `agent.py` - Orchestrates all services within an async event loop
  - `llm_service.py` - Handles LLM interactions via LongCat OpenAI-format API
  - `scraper_service.py` - Fetches AI/ML/tech news from RSS feeds
  - `github_service.py` - Manages GitHub repository data and user events
  - `telegram_service.py` - Telegram bot integration with message queuing
  - `storage.py` - JSON/Markdown-based persistent storage system

- **Configuration**: TypeScript configs (`tsconfig.*.json`), ESLint setup, and Vite build tooling
- **Root files**: Package manifests, dependency locks, and HTML entry point

## License

This project is licensed under the **MIT License** — see the `LICENSE` file for details.

The MIT License is a permissive open-source license that allows you to freely use, modify, distribute, and sublicense the software, provided that the original copyright notice and permission notice are included in all copies or substantial portions of the code. It's ideal for projects like this LinkedIn Agent that combine web scraping, LLM integration, and real-time monitoring with a clean, maintainable tech stack.

You are welcome to use this codebase for personal or commercial purposes, contribute improvements, or integrate it into your own solutions — just give proper credit and include the license terms.

---

<p align="center">Made with ❤️ by <a href="https://github.com/H0NEYP0T-466">H0NEYP0T-466</a></p>