"""TrailBuddy Local - Offline-First AI Outdoor Companion.

Built for the Hacktoberfest 2026 Week 1 Challenge: "Touch Grass".
100% Local Inference (Ollama + Qwen 2.5 3B) | SQLite Persistent Storage | Zero Telemetry
"""

import sys
from pathlib import Path
from datetime import datetime
import streamlit as st

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src.privacy import verify_privacy_posture
from src.llm import OllamaClient, OllamaConnectionError, OllamaModelNotFoundError
from src.schemas import (
    MissionRequest,
    Mission,
    ALLOWED_DURATIONS,
    ALLOWED_INTERESTS,
    ALLOWED_DIFFICULTIES,
    ALLOWED_ENVIRONMENTS,
)
from src.mission_generator import MissionGenerator, MissionGenerationError
from src.storage import StorageManager

# Initialize storage
storage = StorageManager()

# Streamlit Page Setup
st.set_page_config(
    page_title="TrailBuddy Local — Touch Grass",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Nature Styling
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b4332;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #40916c;
        margin-bottom: 1.5rem;
    }
    .mission-card {
        background: #f4f7f4;
        border-radius: 12px;
        padding: 1.5rem;
        border-left: 6px solid #2d6a4f;
        margin-bottom: 1.2rem;
    }
    .task-item {
        background: #ffffff;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 1px solid #d8f3dc;
        margin-bottom: 0.5rem;
        font-size: 1.05rem;
        color: #1b4332;
    }
    .safety-box {
        background: #fff8e7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #d4a373;
        margin-top: 1rem;
        color: #6b4e28;
    }
    .heading-out-box {
        background: #e8f5e9;
        border: 2px dashed #2d6a4f;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        margin: 1.5rem 0;
    }
    .stat-card {
        background: #eef5ee;
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid #cfe2cf;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #1b4332;
    }
    .stat-label {
        font-size: 0.95rem;
        color: #52796f;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "active_mission" not in st.session_state:
    st.session_state.active_mission = None
if "heading_out_mode" not in st.session_state:
    st.session_state.heading_out_mode = False

# Sidebar Navigation & System Health
with st.sidebar:
    st.markdown("## 🌿 TrailBuddy Local")
    st.caption("Hacktoberfest 2026 • Touch Grass Edition")
    st.markdown("---")

    menu = st.radio(
        "Navigation",
        [
            "🌱 Create Mission",
            "🎒 Go Outside Mode",
            "📋 My Missions",
            "📖 Nature Journal & Progress",
            "🔒 Privacy & About",
        ],
        index=0 if st.session_state.active_mission is None else 1,
    )

    st.markdown("---")
    st.markdown("### 🖥️ Local Model Status")

    # Local Ollama Health Check
    llm_client = OllamaClient()
    health = llm_client.check_health()
    if health["available"] and health["target_model_installed"]:
        st.success(f"Ollama Online • `{config.DEFAULT_MODEL}` ready")
    elif health["available"]:
        st.warning(
            f"Ollama Online, but model `{config.DEFAULT_MODEL}` is missing.\n"
            f"Run: `ollama pull {config.DEFAULT_MODEL}`"
        )
    else:
        st.error(
            "Ollama Unreachable\n\n"
            "Start Ollama locally with:\n`ollama serve`"
        )

    st.markdown("---")
    st.caption("🔒 100% Offline • Zero Telemetry • Localhost Only")


# -------------------------------------------------------------
# 1. Create Mission Section
# -------------------------------------------------------------
if menu == "🌱 Create Mission":
    st.markdown('<div class="main-title">🌿 Create an Outdoor Mission</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Set your preferences and let your local AI companion design a safe, screen-free outdoor exploration.</div>',
        unsafe_allow_html=True,
    )

    if not health["available"] or not health["target_model_installed"]:
        st.warning(
            "⚠️ **Local AI is not currently ready.**\n\n"
            "Please ensure Ollama is running (`ollama serve`) and the model is downloaded "
            f"(`ollama pull {config.DEFAULT_MODEL}`)."
        )

    with st.form("mission_form"):
        col1, col2 = st.columns(2)

        with col1:
            duration = st.select_slider(
                "⏱️ Available Outdoor Time",
                options=ALLOWED_DURATIONS,
                value=20,
                format_func=lambda m: f"{m} minutes",
                help="Choose a brief mindful pause or a slightly longer walk.",
            )

            interest = st.selectbox(
                "🔍 Primary Interest",
                options=ALLOWED_INTERESTS,
                index=0,
                format_func=lambda s: s.capitalize(),
                help="What draws your curiosity outside today?",
            )

            difficulty = st.selectbox(
                "🥾 Difficulty Level",
                options=ALLOWED_DIFFICULTIES,
                index=0,
                format_func=lambda s: s.capitalize(),
                help="Easy missions focus on gentle presence, while challenging ones add active sensory puzzles.",
            )

        with col2:
            environment = st.selectbox(
                "🌲 Outdoor Environment",
                options=ALLOWED_ENVIRONMENTS,
                index=1,
                format_func=lambda s: s.capitalize(),
                help="Select the space you have direct, safe access to.",
            )

            accessibility = st.text_input(
                "♿ Accessibility / Mobility Preferences (Optional)",
                placeholder="e.g. Paved flat paths, seated observation, low-energy stroll",
                help="Any physical accommodations or comfort needs for this session.",
            )

            st.caption(
                "🛡️ **Safety Guarantee:** TrailBuddy never requires touching unknown plants, "
                "approaching wildlife, entering roadways, or using your phone outside."
            )

        submitted = st.form_submit_button("🌱 Generate Outdoor Mission", use_container_width=True)

    if submitted:
        try:
            req = MissionRequest(
                duration_minutes=duration,
                interest=interest,
                difficulty=difficulty,
                environment=environment,
                accessibility=accessibility.strip() if accessibility else None,
            )

            with st.spinner("🌿 Consulting local AI to craft a safe outdoor mission..."):
                generator = MissionGenerator(llm_client=llm_client)
                mission = generator.generate_mission(req)
                storage.save_mission(mission)
                st.session_state.active_mission = mission
                st.session_state.heading_out_mode = False

            st.success("✨ Your mission is ready! Transitioning to Go Outside Mode...")
            st.rerun()

        except MissionGenerationError as e:
            st.error(f"❌ Could not create mission: {e}")
        except OllamaConnectionError as e:
            st.error(f"❌ Connection error: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")


# -------------------------------------------------------------
# 2. Go Outside Mode
# -------------------------------------------------------------
elif menu == "🎒 Go Outside Mode":
    st.markdown('<div class="main-title">🎒 Go Outside Mode</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">A minimal, distraction-free card designed for quick review before locking your phone.</div>',
        unsafe_allow_html=True,
    )

    mission: Mission = st.session_state.active_mission

    if mission is None:
        # Check if there is a recent incomplete mission in the database
        recent_missions = storage.list_missions(limit=1)
        if recent_missions and not recent_missions[0].completed:
            mission = recent_missions[0]
            st.session_state.active_mission = mission

    if mission is None:
        st.info("No active mission right now. Head over to **Create Mission** to plan an outdoor excursion!")
    else:
        # Mission Card Container
        st.markdown(
            f"""
            <div class="mission-card">
                <span style="background: #2d6a4f; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">
                    ⏱️ {mission.duration_minutes} MINUTES
                </span>
                <h2 style="color: #1b4332; margin-top: 0.6rem; margin-bottom: 0.4rem;">{mission.title}</h2>
                <p style="color: #3e5c4a; font-size: 1.05rem; margin-bottom: 1rem;">{mission.description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.markdown("### 📋 Actionable Tasks")
            st.caption("Review these steps. Once you're ready, lock your screen and begin.")
            for i, task in enumerate(mission.tasks, 1):
                st.markdown(f'<div class="task-item"><strong>{i}.</strong> {task}</div>', unsafe_allow_html=True)

            if mission.required_items:
                st.markdown("#### 🎒 Items to Bring")
                items_str = ", ".join(mission.required_items)
                st.info(f"Simple essentials: **{items_str}**")

        with col_right:
            st.markdown("### 🛡️ Safety Reminders")
            for safety in mission.safety_reminders:
                st.markdown(f"- {safety}")

            if mission.reflection_question:
                st.markdown("### 🌿 Contemplation Prompt")
                st.caption("Ponder this quietly during or after your time outdoors:")
                st.markdown(f"> *\"{mission.reflection_question}\"*")

        # Heading Outside Action Banner
        st.markdown(
            """
            <div class="heading-out-box">
                <h3 style="color: #1b4332; margin-bottom: 0.3rem;">🌿 Ready to Touch Grass?</h3>
                <p style="color: #40916c; margin-bottom: 0;">
                    Lock your screen and step out. No GPS, no camera check-ins, no notifications.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚪 I'm Heading Outside", use_container_width=True, type="primary"):
                st.session_state.heading_out_mode = True
                st.toast("Enjoy the outdoors! Lock your screen now 🌿", icon="🌳")

        with col_btn2:
            st.button("🔄 Create New Mission", use_container_width=True, on_click=lambda: st.session_state.update(active_mission=None))

        # Completion Section
        st.markdown("---")
        st.markdown("### 🏁 Returned from Outside?")

        with st.expander("✅ Mark Mission Complete & Add Journal Reflection", expanded=mission.completed):
            reflection_input = st.text_area(
                "Optional Nature Journal Reflection",
                value=mission.user_reflection or "",
                placeholder="What sounds did you notice? How did the air feel? Did anything catch your eye?",
                help="This reflection is stored strictly in your local SQLite database.",
            )

            if st.button("Mark Mission Complete", type="secondary"):
                updated = storage.complete_mission(
                    mission_id=mission.id,
                    reflection=reflection_input.strip() if reflection_input else None,
                )
                st.session_state.active_mission = updated
                st.balloons()
                st.success("🎉 Wonderful! Mission completed and saved to your local nature journal.")


# -------------------------------------------------------------
# 3. My Missions
# -------------------------------------------------------------
elif menu == "📋 My Missions":
    st.markdown('<div class="main-title">📋 Mission History</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">All previously generated outdoor missions saved on your machine.</div>',
        unsafe_allow_html=True,
    )

    all_missions = storage.list_missions(limit=50)

    if not all_missions:
        st.info("No saved missions yet. Generate one in the **Create Mission** section!")
    else:
        for m in all_missions:
            status_badge = "✅ Completed" if m.completed else "⏳ In Progress"
            with st.expander(f"{m.title} — {m.duration_minutes} min ({status_badge})"):
                st.write(m.description)
                st.markdown("**Tasks:**")
                for task in m.tasks:
                    st.markdown(f"- {task}")
                if m.safety_reminders:
                    st.markdown("**Safety Tips:** " + "; ".join(m.safety_reminders))
                if m.user_reflection:
                    st.markdown(f"**Your Reflection:** *\"{m.user_reflection}\"*")
                if not m.completed:
                    if st.button(f"Make Active Mission", key=f"activate_{m.id}"):
                        st.session_state.active_mission = m
                        st.rerun()


# -------------------------------------------------------------
# 4. Nature Journal & Progress
# -------------------------------------------------------------
elif menu == "📖 Nature Journal & Progress":
    st.markdown('<div class="main-title">📖 Local Nature Journal & Progress</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">A calm, pressure-free summary of your time spent outside. No streaks, no competition.</div>',
        unsafe_allow_html=True,
    )

    stats = storage.get_progress_summary()

    # Mindful Progress Display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{stats['completed_missions']}</div>
                <div class="stat-label">Missions Completed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{stats['total_outdoor_minutes']}</div>
                <div class="stat-label">Minutes Outdoors</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="stat-card">
                <div class="stat-number">{len(stats['recent_reflections'])}</div>
                <div class="stat-label">Reflections Penned</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 📝 Recorded Reflections")

    journals = storage.list_journal_entries(limit=30)
    if not journals:
        st.info("You haven't recorded any reflections yet. After completing an outdoor mission, jot down a thought!")
    else:
        for entry in journals:
            with st.container():
                st.markdown(
                    f"""
                    <div style="background: white; border-radius: 8px; padding: 1rem; border: 1px solid #d8f3dc; margin-bottom: 0.8rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                            <strong style="color: #1b4332; font-size: 1.1rem;">{entry.mission_title}</strong>
                            <span style="color: #52796f; font-size: 0.85rem;">⏱️ {entry.duration_minutes} min • {entry.date_completed[:10]}</span>
                        </div>
                        <p style="color: #2d6a4f; font-style: italic; margin-bottom: 0;">
                            {entry.reflection or '<em>No written reflection recorded.</em>'}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# -------------------------------------------------------------
# 5. Privacy & About
# -------------------------------------------------------------
elif menu == "🔒 Privacy & About":
    st.markdown('<div class="main-title">🔒 Privacy & About</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Hacktoberfest 2026 Week 1 Challenge: "Touch Grass"</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        ### 🌿 The Mission
        Modern life keeps us tied to glowing rectangles. **TrailBuddy Local** is engineered to do the exact opposite:
        use open-weight AI running **entirely on your own computer** to help you put your phone away, step outside,
        and reconnect with nature.

        ### 🛡️ Privacy & Localhost Architecture
        """
    )

    posture = verify_privacy_posture()
    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.markdown("#### Live Privacy Audit")
        st.write(f"- **Zero External Telemetry:** {'✅ Verified' if posture['telemetry_disabled'] else '❌ Failed'}")
        st.write(f"- **External Cloud AI Calls:** {'✅ Blocked (0 Cloud APIs)' if posture['external_network_blocked'] else '❌ Failed'}")
        st.write(f"- **GPS / Location Tracking:** {'✅ Disabled (No Coordinates Requested)' if posture['gps_disabled'] else '❌ Failed'}")
        st.write(f"- **Local Inference Endpoint:** `http://127.0.0.1:11434` (`{config.DEFAULT_MODEL}`)")
        st.write(f"- **Persistence Engine:** Local SQLite (`trailbuddy.db`)")
        st.write(f"- **Streamlit Host:** `127.0.0.1:{config.STREAMLIT_PORT}`")

    with col_p2:
        st.markdown("#### Anti-Addiction Manifesto")
        st.markdown(
            """
            - 🚫 **No Streaks:** Never feel guilt for taking a day off.
            - 🚫 **No Leaderboards:** Nature exploration is not a sport.
            - 🚫 **No Social Feeds:** Your reflections belong only to you.
            - 🚫 **No Live Outdoor Screens:** Review your mission, lock your screen, step outside.
            """
        )

    st.markdown("---")
    st.caption("TrailBuddy Local is open source under the MIT License.")
