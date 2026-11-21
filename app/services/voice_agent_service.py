"""
FindHome Vietnam — Advanced AI Real Estate Voice & WhatsApp Agent
Conversational multi-turn engine with per-user session memory,
dynamic property recommendation, pagination ("more options" / "más opciones"),
detailed property inspection, visit booking, and rent split calculations.
Connected to official WhatsApp support line: +34 603 331 391
"""

import re
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.models.database import get_properties

AGENT_WHATSAPP_NUMBER = "+34603331391"
AGENT_WHATSAPP_CLEAN = "34603331391"

BRAND_NAME = "FindHome Vietnam"
COUNTRY_NAME = "Vietnam"
CURRENCY_SYMBOL = "₫"
DEFAULT_LANG = "vi"
AVG_RENT_BENCHMARK = 18000000
LOCAL_CITIES = ["Ho Chi Minh City", "Hanoi", "Da Nang", "Hai Phong", "Can Tho"]


class UserSession:
    """Maintains multi-turn context and conversational state per phone/user."""

    def __init__(self, user_id: str, user_name: str = "Visitor"):
        self.user_id = user_id
        self.user_name = user_name or "Visitor"
        self.city: Optional[str] = None
        self.offset: int = 0
        self.last_properties: List[Dict[str, Any]] = []
        self.selected_property: Optional[Dict[str, Any]] = None
        self.budget_max: Optional[float] = None
        self.roommates_count: Optional[int] = None
        self.state: str = "idle"
        self.last_visit_booking: Optional[Dict[str, Any]] = None
        self.last_activity = datetime.now()

    def touch(self):
        self.last_activity = datetime.now()


class LocalizedVoiceAgent:
    """
    Intelligent conversational voice & WhatsApp agent for FindHome Vietnam.
    Maintains session memory, supports pagination, detailed inspection, and booking.
    """

    def __init__(self):
        self.whatsapp_number = AGENT_WHATSAPP_NUMBER
        self.clean_whatsapp = AGENT_WHATSAPP_CLEAN
        self.brand = BRAND_NAME
        self.currency = CURRENCY_SYMBOL
        self.sessions: Dict[str, UserSession] = {}

    def get_or_create_session(self, user_id: Optional[str], user_name: Optional[str] = None) -> UserSession:
        uid = str(user_id or "anonymous_guest").strip()
        now = datetime.now()
        expired = [k for k, s in self.sessions.items() if (now - s.last_activity).total_seconds() > 86400]
        for k in expired:
            del self.sessions[k]

        if uid not in self.sessions:
            self.sessions[uid] = UserSession(uid, user_name or "Visitor")
        else:
            if user_name and user_name != "Visitor":
                self.sessions[uid].user_name = user_name
            self.sessions[uid].touch()

        return self.sessions[uid]

    def process_query(
        self,
        message: str,
        lang: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        channel: str = "whatsapp"
    ) -> Dict[str, Any]:
        target_lang = lang or DEFAULT_LANG
        session = self.get_or_create_session(user_id, user_name)
        msg_raw = (message or "").strip()
        msg_clean = msg_raw.lower()

        # 1. Greetings
        if any(msg_clean == w or msg_clean.startswith(f"{w} ") for w in [
            "hello", "hi", "hey", "hola", "buenos dias", "buenos días", "buenas tardes",
            "konnichiwa", "annyeong", "sawasdee", "xin chao", "namaste", "marhaban", "hallo"
        ]):
            return self._handle_greeting(session, target_lang, channel)

        # 2. Pagination / More options
        more_keywords = [
            "more options", "show more", "next", "see more", "more", "other options", "another flat",
            "mas opciones", "más opciones", "muestrame mas", "muéstrame más", "tienes mas", "tienes más",
            "ver mas", "ver más", "siguiente", "otras opciones", "otro piso",
            "もっと見る", "더 보기", "เพิ่มเติม", "thêm", "lagi", "dagdag", "और विकल्प", "المزيد"
        ]
        if any(k in msg_clean for k in more_keywords):
            return self._handle_more_options(session, target_lang, channel)

        # 3. Selection (1, 2, 3...)
        sel_idx = self._extract_selection_index(msg_clean)
        if sel_idx is not None and session.last_properties:
            return self._handle_select_property(session, sel_idx, target_lang, channel)

        # 4. Visit Scheduling
        if self._is_visit_request(msg_clean):
            return self._handle_visit_scheduling(session, msg_raw, target_lang, channel)

        # 5. City Search
        matched_city = None
        for city in LOCAL_CITIES:
            if city.lower() in msg_clean:
                matched_city = city
                break

        beds_match = re.search(r"(\d+)\s*(bedrooms|beds|rooms|habitaciones|dormitorios|habs|cuartos)", msg_clean)
        bedrooms = int(beds_match.group(1)) if beds_match else None

        budget_match = re.search(r"(\d[\d\.,]{2,})", msg_clean)
        budget_max = None
        if budget_match:
            try:
                budget_max = float(budget_match.group(1).replace(".", "").replace(",", ""))
            except Exception:
                budget_max = None

        if matched_city or (session.city and any(w in msg_clean for w in ["flat", "apartment", "piso", "arriendo", "rent", "room", "habitacion", "zona", "area", "house"])):
            target_city = matched_city or session.city
            return self._handle_city_search(session, target_city, bedrooms, budget_max, target_lang, channel)

        # 6. Rent-Split Calculator
        calc_match = re.search(r"(\d+)\s*(people|roommates|friends|personas|amigos|compañeros)", msg_clean)
        if any(w in msg_clean for w in ["calculate", "split", "rent", "share", "calcular", "reparto", "cuota", "cuanto"]) or (calc_match and budget_max):
            roommates = int(calc_match.group(1)) if calc_match else (session.roommates_count or 4)
            total_rent = budget_max if budget_max else AVG_RENT_BENCHMARK
            return self._handle_calculator(session, roommates, total_rent, target_lang, channel)

        # 7. FAQs
        faq_res = self._handle_faqs(session, msg_clean, target_lang, channel)
        if faq_res:
            return faq_res

        # 8. Human Agent Request
        if any(w in msg_clean for w in ["human", "agent", "call", "operator", "humano", "persona", "operador", "llamar"]):
            return self._handle_human_request(session, target_lang, channel)

        # 9. Contextual fallback
        return self._handle_fallback(session, msg_raw, target_lang, channel)

    def _handle_greeting(self, session: UserSession, lang: str, channel: str) -> Dict[str, Any]:
        session.state = "browsing"
        is_es = lang == "es"
        top_cities = ", ".join(LOCAL_CITIES[:4])

        if channel == "whatsapp":
            if is_es:
                reply = (
                    f"¡Hola! Te damos la bienvenida al Asistente Oficial de *{self.brand}* 🏡\n\n"
                    f"Te ayudo a encontrar habitaciones y departamentos compartidos verificados en {COUNTRY_NAME}:\n"
                    f"• *Ciudades destacadas:* {top_cities}\n\n"
                    f"¿En qué ciudad te gustaría encontrar arriendo o cuál es tu presupuesto mensual?"
                )
            else:
                reply = (
                    f"Hello! Welcome to *{self.brand}* Official AI Assistant 🏡\n\n"
                    f"I can help you find verified shared apartments, calculate per-person rent splits, and coordinate viewings across {COUNTRY_NAME}.\n"
                    f"• *Featured locations:* {top_cities}\n\n"
                    f"Which city or budget are you looking for?"
                )
        else:
            if is_es:
                reply = f"¡Hola! Soy el Agente de Voz de {self.brand}. Te ayudo a buscar vivienda compartida en {COUNTRY_NAME}. ¿Qué ciudad buscas?"
            else:
                reply = f"Hello! I am your AI Voice Agent for {self.brand}. I can help you find shared apartments in {COUNTRY_NAME}. What city are you interested in?"

        return {
            "reply_text": reply,
            "action": "greeting",
            "whatsapp_url": self.build_whatsapp_link(f"Hello {self.brand}, I am looking for shared housing options.")
        }

    def _handle_city_search(
        self,
        session: UserSession,
        city: str,
        bedrooms: Optional[int],
        budget_max: Optional[float],
        lang: str,
        channel: str
    ) -> Dict[str, Any]:
        session.city = city
        session.offset = 0
        is_es = lang == "es"

        props = self._query_properties(city=city)
        if not props:
            props = get_properties()

        session.last_properties = props[:3]
        total_found = len(props)

        if channel == "whatsapp":
            items_text = []
            for i, p in enumerate(session.last_properties, 1):
                rent_total = p.get("total_rent", AVG_RENT_BENCHMARK)
                beds = p.get("bedrooms", 4)
                rent_p = round(rent_total / max(1, beds))
                title = p.get("title", f"Apartment in {city}")
                addr = p.get("address") or p.get("neighborhood") or city
                surface = p.get("surface", 120)
                if not is_es:
                    items_text.append(
                        f"*{i}️⃣ {title}*\n"
                        f"📍 {addr}\n"
                        f"🛏️ {beds} beds | 📐 {surface} m² | 💵 *{rent_p:,} {self.currency}/person/mo* (Total: {rent_total:,} {self.currency})"
                    )
                else:
                    items_text.append(
                        f"*{i}️⃣ {title}*\n"
                        f"📍 {addr}\n"
                        f"🛏️ {beds} habs | 📐 {surface} m² | 💵 *{rent_p:,} {self.currency}/persona/mes* (Total: {rent_total:,} {self.currency})"
                    )

            cards = "\n\n".join(items_text)
            if is_es:
                reply = (
                    f"🏙️ *Viviendas disponibles en {city} ({total_found} encontradas):*\n\n"
                    f"{cards}\n\n"
                    f"👉 *¿Cómo deseas continuar?*\n"
                    f"• Escribe *1*, *2* o *3* para ver la ficha completa y agendar visita.\n"
                    f"• Escribe *'más opciones'* para ver los siguientes departamentos.\n"
                    f"• O indícame si buscas un presupuesto o zona particular."
                )
            else:
                reply = (
                    f"🏙️ *Available Shared Listings in {city} ({total_found} found):*\n\n"
                    f"{cards}\n\n"
                    f"👉 *Next steps:*\n"
                    f"• Reply *1*, *2* or *3* to view full details and book a viewing.\n"
                    f"• Reply *'more options'* to see next available listings.\n"
                    f"• Or state your target budget or preferred neighborhood."
                )
        else:
            reply = f"Found {total_found} listings in {city}. First option displayed on screen."

        return {
            "reply_text": reply,
            "action": "property_recommendations",
            "city": city,
            "suggested_properties": session.last_properties,
            "total_count": total_found
        }

    def _handle_more_options(self, session: UserSession, lang: str, channel: str) -> Dict[str, Any]:
        target_city = session.city or LOCAL_CITIES[0]
        session.offset += 3
        is_es = lang == "es"

        all_props = self._query_properties(city=target_city)
        if not all_props:
            all_props = get_properties()

        if session.offset >= len(all_props):
            session.offset = 0
            next_props = all_props[:3]
            wrapped = True
        else:
            next_props = all_props[session.offset:session.offset + 3]
            wrapped = False

        session.last_properties = next_props

        if channel == "whatsapp":
            items_text = []
            for i, p in enumerate(next_props, 1):
                rent_total = p.get("total_rent", AVG_RENT_BENCHMARK)
                beds = p.get("bedrooms", 4)
                rent_p = round(rent_total / max(1, beds))
                title = p.get("title", f"Apartment in {target_city}")
                addr = p.get("address") or p.get("neighborhood") or target_city
                surface = p.get("surface", 120)
                if not is_es:
                    items_text.append(
                        f"*{i}️⃣ {title}*\n"
                        f"📍 {addr}\n"
                        f"🛏️ {beds} beds | 📐 {surface} m² | 💵 *{rent_p:,} {self.currency}/person/mo* (Total: {rent_total:,} {self.currency})"
                    )
                else:
                    items_text.append(
                        f"*{i}️⃣ {title}*\n"
                        f"📍 {addr}\n"
                        f"🛏️ {beds} habs | 📐 {surface} m² | 💵 *{rent_p:,} {self.currency}/persona/mes* (Total: {rent_total:,} {self.currency})"
                    )

            cards = "\n\n".join(items_text)
            header = f"🔄 *Next {len(next_props)} listings in {target_city}:*" if not is_es else f"🔄 *Siguientes {len(next_props)} opciones en {target_city}:*"
            if wrapped:
                header = f"🔄 *All listings in {target_city} viewed. Showing top recommendations:*" if not is_es else f"🔄 *Has visto todas las opciones en {target_city}. Te muestro las principales:*"

            if not is_es:
                reply = (
                    f"{header}\n\n"
                    f"{cards}\n\n"
                    f"👉 Reply *1*, *2* or *3* to view details or book a tour, or name another city."
                )
            else:
                reply = (
                    f"{header}\n\n"
                    f"{cards}\n\n"
                    f"👉 Responde *1*, *2* o *3* para ver detalles o agendar visita, o escribe otra ciudad."
                )
        else:
            reply = f"Showing more listings in {target_city}."

        return {
            "reply_text": reply,
            "action": "property_recommendations",
            "city": target_city,
            "suggested_properties": next_props,
            "offset": session.offset
        }

    def _handle_select_property(self, session: UserSession, idx: int, lang: str, channel: str) -> Dict[str, Any]:
        if idx < 0 or idx >= len(session.last_properties):
            idx = 0

        prop = session.last_properties[idx]
        session.selected_property = prop
        session.state = "viewing_detail"
        is_es = lang == "es"

        title = prop.get("title", "Selected Residence")
        city = prop.get("city", session.city or LOCAL_CITIES[0])
        addr = prop.get("address", city)
        beds = prop.get("bedrooms", 4)
        baths = prop.get("bathrooms", 2)
        surface = prop.get("surface", 120)
        rent_total = prop.get("total_rent", AVG_RENT_BENCHMARK)
        rent_p = round(rent_total / max(1, beds))
        desc = prop.get("desc", prop.get("description", "Fully furnished shared living space."))
        contact = prop.get("contact_name", f"{self.brand} Local Coordinator")

        if channel == "whatsapp":
            if is_es:
                reply = (
                    f"✨ *Detalles de la Opción {idx + 1}:*\n"
                    f"🏠 *{title}*\n\n"
                    f"📍 *Ubicación:* {addr}, {city}\n"
                    f"💶 *Cuota individual:* *{rent_p:,} {self.currency}/persona/mes*\n"
                    f"💰 *Alquiler total:* {rent_total:,} {self.currency}/mes ({beds} habs, {baths} baños)\n"
                    f"📐 *Superficie:* {surface} m²\n"
                    f"📋 *Descripción:* {desc}\n"
                    f"👤 *Gestión directa:* {contact}\n\n"
                    f"📅 *¿Deseas coordinar una visita virtual o presencial?*\n"
                    f"Dime qué día y horario te viene bien (por ejemplo: *'Mañana a las 17:00'* o *'El viernes por la tarde'*) y te la agendo de inmediato."
                )
            else:
                reply = (
                    f"✨ *Details for Option {idx + 1}:*\n"
                    f"🏠 *{title}*\n\n"
                    f"📍 *Address:* {addr}, {city}\n"
                    f"💵 *Per-person rent:* *{rent_p:,} {self.currency}/month*\n"
                    f"💰 *Total rent:* {rent_total:,} {self.currency}/month ({beds} bed, {baths} bath)\n"
                    f"📐 *Surface:* {surface} m²\n"
                    f"📋 *Features:* {desc}\n"
                    f"👤 *Coordinator:* {contact}\n\n"
                    f"📅 *Would you like to schedule an in-person or virtual tour?*\n"
                    f"Let me know your preferred day and time (e.g., *'Tomorrow at 5:00 PM'* or *'Friday afternoon'*) to confirm your viewing."
                )
        else:
            reply = f"Option {idx + 1} selected: {title} in {city}."

        return {
            "reply_text": reply,
            "action": "property_detail",
            "property": prop
        }

    def _handle_visit_scheduling(self, session: UserSession, raw_msg: str, lang: str, channel: str) -> Dict[str, Any]:
        if not session.selected_property and session.last_properties:
            session.selected_property = session.last_properties[0]

        target_prop = session.selected_property
        prop_title = target_prop.get("title", "Selected Apartment") if target_prop else "Listing"
        prop_city = target_prop.get("city", session.city or LOCAL_CITIES[0]) if target_prop else "Your location"
        prop_addr = target_prop.get("address", "") if target_prop else ""
        is_es = lang == "es"

        session.state = "visit_confirmed"
        session.last_visit_booking = {
            "property": prop_title,
            "city": prop_city,
            "time": raw_msg,
            "user": session.user_name,
            "phone": session.user_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if channel == "whatsapp":
            if is_es:
                reply = (
                    f"✅ *¡Visita Pre-Agendada con Éxito!*\n\n"
                    f"🏠 *Vivienda:* {prop_title}\n"
                    f"📍 *Ubicación:* {prop_addr or prop_city}\n"
                    f"🕒 *Horario solicitado:* {raw_msg}\n"
                    f"👤 *Titular:* {session.user_name} ({session.user_id})\n\n"
                    f"Nuestro coordinador local de *{self.brand}* te contactará por este mismo chat de WhatsApp para confirmar los detalles de acceso.\n\n"
                    f"¿Deseas consultar algo más sobre el depósito, contratos o ver otras opciones?"
                )
            else:
                reply = (
                    f"✅ *Viewing Pre-Scheduled Successfully!*\n\n"
                    f"🏠 *Property:* {prop_title}\n"
                    f"📍 *Location:* {prop_addr or prop_city}\n"
                    f"🕒 *Requested Time:* {raw_msg}\n"
                    f"👤 *Contact:* {session.user_name} ({session.user_id})\n\n"
                    f"Our local coordinator at *{self.brand}* will reach out on this WhatsApp chat to finalize viewing instructions.\n\n"
                    f"Would you like to ask about lease terms, deposits, or view other flats?"
                )
        else:
            reply = f"Viewing booked for {prop_title} at {raw_msg}."

        return {
            "reply_text": reply,
            "action": "visit_booked",
            "booking": session.last_visit_booking
        }

    def _handle_calculator(self, session: UserSession, roommates: int, total_rent: float, lang: str, channel: str) -> Dict[str, Any]:
        roommates = max(1, roommates)
        per_person = round(total_rent / roommates)
        is_es = lang == "es"

        if channel == "whatsapp":
            if is_es:
                reply = (
                    f"🧮 *Cálculo de Reparto de Arriendo:*\n\n"
                    f"• *Alquiler total:* {int(total_rent):,} {self.currency}/mes\n"
                    f"• *Compañeros:* {roommates} personas\n"
                    f"• *Cuota individual:* 👉 *{per_person:,} {self.currency}/persona/mes*\n\n"
                    f"¿Deseas que te recomiende viviendas de {roommates} habitaciones que se adapten a este presupuesto?"
                )
            else:
                reply = (
                    f"🧮 *Rent-Split Breakdown:*\n\n"
                    f"• *Total Apartment Rent:* {int(total_rent):,} {self.currency}/month\n"
                    f"• *Roommates:* {roommates} people\n"
                    f"• *Individual Share:* 👉 *{per_person:,} {self.currency}/person/month*\n\n"
                    f"Would you like to view verified {roommates}-bedroom apartments in this price range?"
                )
        else:
            reply = f"Per-person quota is {per_person:,} {self.currency}/month for {roommates} people."

        return {
            "reply_text": reply,
            "action": "calculator_result",
            "per_person": per_person,
            "total_rent": total_rent,
            "roommates": roommates
        }

    def _handle_faqs(self, session: UserSession, msg: str, lang: str, channel: str) -> Optional[Dict[str, Any]]:
        is_es = lang == "es"
        if any(w in msg for w in ["deposit", "fianza", "garantia", "garantía", "deposito", "depósito", "보증금", "敷金"]):
            if is_es:
                reply = (
                    f"🔒 *Garantías y Depósito en {COUNTRY_NAME}:*\n\n"
                    f"• El depósito legal estándar equivale a 1 mes de arriendo, protegido conforme a la normativa vigente.\n"
                    f"• Se restituye al finalizar el contrato.\n"
                    f"• En {self.brand} fomentamos contratos claros sin cobros abusivos.\n\n"
                    f"¿Deseas revisar opciones disponibles en {session.city or LOCAL_CITIES[0]}?"
                )
            else:
                reply = (
                    f"🔒 *Security Deposit Policy in {COUNTRY_NAME}:*\n\n"
                    f"• Standard deposit is typically 1 month of rent, held in compliance with local tenancy laws.\n"
                    f"• Returned fully at lease completion subject to room condition.\n"
                    f"• In {self.brand}, we eliminate hidden broker markups.\n\n"
                    f"Would you like to explore listings in {session.city or LOCAL_CITIES[0]}?"
                )
            return {"reply_text": reply, "action": "faq_deposit"}

        if any(w in msg for w in ["pet", "pets", "mascota", "mascotas", "perro", "gato", "dog", "cat", "반려동물", "ペット"]):
            if not is_es:
                reply = "🐾 Pet allowances vary per property. Tell us your target city and we will filter pet-friendly homes for you!"
            else:
                reply = "🐾 La admisión de mascotas depende de cada propietario. Indícanos qué departamento te interesa para verificar si admite animales."
            return {"reply_text": reply, "action": "faq_pets"}

        return None

    def _handle_human_request(self, session: UserSession, lang: str, channel: str) -> Dict[str, Any]:
        if channel == "whatsapp":
            if lang != "es":
                reply = (
                    f"👩‍💼 *Live Advisor Assistance:*\n\n"
                    f"You are connected directly to our official line for {self.brand}. "
                    f"A team coordinator will review your chat history and reply right here for specialized support."
                )
            else:
                reply = (
                    f"👩‍💼 *Atención Directa:*\n\n"
                    f"Ya estás en el canal oficial de {self.brand}. Un asesor inmobiliario revisará tu conversación y te responderá por este mismo chat en breve."
                )
        else:
            reply = f"Contact our live team on WhatsApp at {self.whatsapp_number}."
        return {"reply_text": reply, "action": "human_requested"}

    def _handle_fallback(self, session: UserSession, raw_msg: str, lang: str, channel: str) -> Dict[str, Any]:
        city_hint = f" in *{session.city}*" if session.city else ""
        if channel == "whatsapp":
            if lang == "es":
                reply = (
                    f"Recibí tu consulta: *'{raw_msg}'*\n\n"
                    f"Para orientarte rápidamente, puedes:\n"
                    f"• Indicar una ciudad: *{', '.join(LOCAL_CITIES[:4])}*...\n"
                    f"• Pedir *'más opciones'*{city_hint}\n"
                    f"• Responder con un número (*1*, *2* o *3*) para ver fotos y agendar visita\n"
                    f"• O preguntar por el cálculo de cuota o fianza."
                )
            else:
                reply = (
                    f"Received your message: *'{raw_msg}'*\n\n"
                    f"To assist you immediately, you can:\n"
                    f"• Specify a city: *{', '.join(LOCAL_CITIES[:4])}*...\n"
                    f"• Say *'more options'*{city_hint}\n"
                    f"• Reply with a number (*1*, *2*, or *3*) to see specs and book a tour\n"
                    f"• Or ask about rent splitting, deposits, or amenities."
                )
        else:
            reply = f"Welcome to {self.brand}. Tell me which city you want to live in to explore verified shared flats."

        return {"reply_text": reply, "action": "fallback"}

    def _query_properties(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            return get_properties(city=city)
        except Exception:
            try:
                return get_properties()
            except Exception:
                try:
                    from app.models.database import INITIAL_PROPERTIES
                    return INITIAL_PROPERTIES
                except Exception:
                    return []

    def _extract_selection_index(self, msg: str) -> Optional[int]:
        if msg in ["1", "1️⃣", "first", "primero", "primera", "el 1", "la 1", "option 1", "opcion 1", "1番", "첫 번째"]:
            return 0
        if msg in ["2", "2️⃣", "second", "segundo", "segunda", "el 2", "la 2", "option 2", "opcion 2", "2番", "두 번째"]:
            return 1
        if msg in ["3", "3️⃣", "third", "tercero", "tercera", "el 3", "la 3", "option 3", "opcion 3", "3番", "세 번째"]:
            return 2
        m1 = re.search(r"\b(the|option|opcion|opción)?\s*1\b", msg)
        if m1 and "10" not in msg and "11" not in msg and "12" not in msg:
            return 0
        m2 = re.search(r"\b(the|option|opcion|opción)?\s*2\b", msg)
        if m2 and "20" not in msg:
            return 1
        m3 = re.search(r"\b(the|option|opcion|opción)?\s*3\b", msg)
        if m3 and "30" not in msg:
            return 2
        return None

    def _is_visit_request(self, msg: str) -> bool:
        time_words = [
            "tomorrow", "today", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "mañana", "hoy", "lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sabado", "sábado",
            "afternoon", "morning", "pm", "am", "clock", "visita", "visit", "viewing", "tour", "appointment",
            "見学", "방문", "นัดดู", "temu janji", "زيارة"
        ]
        return any(w in msg for w in time_words) and any(w in msg for w in ["visit", "viewing", "tour", "visita", "cita", "at", "a las", "por la", "pm", "am", "見学", "방문"])

    def build_whatsapp_link(self, message: str) -> str:
        encoded = urllib.parse.quote(message)
        return f"https://wa.me/{self.clean_whatsapp}?text={encoded}"


voice_agent = LocalizedVoiceAgent()
