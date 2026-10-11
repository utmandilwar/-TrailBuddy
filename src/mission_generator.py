"""Mission generator for TrailBuddy Local.

Synthesizes personalized offline outdoor missions via local Ollama inference,
enforcing strict safety rules, screen-free interaction, and Pydantic validation.
"""

import json
import logging
import re
from typing import Optional, Dict, Any
from pydantic import ValidationError

import config
from src.schemas import Mission, MissionRequest
from src.llm import OllamaClient, OllamaError

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are TrailBuddy Local, a friendly outdoor companion and mindful nature guide.
Your purpose is to help people disconnect from screens and connect with the natural world right outside their door.

CORE PRINCIPLES:
1. SAFE & LOW-COST: Focus on observation, sensory awareness, and gentle movement. No expensive gear or purchases.
2. LEAVE NO TRACE: Never instruct users to collect specimens, pick living plants, or disturb habitats.
3. ABSOLUTE OUTDOOR SAFETY:
   - NEVER tell the user to touch unknown plants, wild mushrooms, or thorny flora.
   - NEVER tell the user to approach, feed, or handle wildlife.
   - NEVER instruct users to enter roads, active traffic, steep drop-offs, private property, or restricted areas.
   - Always include practical, environment-appropriate safety reminders (e.g., stay on paths, watch footing, hydration, sun protection).
4. SCREEN-FREE OUTDOORS:
   - Do NOT require smartphones, GPS, camera apps, or screen interaction during the activity.
   - The mission is meant to be read before going outside; the user should lock their phone.
5. HONEST & GROUNDED:
   - Do NOT promise or guarantee that specific rare wildlife will appear.
   - Do NOT pretend to know current real-time weather or local trail conditions.
6. ACCESSIBILITY:
   - Fully respect any requested mobility or accessibility needs (e.g., seated observation, level paved paths).

OUTPUT FORMAT:
Respond with ONLY a valid JSON object (no markdown fences, no conversational text) matching this schema:
{
  "title": "Short descriptive mission title (3-120 chars)",
  "description": "Short inspiring overview (1-2 sentences)",
  "duration_minutes": <number matching requested duration>,
  "tasks": [
    "Task 1: actionable sensory or observational step",
    "Task 2: actionable sensory or observational step",
    "Task 3: actionable sensory or observational step"
  ],
  "required_items": ["Optional simple household item, e.g., Water bottle", "Notebook"],
  "safety_reminders": ["Stay on clear paths", "Watch your step on uneven ground"],
  "reflection_question": "A mindful question to contemplate after returning inside"
}
Number of tasks MUST be between 3 and 5.
"""


class MissionGenerationError(Exception):
    """Raised when mission generation fails after retries."""
    pass


def extract_json_payload(raw_text: str) -> Dict[str, Any]:
    """Extract and parse a JSON dictionary from raw model text.
    
    Handles markdown code blocks (```json ... ```) or preambles.
    """
    cleaned = raw_text.strip()
    
    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    else:
        # If model included leading or trailing text outside { ... }
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            cleaned = cleaned[brace_start : brace_end + 1]

    return json.loads(cleaned)


class MissionGenerator:
    """Generates structured outdoor missions using local Ollama."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        self.client = llm_client or OllamaClient()

    def _build_user_prompt(self, request: MissionRequest) -> str:
        """Construct the prompt from user parameters."""
        prompt_parts = [
            f"Generate a safe, engaging outdoor mission with the following parameters:",
            f"- Available Time: {request.duration_minutes} minutes",
            f"- Primary Interest: {request.interest}",
            f"- Difficulty Level: {request.difficulty}",
            f"- Outdoor Environment: {request.environment}",
        ]
        if request.accessibility:
            prompt_parts.append(
                f"- Mobility & Accessibility Preferences: {request.accessibility} (ensure all tasks accommodate this)"
            )
        prompt_parts.append(
            f"Remember: exactly {request.duration_minutes} minutes duration, between 3 and 5 actionable tasks, "
            "leave no trace, no screen time required outdoors, and include practical safety reminders."
        )
        return "\n".join(prompt_parts)

    def generate_mission(self, request: MissionRequest) -> Mission:
        """Generate a validated Mission object, retrying once on malformed output.
        
        Args:
            request: The validated user MissionRequest.
            
        Returns:
            A validated Mission instance.
            
        Raises:
            MissionGenerationError: If the model repeatedly returns malformed or invalid output.
            OllamaError: If Ollama service is unreachable or errors.
        """
        user_prompt = self._build_user_prompt(request)
        attempts = 0
        max_attempts = 1 + config.MAX_RETRIES  # 1 initial + 1 retry = 2 attempts
        last_error: Optional[Exception] = None

        while attempts < max_attempts:
            attempts += 1
            try:
                if attempts == 1:
                    raw_output = self.client.generate(
                        prompt=user_prompt,
                        system_prompt=SYSTEM_PROMPT,
                        json_format=True,
                    )
                else:
                    logger.warning(
                        "Retrying mission generation due to prior error: %s", last_error
                    )
                    retry_prompt = (
                        f"{user_prompt}\n\n"
                        f"IMPORTANT CORRECTION: The previous output failed with: {str(last_error)}. "
                        "You MUST return ONLY valid JSON with fields: 'title', 'description', "
                        "'duration_minutes' (number), 'tasks' (array of 3-5 strings), "
                        "'required_items' (array), 'safety_reminders' (array of strings), "
                        "'reflection_question' (string)."
                    )
                    raw_output = self.client.generate(
                        prompt=retry_prompt,
                        system_prompt=SYSTEM_PROMPT,
                        json_format=True,
                    )

                data = extract_json_payload(raw_output)
                if not isinstance(data, dict):
                    raise ValueError(f"Expected JSON object, got {type(data).__name__}")

                # Ensure duration_minutes is properly populated
                if "duration_minutes" not in data or not data["duration_minutes"]:
                    data["duration_minutes"] = request.duration_minutes

                mission = Mission(**data)
                return mission

            except (json.JSONDecodeError, ValueError, ValidationError) as err:
                last_error = err
                logger.info(
                    "Attempt %d/%d failed validation: %s", attempts, max_attempts, err
                )
                if attempts >= max_attempts:
                    break

        raise MissionGenerationError(
            f"Unable to generate a valid mission after retry. Cause: {last_error}"
        )
