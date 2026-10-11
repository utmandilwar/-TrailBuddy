# 🌿 TrailBuddy Local

> **An offline-first, privacy-respecting AI outdoor companion designed to help you disconnect from glowing screens, step outside, and touch grass.**

Built for the **Hacktoberfest 2026 Week 1 Challenge: "Touch Grass"**.

---

## 📌 Problem Statement

Modern devices and software are engineered to maximize screen time, capture attention with push notifications, and quantify every second of life into gamified streaks and social leaderboards. 

Even outdoor and fitness apps frequently encourage continuous screen interaction: staring at maps, tracking GPS breadcrumbs, checking leaderboards, and taking photos for social feeds.

**TrailBuddy Local flips this paradigm:**
- Uses an open-weight, locally hosted language model (**Qwen 2.5 3B Instruct** via **Ollama**) to craft mindful, personalized outdoor exploration missions.
- Designed around **"Go Outside Mode"**: read your mission, absorb the actionable sensory tasks, **lock your phone**, and step outside.
- Operates **100% offline** on your local machine with **zero cloud AI**, **zero external telemetry**, and **zero GPS tracking**.
- Features an **anti-addiction progress tracker**: no streaks, no guilt, no competition.

---

## 🌟 Key Features

### 1. Tailored Outdoor Mission Generator
- **Time Commitment:** 10, 20, or 30 minutes.
- **Curated Interests:** Nature, Plants, Birds, Mindfulness, Photography, or General Exploration.
- **Difficulty Tiers:** Easy, Moderate, or Challenging.
- **Accessible Environments:** Garden, Park, Neighborhood, or any accessible outdoor space.
- **Mobility & Accessibility:** Accommodates seated observation, paved flat paths, low-energy strolls, and physical constraints.

### 2. Structured & Safe AI Output
- Strictly validated with **Pydantic v2** (`Mission` schema).
- Built-in automatic retry mechanism for malformed JSON before presenting user-friendly diagnostics.
- **Leave No Trace & Safety Guardrails:**
  - Never instructs touching unknown plants, berries, or wild mushrooms.
  - Never instructs approaching, feeding, or disturbing wildlife.
  - Never directs users toward roadways, private property, or hazardous terrain.
  - Never requires screens, camera apps, or continuous device usage outdoors.
  - Never hallucinates species guarantees or claims real-time weather knowledge.

### 3. Go Outside Mode
- Distraction-free, high-contrast mission card.
- 3 to 5 actionable sensory tasks.
- Essential safety checklist.
- Mindful contemplation prompt for your walk.
- Prominent **"I'm Heading Outside"** action that encourages locking your screen immediately.
- Post-walk **"Mark Mission Complete"** flow with optional reflection journal.

### 4. Local Nature Journal
- Persisted locally using **SQLite** (`trailbuddy.db`).
- Records mission title, completion timestamp, duration, and personal reflections.
- Your personal thoughts never leave your local hard drive.

### 5. Mindful, Non-Gamified Progress
- Calm summary of completed missions, cumulative outdoor minutes, and recent reflections.
- Completely free of streaks, badges, push notifications, or pressure.

### 6. Zero-Cloud Privacy & Offline Execution
- Inference runs on `http://127.0.0.1:11434` via Ollama.
- Streamlit bound strictly to `127.0.0.1`.
- Built-in privacy guard module (`src/privacy.py`) audits and rejects non-loopback endpoints.
- Fully functional in **Airplane Mode** once models and dependencies are downloaded.

---

## 🏗️ Architecture

```
+-------------------------------------------------------------------+
|                        User Web Browser                           |
|                    http://127.0.0.1:8501                          |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                   Streamlit Application (app.py)                   |
|       - Create Mission Form       - Go Outside Mode (Screen-lock) |
|       - My Missions               - Local Nature Journal & Progress|
|       - Privacy Posture Audit                                     |
+-------------------+-----------------------------+-----------------+
                    |                             |
                    v                             v
+---------------------------------------+ +-------------------------+
|    Mission Generator & Pydantic       | |     Storage Manager     |
|         (src/mission_generator.py)     | |      (src/storage.py)   |
|   - Safety Guardrails & Prompts       | |   - SQLite Persistence  |
|   - Single-Retry Validation Loop      | |   - Zero Cloud Telemetry|
+-------------------+-------------------+ +------------+------------+
                    |                                  |
                    v                                  v
+---------------------------------------+ +-------------------------+
|       Ollama Client (src/llm.py)      | |   trailbuddy.db         |
|   - Local Loopback Validation         | |   (Local SQLite File)   |
+-------------------+-------------------+ +-------------------------+
                    |
                    v (HTTP REST 127.0.0.1:11434)
+-------------------------------------------------------------------+
|                       Local Ollama Daemon                         |
|        Model: qwen2.5:3b (Quantized GGUF / CPU or GPU)             |
+-------------------------------------------------------------------+
```

---

## 📂 Project Structure

```
trailbuddy-local/
├── .streamlit/
│   └── config.toml             # Localhost binding, zero telemetry, nature theme
├── src/
│   ├── __init__.py             # Package initialization
│   ├── llm.py                  # Local Ollama client & endpoint verification
│   ├── mission_generator.py    # Safety-guided prompts, JSON parsing & retry logic
│   ├── privacy.py              # Endpoint auditing and privacy enforcement
│   ├── schemas.py              # Pydantic data models & boundary validation
│   └── storage.py              # SQLite local persistence & progress tracking
├── tests/
│   ├── __init__.py             # Test suite package
│   ├── test_local_inference.py # Local inference and privacy boundary tests
│   ├── test_mission_generator.py # Mocked generation, retries, and live tests
│   ├── test_privacy.py         # Loopback enforcement and telemetry audit tests
│   ├── test_schemas.py         # Pydantic schema constraints and validation tests
│   └── test_storage.py         # SQLite CRUD and progress calculations tests
├── app.py                      # Streamlit interactive application
├── config.py                   # Centralized application settings
├── pytest.ini                  # Pytest configuration and marker registration
├── requirements.txt            # Python dependencies
├── LICENSE                     # MIT Open Source License
└── README.md                   # Full documentation & guide
```

---

## 🚀 Getting Started (Windows Installation)

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.9, 3.10, or 3.11 installed
- Internet connection **only** for the initial installation and model weight download

### Step 1: Install Ollama
Using Windows Package Manager (`winget`):
```powershell
winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
```
*Alternatively, download the installer from [ollama.com](https://ollama.com).*

### Step 2: Download the Qwen 2.5 3B Model
Open PowerShell and pull the model weights (approx. 1.9 GB):
```powershell
ollama pull qwen2.5:3b
```

Verify the model is installed:
```powershell
ollama list
```

### Step 3: Start Ollama Service
Ensure Ollama is running locally:
```powershell
ollama serve
```

### Step 4: Set Up TrailBuddy Local
Clone or navigate to the project directory:
```powershell
cd "path\to\hacktoberfest week 1"
```

Create and activate a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:
```powershell
pip install -r requirements.txt
```

### Step 5: Launch the Application
Run the Streamlit application:
```powershell
streamlit run app.py
```
Open your browser to: **`http://127.0.0.1:8501`**

---

## 🧪 Testing & Verification

The test suite covers schema validation, missing fields, invalid durations, model unavailable handling, retry recovery, SQLite persistence, and privacy posture.

### Running Unit Tests (Offline / Mocked)
Unit tests run completely without calling external networks or running LLM inference:
```powershell
pytest tests/ -m "not integration" -v
```

### Running Live Ollama Integration Test
To verify the full pipeline with your locally running `qwen2.5:3b` model:
```powershell
pytest tests/test_mission_generator.py -k "test_real_ollama_mission_generation" -v
```

---

## 📴 Offline Verification Procedure

To verify that TrailBuddy Local operates genuinely offline:
1. Ensure `ollama pull qwen2.5:3b` and `pip install -r requirements.txt` have completed.
2. Turn off your Wi-Fi or enable **Airplane Mode** in Windows.
3. In PowerShell, launch Ollama:
   ```powershell
   ollama serve
   ```
4. In another PowerShell terminal, run TrailBuddy:
   ```powershell
   streamlit run app.py
   ```
5. Open `http://127.0.0.1:8501`, fill in the mission generator form, and generate a mission.
6. Observe that the mission generates successfully, saves to `trailbuddy.db`, and allows journal logging with **zero active internet connection**.

---

## ⚡ Hardware Considerations & Optimization

- **RAM Requirements:** Minimum 4 GB of free system RAM (approx. 2.2 GB utilized by Ollama + Qwen 2.5 3B Q4_K_M weights during inference).
- **CPU / GPU Execution:** 
  - TrailBuddy Local defaults to `num_gpu = 0` (CPU mode) in `config.py`. This ensures stability across legacy or laptop GPUs (e.g., NVIDIA GeForce GTX 1650 mobile) where Windows CUDA stack overruns can occur.
  - On a standard modern 4-core / 8-thread CPU, generating a structured mission takes **15 to 30 seconds**.
  - If you have a supported modern RTX GPU, you can set `$env:TRAILBUDDY_NUM_GPU=33` in PowerShell to offload all layers to VRAM for sub-2-second generation.

---

## 📄 Licenses & Attribution

- **TrailBuddy Local:** Open source under the [MIT License](LICENSE).
- **Qwen 2.5 3B:** Released by the Qwen Team under the [Apache 2.0 License](https://github.com/QwenLM/Qwen2.5/blob/main/LICENSE).
- **Ollama:** Open source under the [MIT License](https://github.com/ollama/ollama/blob/main/LICENSE).
- **Core Python Libraries:** Streamlit (Apache 2.0), Pydantic (MIT), Requests (Apache 2.0), Pytest (MIT).
- **Event:** Created for Hacktoberfest 2026 Week 1 Challenge: *"Touch Grass"*.
