# Contributing to H0NEYP0T-466/linkedin-agent 🤝

Welcome to the **LinkedIn Agent** project! We're excited you're here and interested in contributing. This autonomous agent monitors GitHub repositories, generates AI-powered LinkedIn posts, and manages content approval workflows via Telegram—all with a real-time terminal-style interface.

Whether you're fixing bugs, adding features, improving documentation, or enhancing the UI, your contributions help make this tool more powerful and accessible.

---

## 🚀 Getting Started

### Prerequisites
Before you begin, ensure you have:
- **Node.js** (v18+) and **npm** installed
- **Python 3.9+** and **pip**
- A **Telegram bot token** (for notification features)
- An **OpenAI-compatible API key** (for LLM functionality)

> 💡 *Don't worry if you don’t have all keys yet—you can still explore the codebase and run the app in demo mode.*

### Setup Instructions

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/linkedin-agent.git
   cd linkedin-agent
   ```

2. **Install Frontend Dependencies**
   ```bash
   npm install
   ```

3. **Set Up Python Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   Create a `.env` file in the `backend/` directory:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_token
   OPENAI_API_KEY=your_openai_key
   GITHUB_USERNAME=your_github_username
   PORT=8006
   ```

5. **Run the App**
   - Start the backend:
     ```bash
     cd backend && uvicorn main:app --reload --port 8006
     ```
   - In another terminal, start the frontend:
     ```bash
     npm run dev
     ```

Now open [http://localhost:5173](http://localhost:5173) in your browser!

---

## 🐞 Reporting Bugs

Found a bug? Help us squash it by opening a detailed issue!

### Before Submitting
- Search existing issues to avoid duplicates.
- Check if it's already fixed in `main`.

### What to Include
When reporting a bug, please provide:
- ✅ **Description**: Clear summary of the problem
- ✅ **Steps to Reproduce**
- ✅ **Expected vs Actual Behavior**
- ✅ **Environment Details**:
  - OS version
  - Node.js / Python versions
  - Browser (if applicable)
- ✅ **Logs or Screenshots** (if relevant)

👉 Use our [Bug Report Template](https://github.com/H0NEYP0T-466/linkedin-agent/issues/new?template=bug_report.md) for consistency.

---

## 💡 Suggesting Features or Enhancements

Have an idea to improve the LinkedIn Agent? We'd love to hear it!

### Guidelines
- Keep proposals focused and scoped.
- Explain the **problem** your feature solves.
- Consider impact on performance, UX, and maintainability.
- If possible, sketch a rough implementation plan.

👉 Open a [Feature Request](https://github.com/H0NEYP0T-466/linkedin-agent/issues/new?template=feature_request.md) using our template.

> ⚠️ Major architectural changes should be discussed in an issue first before writing code.

---

## 🔁 Pull Request Process

We use a simple but effective workflow:

### Step-by-Step Guide
1. **Fork the repo** and create your feature/fix branch:
   ```bash
   git checkout -b feat/add-github-stars-tracking
   # or
   git checkout -b fix/websocket-reconnection-issue
   ```

2. **Make your changes** following code style rules below.

3. **Test locally**:
   - Run linters and tests (see section below).
   - Verify both frontend and backend work together.

4. **Commit with clarity**:
   ```bash
   git commit -m "feat(agent): add auto-retry logic for failed post submissions"
   ```
   Use conventional commits: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.

5. **Push to your fork**:
   ```bash
   git push origin feat/add-github-stars-tracking
   ```

6. **Open a Pull Request**:
   - Target branch: `main`
   - Fill out the PR template completely
   - Reference related issues (e.g., `Closes #123`)
   - Include screenshots or GIFs if UI changes are involved

### PR Review Expectations
- All CI checks must pass (linting, type checking, etc.)
- Code must follow project conventions
- At least one maintainer will review within 3–5 business days
- Be responsive to feedback—we’re all learning!

---

## ✨ Code Style & Quality

We care about clean, consistent, and maintainable code.

### Frontend (TypeScript + React)
- Uses **ESLint** with React + TypeScript rules
- Enforces **strict typing** via `tsconfig.app.json`
- Follows **React best practices** (hooks, functional components, etc.)
- CSS uses **BEM-like naming**; avoid global styles unless necessary

### Backend (Python + FastAPI)
- PEP 8 compliant formatting (`black`-like structure)
- Async/await patterns preferred
- Type hints encouraged (`typing.Optional`, etc.)
- Logging over print statements

### General Rules
- No trailing whitespace
- Max line length: 100 chars (frontend), 88 (backend)
- Use descriptive variable/function names
- Comment complex logic—not obvious things

### Automated Checks
All PRs must pass:
```bash
# Frontend
npm run lint
npm run type-check

# Backend (from backend/)
python -m flake8 .  # or black --check .
```

> 🛠️ These run automatically via GitHub Actions. Fix any failures before merge.

---

## 🧪 Testing & Linting

While comprehensive test suites aren’t fully set up yet, we encourage testing where practical.

### Current Tooling
- **Frontend**: ESLint + TypeScript compiler checks
- **Backend**: Flake8 (or Black) for formatting
- **Vite**: Fast HMR and build validation

### Adding Tests Later?
We welcome test contributions! Ideal places to start:
- WebSocket connection resilience
- LLM response parsing edge cases
- Storage persistence under load

---

## 📜 Code of Conduct

This project adheres to the **Contributor Covenant Code of Conduct**.  
By participating, you are expected to uphold it.

Please report unacceptable behavior to the maintainers via GitHub Issues or email.

🔗 Full text available in [`CODE_OF_CONDUCT