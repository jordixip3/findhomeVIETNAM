import urllib.parse
from typing import Dict, Any

class LocalizedVoiceAgent:
    def __init__(self):
        self.whatsapp_number = "+34603331391"
        self.clean_whatsapp = "34603331391"
        self.brand = "FindHome Vietnam"
        self.currency = "₫"

    def process_query(self, message: str, lang: str = "vi") -> Dict[str, Any]:
        reply = f"Hello from {self.brand}! I can assist you with roommate matching, per-person rent calculations in {self.currency}, and scheduling viewings. Connect with our coordinator 24/7 on WhatsApp {self.whatsapp_number}."
        wa_text = f"Inquiry on {self.brand}: {message}"
        wa_url = f"https://wa.me/{self.clean_whatsapp}?text={urllib.parse.quote(wa_text)}"
        return {
            "reply_text": reply,
            "action": "greeting",
            "whatsapp_url": wa_url,
            "whatsapp_display": self.whatsapp_number
        }

voice_agent = LocalizedVoiceAgent()
