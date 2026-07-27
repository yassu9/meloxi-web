"""
Mood Engine for Meloxi Web.
Wraps AIManager and preset mood categories.
"""

from typing import List, Dict, Any, Optional
from music.ai import AIManager

class MoodEngine:
    """Provides curated mood presets and AI prompt query resolution."""

    MOOD_CATEGORIES = [
        {
            "id": "sad",
            "name": "Sad & Emotional",
            "emoji": "💔",
            "gradient": "linear-gradient(135deg, #2b1055, #7597de)",
            "query": "sad bollywood emotional songs"
        },
        {
            "id": "romantic",
            "name": "Romantic Hits",
            "emoji": "💖",
            "gradient": "linear-gradient(135deg, #ff0844, #ffb199)",
            "query": "romantic bollywood love songs"
        },
        {
            "id": "chill",
            "name": "Lofi & Chill",
            "emoji": "🎧",
            "gradient": "linear-gradient(135deg, #43e97b, #38f9d7)",
            "query": "lofi slowed reverb bollywood songs"
        },
        {
            "id": "party",
            "name": "Party Bangers",
            "emoji": "🔥",
            "gradient": "linear-gradient(135deg, #f857a6, #ff5858)",
            "query": "bollywood dance party bangers"
        },
        {
            "id": "workout",
            "name": "Gym Workout",
            "emoji": "🏋️",
            "gradient": "linear-gradient(135deg, #fa709a, #fee140)",
            "query": "high energy gym workout motivation songs"
        },
        {
            "id": "sufi",
            "name": "Sufi & Ghazal",
            "emoji": "🪕",
            "gradient": "linear-gradient(135deg, #30cfd0, #330867)",
            "query": "soulful sufi ghazals nusrat fateh ali khan"
        },
        {
            "id": "devotional",
            "name": "Devotional & Peace",
            "emoji": "🕊️",
            "gradient": "linear-gradient(135deg, #ff9a9e, #fecfef)",
            "query": "spiritual bhajan peaceful aarti"
        }
    ]

    def __init__(self):
        self.ai = AIManager()

    def get_moods(self) -> List[Dict[str, Any]]:
        """Return available mood cards metadata."""
        return self.MOOD_CATEGORIES

    async def resolve_mood_query(self, mood_id: str, custom_text: Optional[str] = None) -> str:
        """Resolve mood into YouTube/catalog search query."""
        if custom_text:
            detected = await self.ai.suggest_mood(custom_text)
            if detected:
                mood_id = detected

        for item in self.MOOD_CATEGORIES:
            if item["id"] == mood_id:
                return item["query"]

        # Default fallback query
        return f"{mood_id} music hits"

mood_engine = MoodEngine()
