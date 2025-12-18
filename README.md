好的，**MindForge**！這是一個非常棒的名字，充滿了力量感和創造性，完美地詮釋了「鍛造思想」的核心理念。

讓我們立刻將這個新名字融入到 `README.md` 中，並進行一些微調，使其更貼合 "MindForge" 這個品牌形象。

---

### 全新 `README.md` for MindForge

```markdown
# MindForge: Your Personal AI-Powered Cognition Forge

**MindForge** is a powerful, locally-run knowledge system designed to help you forge raw information into structured, actionable insights. It acts as an intelligent engine connected to your Notion workspace, automating the entire cognitive workflow: from capturing fleeting ideas to synthesizing long-term trends and forging new connections.

![UI Screenshot](https://via.placeholder.com/800x450.png?text=Your+MindForge+UI+Screenshot+Here)
*(Suggestion: Take a screenshot of your Streamlit UI and replace the placeholder link above)*

---

## ✨ Core Features

- **🧠 Intelligent Ingest**: Automatically categorizes, tags, and summarizes new notes, articles, and even text from images (OCR) as they enter your digital space.
- **🔗 Knowledge Forging**: Transforms processed inbox items into structured knowledge nodes, extracting the core idea, key insights, and potential use cases.
- **📊 Trend Synthesis**: Acts as your personal AI strategist, reviewing your knowledge base weekly, monthly, or quarterly to identify emerging trends, new ideas, and actionable insights.
- **💻 Local-First & Privacy-Focused**: Powered by Ollama, all AI processing runs on your local machine. Your thoughts and data remain yours, always.
- **🚀 Multi-Interface Access**:
    - **Web UI**: An intuitive Streamlit-based interface for a comprehensive visual experience.
    - **CLI**: A powerful command-line interface for power users and automation.
    - **Flow Launcher Integration**: Capture ideas instantly from anywhere on your desktop, without breaking your flow.

---

## 🛠️ System Architecture

MindForge is built on a modular architecture, connecting your Notion workspace with a local AI model through a series of specialized Python scripts.

1.  **Notion Workspace (The Anvil)**:
    - `Inbox DB`: The entry point for all raw materials (information).
    - `Knowledge Base DB`: Stores structured, forged knowledge nodes.
    - `Periodic Reviews DB`: Archives the AI-generated trend synthesis reports.
2.  **MindForge Engine (The Hammer)**:
    - `ui.py`: The Streamlit web interface.
    - `main.py`: The Typer-based command-line interface.
    - `scripts/`: Contains all core logic modules (Notion handling, AI agents, etc.).
    - `config.json`: Centralized configuration for API keys, database IDs, and modes.
3.  **Local AI Provider (The Fire)**:
    - `Ollama`: Runs large language models (e.g., Llama 3, Qwen) locally, providing the heat for transformation.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running.
- [Flow Launcher](https://www.flowlauncher.com/) (for desktop integration).

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd MindForge

# Create and activate a virtual environment
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Notion Setup

1.  **Create a Notion Integration**:
    - Go to [My integrations](https://www.notion.so/my-integrations).
    - Create a new integration (e.g., "MindForge Engine"), and copy the "Internal Integration Token".
2.  **Duplicate Notion Templates**:
    - Duplicate the three required database templates (Inbox, Knowledge Base, Periodic Reviews) into your workspace.
3.  **Connect Integration to Databases**:
    - For each of the three databases, click the `...` menu, go to `Add connections`, and select your "MindForge Engine" integration.

### 3. Configuration

1.  Rename `config.example.json` to `config.json`.
2.  Open `config.json` and fill in the required values:
    - `NOTION_TOKEN`: Your Notion integration token.
    - `INBOX_DB_ID`, `KNOWLEDGE_DB_ID`, `REVIEW_DB_ID`: The 32-character IDs of your three databases.
    - `LLM_MODEL_NAME`: The name of the Ollama model you want to use (e.g., `llama3:8b`).
    - `DEBUG_MODE`: Set to `true` for detailed logging, `false` for clean output.

---

## 💻 Usage

### Web UI (The Forge)

Run the Streamlit application:

```bash
streamlit run ui.py
```

Open your browser to the local URL provided. The UI is your main forge, providing access to all tools for shaping your knowledge.

### Command-Line Interface (CLI)

The CLI is perfect for quick strikes and automated workflows.

```bash
# Add a piece of raw material (a note)
python main.py add "This is a new idea about system architecture."

# Add a note from a URL
python main.py add-url "https://some-article-url.com"

# Run the knowledge forging process
python main.py synthesize

# Generate a weekly trend synthesis
python main.py review --period weekly

# Generate a monthly trend synthesis
python main.py review --period monthly
```

### Flow Launcher Integration

1.  Create a `launcher.bat` file (see `launcher.example.bat`).
2.  Configure Flow Launcher's Shell plugin to create keywords (e.g., `mf-add`, `mf-url`) that execute the batch file with the correct parameters.

---

## 💡 Future Blueprints

- [ ] **Vector-Powered Connections**: Implement a vector database to automatically find and display related notes.
- [ ] **Knowledge Graph Visualization**: Create a visual map of your knowledge base to uncover hidden structures.
- [ ] **Expanded Ingest Sources**: Add support for more data sources like email, RSS feeds, and social media bookmarks.

```

