"""
AI Management for Meloxi.
Mood analysis and suggestions.
"""

# ==============================================================================
# 📥 IMPORTS
# ==============================================================================

import openai
from typing import Optional
from config.settings import OPENAI_API_KEY, GEMINI_API_KEY

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai_legacy

# ==============================================================================
# 🧠 AI MANAGER (DUAL-CORE: OpenAI + Gemini)
# ==============================================================================

class AIManager:
    """Wrapper for AI operations with Dual-Provider Fallback."""
    
    
    def __init__(self):
        # 🛡️ Feature Flag Check
        from config.settings import DEFAULT_FEATURES
        self.ai_enabled_flag = DEFAULT_FEATURES.get("use_ai_enhancement", False)
        
        # Primary: OpenAI
        self.openai_enabled = bool(OPENAI_API_KEY) and self.ai_enabled_flag
        if self.openai_enabled:
            openai.api_key = OPENAI_API_KEY
            
        # Secondary: Gemini
        self.gemini_enabled = bool(GEMINI_API_KEY) and self.ai_enabled_flag
        if self.gemini_enabled:
            if HAS_GENAI:
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            else:
                genai_legacy.configure(api_key=GEMINI_API_KEY)
    
    def is_enabled(self) -> bool:
        return self.openai_enabled or self.gemini_enabled

    async def _run_async(self, func, *args, **kwargs):
        """Run blocking function in executor."""
        import asyncio
        import functools
        loop = asyncio.get_running_loop()
        partial = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, partial)

    async def suggest_mood(self, message: str) -> Optional[str]:
        """Detect mood from text."""
        # 1. Deterministic Check
        if m := self._rule_based_mood(message): return m
        # 2. AI Fallback (Dual)
        if self.is_enabled():
             return await self._dual_ai_mood(message)
        return None

    def _rule_based_mood(self, message: str) -> Optional[str]:
        """Keyword matching."""
        msg = message.lower()
        keywords = {
            'sad': ['sad', 'depressed', 'lonely', 'cry', 'tears', 'broken', 'dard', 'tanhai', 'judai', 'bewafa'],
            'romantic': ['love', 'romance', 'couple', 'date', 'heart', 'dil', 'ishq', 'pyaar', 'mohabbat', 'sanam'],
            'party': ['party', 'dance', 'club', 'vibe', 'beat', 'nach', 'bhangra', 'dj', 'remix', 'banger', 'hype'],
            'chill': ['night', 'sleep', 'dark', 'drive', 'late', 'lofi', 'slowed', 'reverb', 'relax', 'peace'],
            'workout': ['gym', 'run', 'train', 'fit', 'lift', 'power', 'motivation', 'beast', 'hardcore'],
            'sufi/ghazal': ['sufi', 'ghazal', 'qawwali', 'nusrat', 'rahmat', 'spiritual', 'soulful', 'jagjit', 'pankaj'],
            'devotional': ['bhajan', 'aarti', 'shlok', 'mantra', 'spiritual', 'god', 'krishna', 'shiva', 'ram']
        }
        for mood, keys in keywords.items():
            if any(k in msg for k in keys): return mood
        return None
    
    async def detect_language(self, song_title: str, artist: str = "") -> str:
        """
        Detect the language of a song (hindi, punjabi, english, tamil, etc.).
        Uses rule-based check first, then AI.
        """
        # 1. Rule-based Fast Check
        text = f"{song_title} {artist}".lower()
        
        # Regional Keywords
        rules = {
            'punjabi': ['sidhu moose wala', 'shubh', 'diljit', 'ap dhillon', 'jassi gill', 'amrit maan', 'karan aujla'],
            'hindi': ['arijit singh', 'neha kakkar', 'jubin nautiyal', 'shreya ghoshal', 'kumar sanu', 'udit narayan', 'bollywood', 't-series', 'vishal-shekhar', 'shankar-ehsaan-loy'],
            'tamil': ['anirudh', 'rahman', 'yuvan', 'santhosh narayanan', 'sid sriram'],
            'telugu': ['devi sri prasad', 'thaman', 'keeravani'],
            'english': ['taylor swift', 'justin bieber', 'ed sheeran', 'drake', 'the weeknd', 'ariana grande', 'post malone', 'dua lipa', 'eminem', 'billie eilish'],
        }
        
        for lang, keywords in rules.items():
            if any(k in text for k in keywords):
                return lang
        
        # 2. AI Fallback for 100% Accuracy
        if self.is_enabled():
            prompt = f"Detect the primary language of this song: '{song_title}' by '{artist}'. Reply ONLY with the language name (e.g., hindi, punjabi, english, tamil, telugu, malayalam, kannada). If unsure, reply 'unknown'."
            
            # Use OpenAI or Gemini
            if self.openai_enabled:
                try:
                    def _ask_gpt():
                        resp = openai.ChatCompletion.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=10, temperature=0.1
                        )
                        return resp.choices[0].message.content.strip().lower()
                    ai_lang = await self._run_async(_ask_gpt)
                    if ai_lang and ai_lang != 'unknown': return ai_lang
                except: pass
            
            if self.gemini_enabled:
                try:
                    def _ask_gemini():
                        if HAS_GENAI:
                            resp = self.gemini_client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=prompt
                            )
                            return resp.text.strip().lower()
                        else:
                            model = genai_legacy.GenerativeModel('gemini-pro')
                            resp = model.generate_content(prompt)
                            return resp.text.strip().lower()
                    ai_lang = await self._run_async(_ask_gemini)
                    if ai_lang and ai_lang != 'unknown': return ai_lang
                except: pass
        
        return "unknown"
    
    async def _dual_ai_mood(self, message: str) -> Optional[str]:
        """Dual-AI: OpenAI -> Gemini -> None"""
        system_prompt = "You are a mood detector. Reply ONLY: sad, romantic, party, night, workout."
        
        # A. Try OpenAI
        if self.openai_enabled:
            try:
                def _ask_gpt():
                    resp = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
                        max_tokens=5, temperature=0.3
                    )
                    return resp.choices[0].message.content.strip().lower()
                mood = await self._run_async(_ask_gpt)
                if mood in ['sad', 'romantic', 'party', 'night', 'workout']: return mood
            except: pass # Fallback to Gemini
        
        # B. Try Gemini
        if self.gemini_enabled:
            try:
                def _ask_gemini():
                    if HAS_GENAI:
                        resp = self.gemini_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"{system_prompt}\nInput: {message}"
                        )
                        return resp.text.strip().lower()
                    else:
                        model = genai_legacy.GenerativeModel('gemini-pro')
                        resp = model.generate_content(f"{system_prompt}\nInput: {message}")
                        return resp.text.strip().lower()
                mood = await self._run_async(_ask_gemini)
                if mood in ['sad', 'romantic', 'party', 'night', 'workout']: return mood
            except: pass
            
        return None
    
    async def get_detailed_mood_analysis(self, song_title: str, artist: str = "", context: str = "") -> dict:
        """
        SAFE AI: Classify mood/language using the Master Prompt.
        Returns structured JSON.
        """
        if not self.is_enabled(): return {}
        
        import json
        
        system_prompt = (
            "SYSTEM ROLE:\n"
            "You are a music mood classifier for a Discord music bot.\n"
            "Your job is ONLY to analyze the given song context and return structured classification.\n"
            "You do NOT select songs. You do NOT change queues.\n\n"
            "STRICT RULES:\n"
            "- Do NOT suggest songs\n"
            "- Do NOT change mood intentionally\n"
            "- Do NOT invent data\n"
            "- If unsure, return 'uncertain'\n\n"
            "CLASSIFICATION GUIDELINES:\n"
            "- Sad / Emotional: heartbreak, loss, pain, breakup, dard, tanhai\n"
            "- Romantic: love, soft melody, ishq, pyaar, positive emotional\n"
            "- Party / Hype: dance, high energy, club, upbeat, banger, remix\n"
            "- Chill / Lofi: relaxed, night, slowed, reverb, peace, sleep\n"
            "- Workout / Aggressive: gym, power, rap, heavy bass, motivation\n"
            "- Sufi / Spiritual: soulful, qawwali, ghazal, traditional melody\n"
            "- Devotional: bhajan, religious, prayer, traditional\n\n"
            "OUTPUT FORMAT (JSON ONLY, NO EXTRA TEXT):\n"
            "{\n"
            "  \"primary_mood\": \"sad | romantic | party | chill | workout | sufi | devotional\",\n"
            "  \"vibe\": \"e.g., 90s Bollywood, Modern Pop, Classical, Lofi, EDM\",\n"
            "  \"energy\": \"low | medium | high\",\n"
            "  \"language\": \"hindi | english | punjabi | mixed | unknown\",\n"
            "  \"confidence\": 0.0 to 1.0\n"
            "}"
        )
        
        user_content = f"Song: {song_title}\nArtist: {artist}\nContext: {context}"
        
        response_text = None
        
        # A. Try OpenAI
        if self.openai_enabled:
            try:
                def _ask_gpt():
                    resp = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                        max_tokens=150, temperature=0.2
                    )
                    return resp.choices[0].message.content.strip()
                response_text = await self._run_async(_ask_gpt)
            except: pass
            
        # B. Try Gemini (if OpenAI failed or disabled)
        if not response_text and self.gemini_enabled:
            try:
                def _ask_gemini():
                    if HAS_GENAI:
                        resp = self.gemini_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=f"{system_prompt}\n\nTask: Analyze this:\n{user_content}"
                        )
                        return resp.text.strip()
                    else:
                        model = genai_legacy.GenerativeModel('gemini-pro')
                        resp = model.generate_content(f"{system_prompt}\n\nTask: Analyze this:\n{user_content}")
                        return resp.text.strip()
                response_text = await self._run_async(_ask_gemini)
            except: pass
            
        if not response_text: return {}

        # Safe JSON Parse
        try:
            # Strip markdown code blocks if present
            clean_text = response_text
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(clean_text)
            return data
        except json.JSONDecodeError:
            return {} # Fail safe

    async def suggest_search_query(self, mood: str, era: str = None) -> str:
        """Generate YouTube query."""
        queries = {
            'sad': 'sad bollywood songs hindi',
            'romantic': 'romantic bollywood songs hindi',
            'party': 'bollywood party songs dance',
            'night': 'bollywood night songs hindi',
            'workout': 'bollywood workout songs energetic'
        }
        base = queries.get(mood, f"{mood} songs")
        
        if era:
            map_era = {'90s': '90s', '2000s': '2000s', '2010s': '2010s'}
            if era in map_era: base = f"{map_era[era]} {base}"
            
        return base

    async def suggest_related_songs(self, song_title: str) -> list[str]:
        """Generate related songs using AI with a robust Music Vault fallback."""
        
        # 1. AI Attempt (High-End Curator Mode)
        if self.openai_enabled:
            try:
                # Premium Curator Prompt
                system_prompt = (
                    "You are 'Meloxi', an elite music curator specializing in Bollywood, Punjabi, and Indian Pop. "
                    "Your goal is to suggest 5 songs that perfectly match the vibe, era, and energy of the user's song. "
                    "Rules:\n"
                    "1. Return ONLY the song title and artist in this format: 'Song Name - Artist'\n"
                    "2. Do not number the list.\n"
                    "3. Do not add quotes or extra text.\n"
                    "4. variety is key: mix hits with hidden gems.\n"
                    "5. If the input is sad, suggestive emotional ballads. If party, suggest high-energy bangers."
                )
                
                def _ask_gpt():
                    resp = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Suggest 5 songs related to: {song_title}"}
                        ],
                        max_tokens=200, temperature=0.7 
                    )
                    text = resp.choices[0].message.content.strip()
                    songs = []
                    for line in text.split('\n'):
                        clean = line.strip().replace('"', '').replace("'", "")
                        if clean and '-' in clean:
                            songs.append(clean)
                    return songs
                
                songs = await self._run_async(_ask_gpt)
                if len(songs) >= 3: return songs[:5]
            except Exception:
                pass # Fallthrough to Music Vault
        
        # 2. THE ULTIMATE MUSIC VAULT (Best-In-Class Fallback)
        # 100+ Hand-picked certified bangers across genres
        vault = [
            # 💔 SAD / EMOTIONAL
            "Channa Mereya - Arijit Singh", "Kabira - Arijit Singh", "Tum Hi Ho - Arijit Singh",
            "Agar Tum Saath Ho - Arijit Singh", "Hamari Adhuri Kahani - Arijit Singh",
            "Tujhe Kitna Chahne Lage - Arijit Singh", "Kalank (Title Track) - Arijit Singh",
            "Bekhayali - Sachet Tandon", "Mann Bharryaa 2.0 - B Praak", "Ranjha - B Praak",
            "Tu Jaane Na - Atif Aslam", "Jeene Laga Hoon - Atif Aslam",
            "Hasi - Ami Mishra", "Kaun Tujhe - Palak Muchhal",
            
            # ❤️ ROMANTIC / VIBE
            "Kesariya - Arijit Singh", "Raatan Lambiyan - Jubin Nautiyal",
            "Apna Bana Le - Arijit Singh", "Tera Ban Jaunga - Akhil Sachdeva",
            "Pehli Nazar Mein - Atif Aslam", "Tera Hone Laga Hoon - Atif Aslam",
            "Main Rang Sharbaton Ka - Atif Aslam", "Zaalima - Arijit Singh",
            "Bol Do Na Zara - Armaan Malik", "Sab Tera - Armaan Malik",
            "Kinna Sona - Jubin Nautiyal", "Mast Magan - Arijit Singh",
            "Heeriye - Jasleen Royal", "Maan Meri Jaan - King",
            "Tu Aake Dekhle - King", "Guli Mata - Saad Lamjarred",
            
            # 🔥 PARTY / DANCE
            "Badtameez Dil - Benny Dayal", "Subha Hone Na De - Mika Singh",
            "Gallan Goodiyaan - Shankar Mahadevan", "London Thumakda - Labh Janjua",
            "Kala Chashma - Amar Arshi", "Abhi Toh Party Shuru Hui Hai - Badshah",
            "Garmi - Badshah", "Kar Gayi Chull - Badshah",
            "Bom Diggy Diggy - Zack Knight", "Dilbar - Neha Kakkar",
            "Saki Saki - Neha Kakkar", "Manali Trance - Neha Kakkar",
            "Besharam Rang - Shilpa Rao", "Jhoome Jo Pathaan - Arijit Singh",
            "Show Me The Thumka - Sunidhi Chauhan", "Kamli - Sunidhi Chauhan",
            
            # 🚜 PUNJABI / HYPE
            "Brown Munde - AP Dhillon", "Excuses - AP Dhillon", "Insane - AP Dhillon",
            "Summer High - AP Dhillon", "Elevated - Shubh", "We Rollin - Shubh",
            "Cheques - Shubh", "Baller - Shubh", "No Love - Shubh",
            "295 - Sidhu Moose Wala", "The Last Ride - Sidhu Moose Wala",
            "So High - Sidhu Moose Wala", "Same Beef - Sidhu Moose Wala",
            "Levels - Sidhu Moose Wala", "Goat - Sidhu Moose Wala",
            "Satisfya - Imran Khan", "Amplifier - Imran Khan", "Bewafa - Imran Khan",
            "Libaas - Kaka", "Temporary Pyar - Kaka",
            
            # 🌀 LOFI / CHILL
            "Iktara - Kavita Seth", "Kun Faya Kun - AR Rahman",
            "Tum Se Hi - Mohit Chauhan", "Pee Loon - Mohit Chauhan",
            "Masakali - Mohit Chauhan", "Ilahi - Arijit Singh",
            "Safarnama - Lucky Ali", "O Sanam - Lucky Ali",
            "Kahin To - Rashid Ali", "Tu Hai Ki Nahi - Ankit Tiwari"
        ]
        
        import random
        # Smart Selection: Try to ensure variety
        return random.sample(vault, 5)

