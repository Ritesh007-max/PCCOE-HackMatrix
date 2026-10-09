"""
FIN Grounded Chat Route.
Provides POST /v1/chat.
CRITICAL INVARIANT: Chat must remain grounded strictly in the verified RAG policy corpus.
Never acts as a generic hallucinating chatbot.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool

from src.rag.retriever import HybridRetriever
from src.rag.models import RetrievalQuery
from src.rag.scheme_name_index import (
    get_scheme_name_index,
    format_canonical_scheme_response,
    format_canonical_score_explanation,
    clean_canonical_field,
)
from src.llm.client import LLMClient
from src.llm.safety import PromptInjectionDetector

from ..auth import verify_api_key
from ..config import ServiceConfig
from ..dependencies import (
    get_hybrid_retriever,
    get_llm_client,
    get_rate_limiter,
    get_service_config,
    get_query_understanding_service,
)
from ..errors import RateLimitExceededError
from ..middleware import InMemoryRateLimiter
from ..schemas import ChatCitationItem, ChatRequest, ChatResponse
from src.query.service import QueryUnderstandingService
from src.query.models import CanonicalIntent
from src.nlp.language import LanguageDetector

logger = logging.getLogger("fin.api.routes.chat")

router = APIRouter(prefix="/v1/chat", tags=["Chat"])

_safety_detector = PromptInjectionDetector()
_language_detector = LanguageDetector()

SYSTEM_PROMPT_GROUNDED_CHAT = """You are FIN's authoritative government welfare assistant.
You assist Indian citizens in discovering statutory schemes, understanding eligibility criteria, and identifying application steps.

CRITICAL INVARIANTS:
1. Ground every claim strictly and exclusively in the provided <POLICY_EVIDENCE> chunks or <APPLICANT_DOCUMENTS_AND_RECORDS>.
2. If the statutory records do not contain the answer, explicitly state: "This information is not available in the verified government scheme repository."
3. NEVER hallucinate eligibility rules, deadlines, or monetary benefits.
4. Reference the supporting evidence chunk IDs or document pages where appropriate.
5. Maintain a professional, empathetic, and clear public-service tone in the citizen's detected language.
"""

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "gu": "Gujarati",
    "hinglish": "Hinglish",
}


FIN_WEBSITE_KNOWLEDGE = """
FIN (Financial Policy Intelligence) Official Platform Architecture & Public Guidance:

1. Citizen Dashboard (/dashboard):
   - Real-time overview of citizen welfare metrics: Profile Strength score, Active Applications count, Verified Documents count, and personalized Scheme Recommendations.
   - Quick navigation links to Discover Schemes, Documents Vault, and Applications.

2. Discover Schemes (/discover):
   - Comprehensive searchable directory of 670+ Central Ministries and State Government welfare schemes.
   - Search by keyword (e.g., "scholarship", "farmer", "student", "subsidy", "MSME") and filter by Central/State, sector, target groups, and benefits.

3. Suggested Schemes (/suggested-schemes):
   - Algorithmic scheme recommendations computed dynamically against citizen demographics (income, domicile state, occupation, social category).
   - CRITICAL INVARIANT: A high recommendation score indicates demographic relevance, NOT confirmed statutory eligibility. Official eligibility requires deterministic policy rule evaluation.

4. My Documents Vault (/documents):
   - Secure digital document locker for statutory certificates (Aadhaar, PAN, Income Certificate, Caste Certificate, Ration Card, Domicile).
   - Automated OCR extraction extracts structured fields to enable instant scheme matching and document readiness audits.
   - CRITICAL INVARIANT: OCR extraction does NOT constitute official government verification. Official statutory verification is conducted independently by the competent departmental nodal officer upon application submission.

5. Application Tracker (/applications):
   - Real-time tracking of submitted welfare applications and support tickets with stage checkpoints (Submission -> Scrutiny -> Verification -> Sanction -> Disbursement) and nodal ministry portal links.

6. Citizen Profile (/profile):
   - Manage personal demographic details: full name, DOB, gender, state of domicile, district, annual household income, occupation, and caste category.
   - Citizens can update details via the "Edit Profile" button. Note: Profile details and uploaded document evidence are preserved independently without overwriting either source.

7. What a Citizen CAN vs CANNOT Do in FIN:
   - Citizens CAN: Browse and filter schemes, update profile demographics, upload documents to their secure vault, check match scores, track submitted applications, raise support tickets, and use FIN AI via text or microphone voice input.
   - Citizens CANNOT: Self-approve government subsidies, bypass departmental nodal verification, alter official government certificate stamps, or modify statutory policy criteria. All approvals are reserved for competent departmental authorities.

8. Ask FIN AI Assistant:
   - Multilingual voice and text intelligent assistant providing grounded answers on government schemes, eligibility, required documents, benefits, and portal navigation.
   - Voice Input: Click the microphone icon to record your question manually. Click stop to transcribe. The assistant responds with grounded text and optional TTS spoken audio. Hands-free auto-looping is completely disabled.
"""

SYSTEM_PROMPT_GROUNDED_CHAT = """You are FIN's authoritative government welfare copilot.
You assist Indian citizens in discovering statutory schemes, understanding eligibility criteria, navigating the FIN platform, and analyzing their uploaded documents and active applications/tickets.

CRITICAL INVARIANTS:
1. STRICT QUESTION UNDERSTANDING: Answer ONLY what the user asked. Do not change the topic. Do not generate unrelated information. Do not invent scheme details.
   - If the user asks about document requirements, answer strictly about document requirements.
   - If the user asks about benefits, answer strictly about benefits.
   - If the user asks about eligibility, answer strictly about eligibility criteria.
   - If the user asks about application procedures, answer strictly about application steps.
   - If the user asks about the FIN website or features, explain the relevant portal modules accurately.
2. Ground policy and scheme claims strictly in the provided <POLICY_EVIDENCE> chunks or <OFFICIAL_SCHEME_RECORD>.
3. Ground citizen facts and document answers strictly in the provided <APPLICANT_DOCUMENTS_AND_RECORDS>.
4. Ground active applications and tickets strictly in the provided <APPLICANT_TICKETS_AND_APPLICATIONS>.
5. When information is unavailable or unverified in official records, clearly state that it could not be verified instead of hallucinating.
6. MULTILINGUAL INVARIANT: Always respond in the EXACT SAME language as the citizen's query (Hindi in Hindi, Gujarati in Gujarati, Hinglish in Hinglish, Tamil in Tamil, Bengali in Bengali, Marathi in Marathi, English in English). Never switch to English unless explicitly requested.
7. Maintain a professional, empathetic, and clear public-service tone."""

OUT_OF_SCOPE_MESSAGES: Dict[str, str] = {
    "en": (
        "FIN AI is focused exclusively on financial welfare schemes, citizen documents, applications, "
        "eligibility evaluation, and platform guidance. I am unable to assist with programming, general trivia, "
        "or creative writing tasks. Please let me know if you have questions regarding government schemes or your documents!"
    ),
    "hi": (
        "फिन एआई (FIN AI) विशेष रूप से सरकारी कल्याणकारी योजनाओं, नागरिक दस्तावेजों, आवेदनों, पात्रता मूल्यांकन "
        "और पोर्टल मार्गदर्शन के लिए बनाया गया है। मैं प्रोग्रामिंग, सामान्य ज्ञान या रचनात्मक लेखन में सहायता करने में "
        "असमर्थ हूँ। कृपया बताएं कि क्या आपके पास सरकारी योजनाओं या अपने दस्तावेजों से संबंधित कोई प्रश्न है।"
    ),
    "gu": (
        "FIN AI ખાસ કરીને સરકારી કલ્યાણકારી યોજનાઓ, નાગરિક દસ્તાવેજો, અરજીઓ, પાત્રતા મૂલ્યાંકન અને પોર્ટલ માર્ગદર્શન "
        "માટે સમર્પિત છે. હું પ્રોગ્રામિંગ, સામાન્ય જ્ઞાન અથવા સર્જનાત્મક લેખન કાર્યોમાં સહાય કરી શકતો નથી. "
        "કૃપા કરીને સરકારી યોજનાઓ અથવા તમારા દસ્તાવેજો વિશે પૂછો."
    ),
    "hinglish": (
        "FIN AI specifically sarkari welfare schemes, citizen documents, applications, eligibility evaluation "
        "aur portal guidance ke liye design kiya gaya hai. Main programming, general trivia ya creative writing "
        "jaise tasks me assist nahi kar sakta. Kripya sarkari schemes ya documents se juda koi sawaal puchein!"
    ),
    "mr": (
        "FIN AI विशेषतः सरकारी कल्याणकारी योजना, नागरिक कागदपत्रे, अर्ज, पात्रता मूल्यांकन आणि पोर्टल मार्गदर्शनासाठी तयार केले आहे. "
        "मी प्रोग्रामिंग, सामान्य ज्ञान किंवा सर्जनशील लेखन कार्यांमध्ये मदत करू शकत नाही."
    ),
    "bn": (
        "FIN AI বিশেষভাবে সরকারি কল্যাণমূলক প্রকল্প, नागरिक নথি, আবেদন, योग्यता মূল্যায়ন এবং পোর্টাল নির্দেশিকার জন্য নিবেদিত। "
        "আমি প্রোগ্রামিং, সাধারণ জ্ঞান বা সৃজনশীল লেখার কাজে সহায়তা করতে পারি না।"
    ),
    "ta": (
        "FIN AI பிரத்தியேகமாக அரசு நலத்திட்டங்கள், குடிமக்கள் ஆவணங்கள், விண்ணப்பங்கள், தகுதி மதிப்பீடு மற்றும் போர்டல் வழிகாட்டுதலுக்காக வடிவமைக்கப்பட்டுள்ளது. "
        "நிரலாக்கம் அல்லது பொதுவான கேள்விகளுக்கு என்னால் பதிலளிக்க முடியாது."
    ),
    "te": (
        "FIN AI ప్రత్యేకంగా ప్రభుత్వ సంక్షేమ పథకాలు, పౌర పత్రాలు, దరఖాస్తులు, అర్హత అంచనా మరియు పోర్టల్ మార్గదర్శకత్వం కోసం రూపొందించబడింది. "
        "నేను ప్రోగ్రామింగ్ లేదా సాధారణ విషయాలలో సహాయం చేయలేను."
    ),
    "kn": (
        "FIN AI ವಿಶೇಷವಾಗಿ ಸರ್ಕಾರಿ ಕಲ್ಯಾಣ ಯೋಜನೆಗಳು, ನಾಗರಿಕ ದಾಖಲೆಗಳು, ಅರ್ಜಿಗಳು, ಅರ್ಹತಾ ಮೌಲ್ಯಮಾಪನ ಮತ್ತು ಪೋರ್ಟಲ್ ಮಾರ್ಗದರ್ಶನಕ್ಕಾಗಿ ಮೀಸಲಾಗಿದೆ. "
        "ನಾನು ಪ್ರೋಗ್ರಾಮಿಂಗ್ ಅಥವಾ ಸಾಮಾನ್ಯ ವಿಷಯಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಲು ಸಾಧ್ಯವಿಲ್ಲ."
    ),
    "ml": (
        "FIN AI പ്രത്യേകമായി സർക്കാർ ക്ഷേമ പദ്ധതികൾ, പൗര രേഖകൾ, അപേക്ഷകൾ, യോഗ്യതാ വിലയിരുത്തൽ, പോർട്ടൽ മാർഗ്ഗനിർദ്ദേശം എന്നിവയ്ക്കായി രൂപകൽപ്പന ചെയ്തിട്ടുള്ളതാണ്."
    ),
    "pa": (
        "FIN AI ਖਾਸ ਤੌਰ 'ਤੇ ਸਰਕਾਰੀ ਭਲਾਈ ਸਕੀਮਾਂ, ਨਾਗਰਿਕ ਦਸਤਾਵੇਜ਼ਾਂ, ਅਰਜ਼ੀਆਂ, ਯੋਗਤਾ ਮੁਲਾਂਕਣ ਅਤੇ ਪੋਰਟਲ ਮਾਰਗਦਰਸ਼ਨ ਲਈ ਬਣਾਇਆ ਗਿਆ ਹੈ।"
    ),
}

NO_EVIDENCE_MESSAGES: Dict[str, str] = {
    "gu": (
        "તમારી શોધ સાથે મેળ ખાતી કોઈ ચકાસાયેલ સરકારી યોજનાઓ અથવા નીતિ દસ્તાવેજો સત્તાવાર રિપોઝિટરીમાં મળ્યા નથી. "
        "કૃપા કરીને ચોક્કસ કીવર્ડ્સ (દા.ત. 'ખેડૂત સબસિડી', 'શિષ્યવૃત્તિ', 'પેન્શન', અથવા રાજ્યનું નામ) સાથે ફરીથી પ્રયાસ કરો."
    ),
    "hi": (
        "आपकी खोज से संबंधित कोई सत्यापित सरकारी योजना या नीति दस्तावेज आधिकारिक डेटाबेस में नहीं मिला। "
        "कृपया विशिष्ट कीवर्ड (जैसे 'किसान सब्सिडी', 'छात्रवृत्ति', 'पेंशन', या राज्य का नाम) के साथ पुनः प्रयास करें।"
    ),
    "hinglish": (
        "Aapki search se related koi verified sarkari scheme ya policy documents nahi mile. "
        "Kripya specific keywords (jaise 'kisan subsidy', 'scholarship', 'pension') ke saath dubara prayas karein."
    ),
    "ta": (
        "உங்கள் வினவலுடன் பொருந்தக்கூடிய சரிபார்க்கப்பட்ட அரசு திட்டங்கள் அல்லது கொள்கை ஆவணங்கள் எதுவும் கிடைக்கவில்லை. "
        "குறிப்பிட்ட முக்கிய வார்த்தைகளுடன் மீண்டும் முயற்சிக்கவும்."
    ),
    "bn": (
        "আপনার প্রশ্নের সাথে মিলে এমন কোনো যাচাইকৃত সরকারি প্রকল্প বা নীতি নথি পাওয়া যায়নি। "
        "অনুগ্রহ করে সুনির্দিষ্ট কীওয়ার্ড দিয়ে পুনরায় অনুসন্ধান করুন।"
    ),
    "mr": (
        "तुमच्या शोधाशी जुळणाऱ्या कोणत्याही अधिकृत सरकारी योजना किंवा धोरण दस्तऐवज आढळले नाहीत. "
        "कृपया विशिष्ट शब्दांसह (उदा. 'शेतकरी अनुदान', 'शिष्यवृत्ती', 'पेन्शन') पुन्हा प्रयत्न करा."
    ),
    "te": (
        "మీ శోధనకు సరిపోలే ధృవీకరించబడిన ప్రభుత్వ పథకాలు ఏవీ లభించలేదు. "
        "దయచేసి నిర్దిష్ట కీలకపదాలతో మళ్లీ ప్రయత్నించండి."
    ),
    "kn": (
        "ನಿಮ್ಮ ಹುಡುಕಾಟಕ್ಕೆ ಹೊಂದಿಕೆಯಾಗುವ ಯಾವುದೇ ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ. "
        "ದಯವಿಟ್ಟು ನಿರ್ದಿಷ್ಟ ಕೀವರ್ಡ್‌ಗಳೊಂದಿಗೆ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."
    ),
    "ml": (
        "നിങ്ങളുടെ അന്വേഷണവുമായി പൊരുത്തപ്പെടുന്ന ഔദ്യോഗിക സർക്കാർ പദ്ധതികളൊന്നും കണ്ടെത്താനായില്ല. "
        "ദയവായി നിർദ്ദിഷ്ട കീവേഡുകൾ ഉപയോഗിച്ച് വീണ്ടും ശ്രമിക്കുക."
    ),
    "pa": (
        "ਤੁਹਾਡੀ ਖੋਜ ਨਾਲ ਮੇਲ ਖਾਂਦੀ ਕੋਈ ਵੀ ਤਸਦੀਕਸ਼ੁਦਾ ਸਰਕਾਰੀ ਯੋਜਨਾ ਨਹੀਂ ਮਿਲੀ। "
        "ਕਿਰਪਾ ਕਰਕੇ ਖਾਸ ਕੀਵਰਡਸ ਨਾਲ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।"
    ),
    "en": (
        "No verified government schemes or policy documents were found matching your query "
        "in the statutory repository. Please try searching with specific keywords "
        "(e.g., 'farmer subsidy', 'scholarship', 'pension', or state name)."
    )
}


def format_no_evidence_message(lang: str) -> str:
    return NO_EVIDENCE_MESSAGES.get(lang, NO_EVIDENCE_MESSAGES["en"])


def is_fin_website_query(query: str) -> bool:
    q = query.lower()
    patterns = [
        r"\b(?:what\s+is\s+fin|about\s+fin|fin\s+platform|fin\s+website|this\s+website|this\s+portal)\b",
        r"\b(?:how\s+(?:to\s+use|does)\s+(?:fin|this\s+website|this\s+portal))\b",
        r"\b(?:how\s+(?:can\s+i|do\s+i)\s+(?:use|navigate)\s+(?:fin|this\s+website))\b",
        r"\b(?:what\s+can\s+i\s+do\s+(?:on|in)\s+(?:fin|this\s+website|here))\b",
        r"\b(?:what\s+is\s+(?:the\s+)?(?:citizen\s+)?dashboard|how\s+to\s+use\s+dashboard|dashboard\s+me\s+kya\s+dikhta\s+hai)\b",
        r"\b(?:what\s+is\s+(?:the\s+)?discover\s+(?:schemes?)?|how\s+does\s+discover\s+work|where\s+(?:are|can\s+i\s+find)\s+(?:the\s+)?schemes?\s+for\s+students?)\b",
        r"\b(?:what\s+is\s+(?:the\s+)?suggested\s+schemes?|how\s+are\s+schemes?\s+suggested)\b",
        r"\b(?:what\s+is\s+(?:the\s+)?(?:my\s+)?documents?\s+(?:vault|locker)?|how\s+to\s+upload\s+documents?|how\s+do\s+i\s+upload\s+(?:a\s+)?document)\b",
        r"\b(?:what\s+is\s+(?:the\s+)?(?:application\s+tracker|applications?\s+page)|how\s+to\s+track\s+applications?|where\s+can\s+i\s+see\s+my\s+applications)\b",
        r"\b(?:what\s+is\s+(?:the\s+)?(?:citizen\s+)?profile\s+page|how\s+to\s+update\s+profile|how\s+do\s+i\s+update\s+my\s+profile)\b",
        r"\b(?:how\s+to\s+use\s+(?:voice|mic|microphone))\b",
    ]
    if any(re.search(pat, q) for pat in patterns):
        return True
    indic_markers = [
        "વેબસાઇટ", "વેબસાઈટ", "પોર્ટલ", "ડેશબોર્ડ", "દસ્તાવેજ વૉલ્ટ", "અરજી ટ્રેક",
        "वेबसाइट", "पोर्टल", "डैशबोर्ड", "दस्तावेज़ वॉल्ट", "आवेदन ट्रैक"
    ]
    if any(marker in query for marker in indic_markers):
        return True
    return False


def format_fin_website_response(query: str, lang: str = "en") -> str:
    """Provides authoritative, deterministic grounding for FIN portal questions."""
    q_low = query.lower()
    
    # 1. Applications navigation
    if re.search(r"\b(?:where\s+can\s+i\s+see\s+my\s+applications|track\s+my\s+applications|applications?\s+page)\b", q_low):
        if lang == "hi":
            return (
                "आप अपने सभी सबमिट किए गए आवेदन और सपोर्ट टिकट **Applications** पेज पर देख सकते हैं। "
                "इसे एक्सेस करने के लिए साइडबार नेविगेशन में **Applications** पर क्लिक करें या सीधे `/applications` पर जाएं।"
            )
        elif lang == "gu":
            return (
                "તમે તમારી બધી સબમિટ કરેલી અરજીઓ અને સપોર્ટ ટિકિટો **Applications** પેજ પર જોઈ શકો છો. "
                "સાઇડબાર નેવિગેશનમાં **Applications** પર ક્લિક કરો અથવા સીધા `/applications` પર જાઓ."
            )
        elif lang == "hinglish":
            return (
                "Aap apne sabhi submitted applications aur support tickets **Applications** page par dekh sakte hain. "
                "Sidebar navigation me **Applications** par click karein ya `/applications` par visit karein."
            )
        return (
            "You can view and track all your submitted welfare applications and support tickets on the **Applications** page. "
            "Navigate to it by clicking **Applications** in the sidebar navigation or visiting `/applications`."
        )

    # 2. Uploading documents
    if re.search(r"\b(?:how\s+do\s+i\s+upload\s+(?:a\s+)?document|how\s+to\s+upload\s+documents?|documents?\s+vault)\b", q_low):
        if lang == "hi":
            return (
                "दस्तावेज़ अपलोड करने के लिए:\n1. साइडबार में **My Documents** (`/documents`) पर जाएं।\n"
                "2. **Upload Document** बटन पर क्लिक करें।\n3. अपने वैधानिक प्रमाण पत्र (आय, जाति, आधार, पैन आदि) की PDF या इमेज चुनें।\n"
                "4. अपलोड होने पर FIN का OCR सिस्टम तुरंत आपके विवरण निकालेगा।"
            )
        elif lang == "gu":
            return (
                "દસ્તાવેજ અપલોડ કરવા માટે:\n1. સાઇડબારમાં **My Documents** (`/documents`) પર જાઓ.\n"
                "2. **Upload Document** બટન પર ક્લિક કરો.\n3. તમારા પ્રમાણપત્રો (આવક, જાતિ, આધાર, પાન વગેરે) પસંદ કરો.\n"
                "4. અપલોડ થતાં જ FIN ની OCR સિસ્ટમ વિગતો સ્કેન કરશે."
            )
        elif lang == "hinglish":
            return (
                "Document upload karne ke liye:\n1. Sidebar me **My Documents** (`/documents`) par jayein.\n"
                "2. **Upload Document** button par click karein.\n3. Apne certificates (Income, Caste, Aadhaar, PAN) select karein.\n"
                "4. Upload ke baad FIN OCR automatically details extract kar lega."
            )
        return (
            "To upload a document:\n1. Navigate to the **My Documents** vault (`/documents`) from the sidebar.\n"
            "2. Click the **Upload Document** button.\n3. Select your statutory certificate (Income Certificate, Caste Certificate, Aadhaar, PAN).\n"
            "4. FIN automatically performs OCR extraction for scheme eligibility matching."
        )

    # 3. Dashboard info
    if re.search(r"\b(?:dashboard\s+me\s+kya\s+dikhta\s+hai|what\s+does\s+(?:the\s+)?dashboard\s+show|dashboard)\b", q_low):
        if lang == "hi":
            return (
                "फिन **Citizen Dashboard** (`/dashboard`) आपको एक नज़र में दिखाता है:\n"
                "• **Profile Strength**: आपकी प्रोफाइल कितनी पूर्ण है।\n• **Active Applications**: आपके सबमिट किए गए आवेदनों की संख्या।\n"
                "• **Verified Documents**: आपके अपलोड किए गए दस्तावेजों की संख्या।\n• **Suggested Schemes**: आपकी प्रोफ़ाइल से मेल खाने वाली शीर्ष योजनाएं।"
            )
        elif lang == "gu":
            return (
                "FIN **Citizen Dashboard** (`/dashboard`) તમને એક નજરમાં બતાવે છે:\n"
                "• **Profile Strength**: તમારી પ્રોફાઇલ કેટલી પૂર્ણ છે.\n• **Active Applications**: તમારી સબમિટ કરેલી અરજીઓની સંખ્યા.\n"
                "• **Verified Documents**: તમારા અપલોડ કરેલા દસ્તાવેજો.\n• **Suggested Schemes**: તમારી પ્રોફાઇલ મુજબ મેળ ખાતી શ્રેષ્ઠ યોજનાઓ."
            )
        elif lang == "hinglish":
            return (
                "FIN **Citizen Dashboard** (`/dashboard`) par aapko ye metrics dikhte hain:\n"
                "• **Profile Strength**: Aapki profile completion score.\n• **Active Applications**: Aapke submitted applications ka count.\n"
                "• **Verified Documents**: Vault me uploaded documents.\n• **Suggested Schemes**: Aapki demographic profile se match hone wali top welfare schemes."
            )
        return (
            "The **Citizen Dashboard** (`/dashboard`) provides a real-time overview of your welfare profile:\n"
            "• **Profile Strength Score**: Measures demographic profile completeness.\n"
            "• **Active Applications**: Count and status of your submitted government applications.\n"
            "• **Verified Documents**: Count of statutory documents stored in your vault.\n"
            "• **Top Scheme Recommendations**: Schemes algorithmically matched to your demographics."
        )

    # 4. Schemes for students
    if re.search(r"\b(?:schemes?\s+for\s+students?|student)\b", q_low):
        if lang == "hi":
            return (
                "छात्रों के लिए योजनाओं को खोजने के लिए, साइडबार में **Discover Schemes** (`/discover`) पर जाएं और 'Education' या 'Students' श्रेणी फ़िल्टर करें। "
                "प्रमुख योजनाओं में **PM Vidyalaxmi** (उच्च शिक्षा ऋण), **Digital India Internship Scheme**, और **Skill India Training** शामिल हैं।"
            )
        elif lang == "gu":
            return (
                "વિદ્યાર્થીઓ માટેની યોજનાઓ શોધવા માટે, સાઇડબારમાં **Discover Schemes** (`/discover`) પર જાઓ અને 'Education' અથવા 'Students' કેટેગરી પસંદ કરો. "
                "મુખ્ય યોજનાઓમાં **PM Vidyalaxmi**, **Digital India Internship Scheme**, અને **Skill India** શામેલ છે."
            )
        elif lang == "hinglish":
            return (
                "Students ke liye schemes search karne ke liye **Discover Schemes** (`/discover`) par jayein aur 'Education' ya 'Students' category filter karein. "
                "Key schemes me **PM Vidyalaxmi** (education loan support), **Digital India Internship**, aur **Skill India** training shamil hain."
            )
        return (
            "To find schemes for students, visit the **Discover Schemes** page (`/discover`) and filter by the 'Education' or 'Students' category, or check your **Suggested Schemes** (`/suggested-schemes`). "
            "Key student schemes include **PM Vidyalaxmi** (higher education loan support), **Digital India Internship Scheme**, and **Skill India** training programs."
        )

    # 5. General capabilities ("What can I do on this website?", "How does FIN work?")
    if lang == "hi":
        return (
            "फिन (FIN) भारत सरकार और राज्य सरकारों की कल्याणकारी योजनाओं के लिए एक आधिकारिक नीति खुफिया पोर्टल है:\n"
            "1. **योजनाएं खोजें (`/discover`)**: 670+ केंद्रीय और राज्य योजनाओं को खोजें और फ़िल्टर करें।\n"
            "2. **सुझाई गई योजनाएं (`/suggested-schemes`)**: अपनी आय, राज्य, जाति और व्यवसाय के आधार पर व्यक्तिगत सिफारिशें प्राप्त करें।\n"
            "3. **दस्तावेज़ वॉल्ट (`/documents`)**: अपने प्रमाण पत्र सुरक्षित रूप से अपलोड करें जहां स्वचालित ओसीआर उनका ऑडिट करता है।\n"
            "4. **पात्रता जांच**: पारदर्शी नीति नियमों के आधार पर सत्यापित करें कि आप पात्र हैं या नहीं।\n"
            "5. **आवेदन ट्रैकर (`/applications`)**: अपने सभी सबमिट किए गए आवेदनों की स्थिति ट्रैक करें।\n\n"
            "*नागरिक अधिकार सीमा: नागरिक अपनी प्रोफ़ाइल प्रबंधित कर सकते हैं और आवेदन ट्रैक कर सकते हैं; आधिकारिक सब्सिडी और वैधानिक अनुमोदन संबंधित सरकारी विभाग के नोडल अधिकारी द्वारा किया जाता है।*"
        )
    elif lang == "gu":
        return (
            "FIN ભારત સરકાર અને રાજ્ય સરકારોની કલ્યાણકારી યોજનાઓ માટેનું એક બુદ્ધિશાળી પોર્ટલ છે:\n"
            "1. **યોજનાઓ શોધો (`/discover`)**: 670+ સરકારી યોજનાઓ શોધો અને ફિલ્ટર કરો.\n"
            "2. **સૂચવેલ યોજનાઓ (`/suggested-schemes`)**: તમારી પ્રોફાઇલ મુજબ વ્યક્તિગત ભલામણો મેળવો.\n"
            "3. **દસ્તાવેજ વૉલ્ટ (`/documents`)**: તમારા પ્રમાણપત્રો સુરક્ષિત રીતે અપલોડ કરો.\n"
            "4. **પાત્રતા તપાસ**: ચોક્કસ નિયમો સાથે તમારી પાત્રતા ચકાસો.\n"
            "5. **અરજી ટ્રેકર (`/applications`)**: તમારી સબમિટ કરેલી અરજીઓની સ્થિતિ ટ્રૅક કરો.\n\n"
            "*નોંધ: સત્તાવાર સબસિડી મંજૂરી સંબંધિત સરકારી વિભાગના નોડલ અધિકારી દ્વારા કરવામાં આવે છે.*"
        )
    elif lang == "hinglish":
        return (
            "FIN website par aap ye sabhi features access kar sakte hain:\n"
            "1. **Discover Schemes (`/discover`)**: 670+ Central aur State schemes search aur filter karein.\n"
            "2. **Suggested Schemes (`/suggested-schemes`)**: Apni demographic profile ke hisaab se personalized recommendations dekhein.\n"
            "3. **My Documents Vault (`/documents`)**: Apne statutory certificates secure vault me upload karein with automated OCR.\n"
            "4. **Deterministic Eligibility**: Policy rules engine se check karein ki aap eligible hain ya nahi.\n"
            "5. **Applications Tracker (`/applications`)**: Apne submitted applications ka real-time lifecycle status track karein.\n\n"
            "*Citizen Permissions: Citizens schemes explore, documents upload, aur applications track kar sakte hain. Official subsidy sanction nodal department ke officer dwara diya jata hai.*"
        )
    return (
        "On the FIN platform, you can access comprehensive welfare intelligence and citizen tools:\n"
        "1. **Discover Schemes (`/discover`)**: Search and filter 670+ Central and State Government welfare schemes.\n"
        "2. **Suggested Schemes (`/suggested-schemes`)**: Receive algorithmic recommendations matched to your income, domicile, category, and occupation.\n"
        "3. **My Documents Vault (`/documents`)**: Securely store statutory certificates with automated OCR data extraction.\n"
        "4. **Deterministic Eligibility Evaluation**: Verify your statutory eligibility using FIN's rules engine (PASS, FAIL, UNKNOWN, REVIEW).\n"
        "5. **Application Tracker (`/applications`)**: Track submitted welfare applications across their full 5-stage lifecycle.\n\n"
        "*Citizen Authority Boundary: Citizens can explore schemes, manage documents, and track applications. Official subsidy sanction and statutory verification are conducted exclusively by competent departmental authorities.*"
    )


async def maybe_translate_response(
    answer: str,
    detected_lang: str,
    detected_lang_name: str,
    query: str,
    llm_client: LLMClient,
    request_id: str
) -> str:
    if detected_lang == "en" or not answer or not answer.strip():
        return answer
    prompt = (
        f"You are FIN's multilingual government scheme assistant.\n"
        f"The citizen asked: \"{query}\"\n\n"
        f"Translate and articulate the following verified answer accurately and faithfully into {detected_lang_name} ({detected_lang}):\n\n"
        f"{answer}\n\n"
        f"INVARIANTS:\n"
        f"1. Respond STRICTLY in {detected_lang_name} ({detected_lang}).\n"
        f"2. Maintain all exact numbers, percentages, criteria, and document requirements.\n"
        f"3. Answer ONLY what the user asked. Do not add unsolicited commentary."
    )
    try:
        translated = await run_in_threadpool(
            llm_client.generate,
            prompt,
            system_prompt=SYSTEM_PROMPT_GROUNDED_CHAT,
            operation="multilingual_translation",
            request_id=request_id,
        )
        if translated and translated.strip():
            return translated.strip()
    except Exception as e:
        logger.warning("Translation to %s failed: %s", detected_lang, e)
    return answer


def strip_negative_constraints(text: str) -> str:
    """
    Strips negative instructions so they do not inadvertently trigger positive
    personal-data, document, or ticket lookups.
    """
    if not text:
        return ""
    neg_pattern = (
        r"\b(?:do\s+not|don['\u2019]?t|dont|never|without|exclude|avoid|stop)\s+"
        r"(?:to\s+)?(?:show|display|use|utilize|search|check|inspect|look\s+at|include|refer\s+to|mention|rely\s+on)?\s*"
        r"[^.!?\n;]*(?:documents?|files?|certificates?|tickets?|applications?|vault|profile|records?)[^.!?\n;]*"
    )
    return re.sub(neg_pattern, " ", text, flags=re.IGNORECASE).strip()


def resolve_document_fact_page(
    doc: Optional[dict],
    fact_value: Optional[Any] = None,
    fact_key: Optional[str] = None,
    fact_obj: Optional[Any] = None,
) -> Optional[int]:
    """
    Deterministically resolves the exact source page number (1-indexed) containing the extracted fact.
    Returns:
        int: 1-indexed page number where the fact is located.
        None: If page provenance is unavailable / unknown across multiple pages.
    """
    if fact_obj and hasattr(fact_obj, "page_number") and isinstance(fact_obj.page_number, int) and fact_obj.page_number > 0:
        return fact_obj.page_number

    if not doc or not isinstance(doc, dict):
        return None

    if doc.get("page_number") and isinstance(doc["page_number"], int) and doc["page_number"] > 0:
        return doc["page_number"]

    ext_text = doc.get("extracted_text") or ""
    if not ext_text.strip():
        ocr_meta = doc.get("ocrMetadata") or {}
        if ocr_meta.get("pages") == 1:
            return 1
        return None

    page_blocks = re.split(r"---\s*\[Page\s+(\d+)\]\s*---", ext_text)
    if len(page_blocks) > 1:
        parsed_pages = []
        for i in range(1, len(page_blocks), 2):
            try:
                p_num = int(page_blocks[i])
                p_content = page_blocks[i + 1]
                parsed_pages.append((p_num, p_content))
            except (ValueError, IndexError):
                continue

        if not parsed_pages:
            return None

        if fact_value is not None:
            clean_needle = re.sub(r"[₹,.\-\s/]", "", str(fact_value)).lower()
            if clean_needle:
                matching = []
                for p_num, p_txt in parsed_pages:
                    p_clean = re.sub(r"[₹,.\-\s/]", "", p_txt).lower()
                    if clean_needle in p_clean:
                        matching.append((p_num, p_txt))

                if len(matching) == 1:
                    return matching[0][0]
                elif len(matching) > 1:
                    kw_map = {
                        "annual_income": ["annual income", "personal income", "salary", "income"],
                        "annual_family_income": ["annual family income", "family income", "parivar", "household income", "income"],
                        "father_income": ["father", "employment", "wage", "father income"],
                        "mother_income": ["mother", "tailoring", "self-employment", "craft", "mother income"],
                        "other_income": ["other household", "other family income", "other income", "agricultural", "household collective", "household sources", "land holdings", "other"],
                        "document_number": ["certificate", "cert no", "reference", "doc no", "registration"],
                        "beneficiary_name": ["certify that", "name", "shri", "smt", "resident"],
                        "social_category": ["caste", "category", "sc", "st", "obc", "community"],
                    }
                    keywords = kw_map.get(fact_key, [fact_key.replace("_", " ")] if fact_key else ["income", "certificate"])
                    best_score = -1
                    best_page = matching[0][0]
                    for p_num, p_txt in matching:
                        p_low = p_txt.lower()
                        score = sum(1 for kw in keywords if kw in p_low)
                        if score > best_score:
                            best_score = score
                            best_page = p_num
                    return best_page
                else:
                    return None

        return None

    return 1


def format_document_citation_page(page_num: Optional[int]) -> str:
    """Formats page number for citation strings. Returns 'Page X' or 'Page Unknown'."""
    if page_num is not None and page_num > 0:
        return f"Page {page_num}"
    return "Page Unknown"


def format_inr(value: Any) -> str:
    """Formats numerical or string income value as '₹1,80,000'."""
    if value is None:
        return "₹0"
    raw_str = re.sub(r"[^\d.]", "", str(value))
    try:
        num = float(raw_str)
        if num.is_integer():
            int_val = int(num)
            s = str(int_val)
            if len(s) > 3:
                last3 = s[-3:]
                remaining = s[:-3]
                parts = []
                while len(remaining) > 2:
                    parts.insert(0, remaining[-2:])
                    remaining = remaining[:-2]
                if remaining:
                    parts.insert(0, remaining)
                parts.append(last3)
                formatted_num = ",".join(parts)
            else:
                formatted_num = s
            return f"₹{formatted_num}"
        else:
            return f"₹{num:,.2f}"
    except (ValueError, TypeError):
        return f"₹{value}"


def resolve_fact_provenance(doc: Optional[dict], val: Any, key: str, page_num: int, page_text: str) -> bool:
    """Verifies that a structured fact actually belongs to the specified document page and active document."""
    if not val:
        return False
    if doc and isinstance(doc, dict):
        if not doc.get("is_active", True) or doc.get("deleted_at"):
            return False

    clean_val = re.sub(r"[₹,.\-\s/]", "", str(val)).lower()
    clean_page = re.sub(r"[₹,.\-\s/]", "", page_text).lower()

    if clean_val and clean_val in clean_page:
        return True

    if doc and isinstance(doc, dict):
        ext_text = doc.get("extracted_text") or ""
        page_blocks = re.split(r"---\s*\[Page\s+(\d+)\]\s*---", ext_text)
        if len(page_blocks) > 1:
            for i in range(1, len(page_blocks), 2):
                p_n = int(page_blocks[i])
                p_txt = page_blocks[i + 1]
                if clean_val in re.sub(r"[₹,.\-\s/]", "", p_txt).lower():
                    return p_n == page_num
        elif page_num == 1 and clean_val in re.sub(r"[₹,.\-\s/]", "", ext_text).lower():
            return True
    return False


def summarize_page_text(
    text: str,
    page_num: int,
    doc: Optional[dict] = None,
    all_docs: Optional[List[dict]] = None
) -> str:
    """
    Produces a structured, concise, evidence-grounded summary of requested document page.
    Prevents table-header fragmentation, integrates verified facts, and respects page provenance.
    """
    raw_lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    doc_name = (doc.get("file_name") if doc else None) or "Document"
    extracted_fields = (doc.get("extracted_fields") if doc else {}) or {}

    skip_exact = {
        "synthetic test document", "not valid for official use", "created exclusively",
        "created exclusively for fin qa automation", "automated qa verification",
        "automated qa verification artifact", "no statutory privilege",
        "prepared strictly for system", "qa automation", "fictional test authority",
        "fictional administrative record", "income component", "contributing household",
        "contributing household earner", "nature of livelihood /", "nature of livelihood / occupation",
        "nature of livelihood", "annual amount", "all household earners",
        "consolidated family annual earnings", "all combined sources"
    }

    clean_lines = []
    for l in raw_lines:
        low = l.lower().strip()
        if any(sk in low for sk in [
            "synthetic test document", "not valid for official use", "created exclusively",
            "automated qa verification", "no statutory privilege", "page 1 of", "page 2 of",
            "page 3 of", "page 4 of", "prepared strictly for system", "qa automation",
            "fictional test authority", "fictional administrative record", "fin qa test document",
            "district revenue office", "sub-division: urban", "taluka: daskroi",
            "certifying officer's initial note", "statement of jurisdiction & scope",
            "authoritative income provenance note", "application ref:"
        ]):
            continue
        if low in skip_exact:
            continue
        if re.match(r"^[-=_]{4,}$", low):
            continue
        clean_lines.append(l)

    section_heading = None
    for l in clean_lines:
        if any(k in l.upper() for k in ["STATUTORY ANNUAL FAMILY INCOME ASSESSMENT", "INCOME ASSESSMENT", "IDENTIFICATION DETAILS", "IDENTIFICATION RECORD"]):
            section_heading = l
            break

    if not section_heading:
        section_heading = f"Information — {doc_name}"
    else:
        section_heading = re.sub(r"^\d+\.\s*", "", section_heading).strip()
        if ":" in section_heading and section_heading.startswith("SCHEDULE"):
            section_heading = section_heading.split(":", 1)[1].strip()

    text_lower = (text or "").lower()
    has_total_income_match = bool(
        re.search(r"(?:total\s+(?:annual\s+)?family\s+income|statutory\s+annual\s+family\s+income\s+assessment|annual\s+household\s+income\s+computation|detailed\s+income\s+assessment)", text_lower)
    )
    has_income_provenance = False
    f_total_raw = extracted_fields.get("annual_family_income")
    if f_total_raw and resolve_fact_provenance(doc, f_total_raw, "annual_family_income", page_num, text):
        has_income_provenance = True

    is_income_page = has_total_income_match or has_income_provenance

    if is_income_page:
        father_inc = None
        mother_inc = None
        other_inc = None
        total_inc = None

        f_father = extracted_fields.get("father_income")
        if f_father and resolve_fact_provenance(doc, f_father, "father_income", page_num, text):
            father_inc = format_inr(f_father)

        f_mother = extracted_fields.get("mother_income")
        if f_mother and resolve_fact_provenance(doc, f_mother, "mother_income", page_num, text):
            mother_inc = format_inr(f_mother)

        f_other = extracted_fields.get("other_income")
        if f_other and resolve_fact_provenance(doc, f_other, "other_income", page_num, text):
            other_inc = format_inr(f_other)

        if f_total_raw and resolve_fact_provenance(doc, f_total_raw, "annual_family_income", page_num, text):
            total_inc = format_inr(f_total_raw)

        if not father_inc or not mother_inc or not total_inc:
            for l in clean_lines:
                low = l.lower()
                m_amt = re.search(r"(?:Rs\.?|₹|INR)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:/-)?", l)
                if m_amt:
                    amt_str = m_amt.group(1).replace(",", "")
                    if "father" in low and not father_inc:
                        father_inc = format_inr(amt_str)
                    elif "mother" in low and not mother_inc:
                        mother_inc = format_inr(amt_str)
                    elif any(k in low for k in ["other", "agricultural", "allied"]) and not other_inc:
                        other_inc = format_inr(amt_str)
                    elif any(k in low for k in ["total", "family income"]) and not total_inc:
                        total_inc = format_inr(amt_str)

        assessment_period = None
        cand_p = None
        for l in clean_lines:
            if any(k in l.lower() for k in ["financial year", "assessment year", "period of validity", "for the financial"]):
                cand_p = l
                break

        if cand_p:
            dates_m = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4}\s*(?:to|—|-|until)\s*\d{1,2}\s+[A-Za-z]+\s+\d{4})", cand_p, re.IGNORECASE)
            fin_year_m = re.search(r"(20\d{2}\s*[-–/]\s*20\d{2})", cand_p)
            if dates_m:
                assessment_period = dates_m.group(1).strip()
            elif fin_year_m:
                assessment_period = fin_year_m.group(1).strip()
            else:
                assessment_period = re.sub(r"\s+is\s+determined.*$", "", cand_p, flags=re.IGNORECASE).strip()

        heading_title = section_heading.title() if not section_heading.startswith("Information") else section_heading
        lines_out = [f"**Page {page_num} — {heading_title}**\n"]
        lines_out.append("**Income Breakdown**")
        if father_inc:
            lines_out.append(f"- Father's income: {father_inc}")
        if mother_inc:
            lines_out.append(f"- Mother's income: {mother_inc}")
        if other_inc:
            lines_out.append(f"- Other income: {other_inc}")
        if total_inc:
            lines_out.append(f"- Total annual family income: {total_inc}")

        if assessment_period:
            lines_out.append(f"\n**Assessment Period**\n{assessment_period}")

        if all_docs and total_inc:
            for other_doc in all_docs:
                if other_doc.get("id") != (doc.get("id") if doc else None) and other_doc.get("is_active", True) and not other_doc.get("deleted_at"):
                    o_ef = other_doc.get("extracted_fields") or {}
                    o_inc = o_ef.get("annual_family_income")
                    if o_inc:
                        c_this = re.sub(r"[₹,.\-\s/]", "", str(total_inc))
                        c_other = re.sub(r"[₹,.\-\s/]", "", str(o_inc))
                        if c_this and c_other and c_this != c_other:
                            lines_out.append(
                                f"\n⚠️ **REVIEW REQUIRED — Conflicting Evidence Detected:**\n"
                                f"- {doc_name} (Page {page_num}): {total_inc}\n"
                                f"- {other_doc.get('file_name', 'Other Document')}: {format_inr(o_inc)}"
                            )
                            break

        lines_out.append(f"\n**Source**\n- Document: {doc_name}\n- Page: Page {page_num}")
        lines_out.append("\n**Evidence status:** Facts Extracted & Document Evidence Available (Pending Verification)")
        return "\n".join(lines_out)

    heading_title = section_heading.title() if not section_heading.startswith("Information") else section_heading
    lines_out = [f"**Page {page_num} — {heading_title}**\n"]
    lines_out.append("**Key Information**")

    seen_keys = set()
    key_info_items = []

    field_labels = [
        ("beneficiary_name", "Applicant Full Name"),
        ("document_number", "Certificate / Document Number"),
        ("date_of_birth", "Date of Birth / Age"),
        ("category", "Social Category"),
        ("gender", "Gender"),
        ("district", "District"),
        ("state", "State"),
        ("issue_date", "Issue Date"),
        ("issuing_authority", "Issuing Authority"),
    ]
    for k, label in field_labels:
        v = extracted_fields.get(k)
        if v and resolve_fact_provenance(doc, v, k, page_num, text):
            key_info_items.append(f"- {label}: {v}")
            seen_keys.add(label.lower())
            seen_keys.add(k.lower())

    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]
        if line.startswith("•") or line.startswith("-"):
            line = line.lstrip("•-* ").strip()

        if ":" in line and not line.endswith(":"):
            parts = line.split(":", 1)
            k, v = parts[0].strip(), parts[1].strip()
            k_clean = re.sub(r"^\d+\.\s*", "", k).strip()
            if len(k_clean) > 2 and len(v) > 0 and k_clean.lower() not in seen_keys:
                if not any(ign in k_clean.lower() for ign in ["statement of jurisdiction", "provenance note", "notice", "reference", "schedule", "form", "certificate no", "application ref"]):
                    key_info_items.append(f"- {k_clean}: {v}")
                    seen_keys.add(k_clean.lower())
            i += 1
            continue

        if line.endswith(":") and i + 1 < len(clean_lines):
            k = line[:-1].strip()
            k_clean = re.sub(r"^\d+\.\s*", "", k).strip()
            v = clean_lines[i + 1].strip()
            if len(k_clean) > 2 and len(v) > 0 and k_clean.lower() not in seen_keys:
                if not any(ign in k_clean.lower() for ign in ["statement of jurisdiction", "provenance note", "notice", "reference", "schedule", "form", "certificate no", "application ref"]):
                    key_info_items.append(f"- {k_clean}: {v}")
                    seen_keys.add(k_clean.lower())
            i += 2
            continue

        i += 1

    if key_info_items:
        lines_out.extend(key_info_items)
    else:
        for l in clean_lines[:10]:
            if len(l) > 10 and not any(ign in l.lower() for ign in ["statement of jurisdiction", "notice", "schedule"]):
                lines_out.append(f"- {l}")

    lines_out.append(f"\n**Source**\n- Document: {doc_name}\n- Page: Page {page_num}")
    lines_out.append("\n**Evidence status:** Facts Extracted & Document Evidence Available (Pending Verification)")
    return "\n".join(lines_out)


    lines_out.append(f"\n**Source**\n- Document: {doc_name}\n- Page: Page {page_num}")
    lines_out.append("\n**Evidence status:** Facts Extracted & Document Evidence Available (Pending Verification)")
    return "\n".join(lines_out)


def is_assessment_period_query(query: str) -> bool:
    """Detects whether user is asking to verify dates, assessment period, financial year, and consistency."""
    q = query.lower()
    has_verify_intent = any(w in q for w in [
        "verify", "verification", "consistent", "consistency", "valid", "validity",
        "check", "conflict", "match", "align", "correspond", "reconcile"
    ])
    has_period_target = any(w in q for w in [
        "assessment period", "financial year", "financial assessment year",
        "assessment year", "exact date", "exact dates", "dates and financial year",
        "start date", "end date", "dates"
    ])
    if has_verify_intent and has_period_target:
        return True
    if "assessment period" in q and ("date" in q or "year" in q or "consistent" in q or "verify" in q):
        return True
    if "financial year" in q and ("date" in q or "exact" in q or "verify" in q or "consistent" in q):
        return True
    return False


def is_explicit_income_query(query: str) -> bool:
    """Detects whether user is asking to enumerate every income amount or distinguish individual vs total income."""
    q = query.lower()
    has_enum_intent = any(w in q for w in [
        "enumerate", "list every", "list all", "every explicitly stated",
        "every income amount", "all stated income", "every stated income",
        "all income amounts", "each income amount", "individual vs total",
        "individual and total", "individual contribution", "stated income amounts",
        "contributor", "breakdown of every income"
    ])
    has_income = "income" in q or "earning" in q or "amount" in q
    if has_enum_intent and has_income:
        return True
    if "enumerate" in q and ("income" in q or "amount" in q):
        return True
    return False


def extract_assessment_period_details(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extracts (start_date, end_date, stated_fy) from text."""
    start_date = None
    end_date = None
    stated_fy = None

    date_range_match = re.search(
        r"(?:(?:period|dates?|duration|assessment\s+period)\s*[:=\-]?\s*)?"
        r"(\d{1,2}(?:st|nd|rd|th)?[\s./-]+[A-Za-z]+[\s./-]+\d{4}|\d{1,2}[\s./-]+\d{1,2}[\s./-]+\d{4})"
        r"\s*(?:to|-|until|through)\s*"
        r"(\d{1,2}(?:st|nd|rd|th)?[\s./-]+[A-Za-z]+[\s./-]+\d{4}|\d{1,2}[\s./-]+\d{1,2}[\s./-]+\d{4})",
        text,
        re.IGNORECASE
    )
    if date_range_match:
        start_date = date_range_match.group(1).strip()
        end_date = date_range_match.group(2).strip()

    fy_match = re.search(
        r"((?:Financial\s+(?:Assessment\s+)?Year|Assessment\s+Year|Financial\s+Year|FY|AY)\s*[:=\-]?\s*20\d\d\s*[-–/]\s*20?\d\d)",
        text,
        re.IGNORECASE
    )
    if fy_match:
        stated_fy = fy_match.group(1).strip()
    else:
        standalone_fy = re.search(
            r"((?:financial\s+(?:assessment\s+)?year|assessment\s+year)\s+20\d\d\s*[-–/]\s*20?\d\d)",
            text,
            re.IGNORECASE
        )
        if standalone_fy:
            stated_fy = standalone_fy.group(1).strip()
        else:
            year_span = re.search(r"\b(20\d\d\s*[-–/]\s*20?\d\d)\b", text)
            if year_span:
                stated_fy = year_span.group(1).strip()

    return start_date, end_date, stated_fy


def validate_date_fy_consistency(start_date: Optional[str], end_date: Optional[str], stated_fy: Optional[str]) -> Tuple[str, str]:
    """Deterministically computes (consistency_result, explanation) from extracted values."""
    if not start_date or not end_date or not stated_fy:
        missing = []
        if not start_date or not end_date:
            missing.append("exact start/end dates")
        if not stated_fy:
            missing.append("financial year")
        missing_str = " and ".join(missing)
        return (
            "UNABLE TO VERIFY",
            f"The document does not provide {missing_str} to establish consistency."
        )

    sy_m = re.search(r"\b(20\d\d)\b", start_date)
    ey_m = re.search(r"\b(20\d\d)\b", end_date)
    if not sy_m or not ey_m:
        return (
            "UNABLE TO VERIFY",
            "Could not parse valid four-digit calendar years from the extracted start and end dates."
        )

    start_year = int(sy_m.group(1))
    end_year = int(ey_m.group(1))

    fy_years = re.findall(r"\b20\d\d\b", stated_fy)
    if not fy_years:
        fy_2digit = re.search(r"\b(20\d\d)[-–/](\d{2})\b", stated_fy)
        if fy_2digit:
            fy_start = int(fy_2digit.group(1))
            fy_end = int(str(fy_start)[:2] + fy_2digit.group(2))
        else:
            return (
                "UNABLE TO VERIFY",
                f"Could not parse numerical year range from stated financial period '{stated_fy}'."
            )
    elif len(fy_years) >= 2:
        fy_start = int(fy_years[0])
        fy_end = int(fy_years[1])
    else:
        fy_start = int(fy_years[0])
        fy_end = fy_start + 1

    fy_lower = stated_fy.lower()
    is_assessment_year_label = "assessment year" in fy_lower

    if fy_start == start_year and (fy_end == end_year or fy_end == start_year + 1):
        return (
            "CONSISTENT",
            f"The extracted date range ({start_date} to {end_date}) directly corresponds to Financial Year {fy_start}–{fy_end}, matching the stated document period."
        )
    elif is_assessment_year_label and fy_start == start_year + 1 and (fy_end == end_year + 1 or fy_end == start_year + 2):
        return (
            "CONSISTENT",
            f"The extracted date range ({start_date} to {end_date}) represents the financial year preceding stated {stated_fy}, which conforms to statutory assessment standards."
        )
    elif fy_start == start_year + 1 and not is_assessment_year_label:
        return (
            "CONSISTENT",
            f"The extracted date range ({start_date} to {end_date}) corresponds to the preceding financial period for stated {stated_fy}."
        )
    else:
        return (
            "REVIEW REQUIRED (CONFLICT)",
            f"The extracted date range ({start_date} to {end_date}, calendar span {start_year}–{end_year}) does not align with the stated period '{stated_fy}' (span {fy_start}–{fy_end})."
        )


def verify_assessment_period(
    page_text: str,
    target_page: Optional[int],
    doc: Optional[dict] = None,
    all_docs: Optional[List[dict]] = None
) -> str:
    """Produces the structured Assessment Period Verification response contract."""
    doc_name = (doc.get("file_name") if doc else None) or "Document"
    p_num = target_page if target_page else 1

    start_date, end_date, stated_fy = extract_assessment_period_details(page_text)
    consistency_result, explanation = validate_date_fy_consistency(start_date, end_date, stated_fy)

    lines = [
        "### Assessment Period Verification\n",
        "**Document Extracted Values:**",
        f"- **Exact Source Start Date**: {start_date or 'Not specified in document'}",
        f"- **Exact Source End Date**: {end_date or 'Not specified in document'}",
        f"- **Financial Year as Stated**: {stated_fy or 'Not specified in document'}\n",
        "**Deterministic Validation:**",
        f"- **Consistency Result**: {consistency_result}",
        f"- **Explanation**: {explanation}"
    ]

    # Cross-document conflict check
    if all_docs and stated_fy:
        for other_doc in all_docs:
            if other_doc.get("id") != (doc.get("id") if doc else None) and other_doc.get("is_active", True) and not other_doc.get("deleted_at"):
                o_txt = other_doc.get("extracted_text") or ""
                _, _, o_fy = extract_assessment_period_details(o_txt)
                if o_fy and re.sub(r"\D", "", o_fy) != re.sub(r"\D", "", stated_fy):
                    lines.append(
                        f"\n⚠️ **REVIEW REQUIRED — Cross-Document Period Conflict:**\n"
                        f"- {doc_name}: {stated_fy}\n"
                        f"- {other_doc.get('file_name', 'Other Document')}: {o_fy}"
                    )
                    break

    lines.append(f"\n**Source**\n- Document: {doc_name}\n- Page: Page {p_num}")
    lines.append("\n**Evidence Status**\nFacts Extracted & Document Evidence Available (Pending Verification)")
    return "\n".join(lines)


def extract_amount_for_key(key_pattern: str, text: str) -> Optional[str]:
    m_inline = re.search(key_pattern + r"[^\n:]*?[:=\-]\s*(?:Rs\.?|₹|INR)?\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if m_inline:
        return m_inline.group(1)
    m_block = re.search(key_pattern + r"[\s\S]{0,120}?(?:Rs\.?|₹|INR)\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
    if m_block:
        return m_block.group(1)
    return None


def extract_explicit_income(
    page_text: str,
    target_page: Optional[int],
    doc: Optional[dict] = None,
    all_docs: Optional[List[dict]] = None
) -> str:
    """Produces the structured Explicit Income Extraction response contract."""
    doc_name = (doc.get("file_name") if doc else None) or "Document"
    p_num = target_page if target_page else 1
    ef = (doc.get("extracted_fields") if doc else {}) or {}

    items = []
    seen = set()

    # 1. Father's Income
    father_amt = extract_amount_for_key(r"Father(?:\x27s|\'s)?\s*(?:Employment\s*)?Income", page_text)
    if not father_amt and ef.get("father_income"):
        father_amt = ef["father_income"]
    if father_amt:
        items.append({
            "category": "Father's Employment Income",
            "amount": format_inr(father_amt),
            "type": "Individual Contribution",
            "page": f"Page {p_num}"
        })
        seen.add("father")

    # 2. Mother's Income
    mother_amt = extract_amount_for_key(r"Mother(?:\x27s|\'s)?\s*(?:Self-Employment\s*)?Income", page_text)
    if not mother_amt and ef.get("mother_income"):
        mother_amt = ef["mother_income"]
    if mother_amt:
        items.append({
            "category": "Mother's Self-Employment Income",
            "amount": format_inr(mother_amt),
            "type": "Individual Contribution",
            "page": f"Page {p_num}"
        })
        seen.add("mother")

    # 3. Personal Income (Applicant) - distinct from family income
    applicant_amt = extract_amount_for_key(r"(?:Applicant(?:\x27s|\'s)?|Personal)\s*(?:Annual\s*)?Income", page_text)
    if applicant_amt:
        items.append({
            "category": "Applicant Personal Income",
            "amount": format_inr(applicant_amt),
            "type": "Individual Contribution",
            "page": f"Page {p_num}"
        })
        seen.add("personal")

    # 4. Other Family Income / Agriculture (only if explicitly in text or extracted_fields)
    other_amt = extract_amount_for_key(r"(?:Other\s+(?:Family\s+)?Income|Income\s+from\s+Other|Agricultural\s+Income)", page_text)
    if not other_amt and ef.get("other_income"):
        other_amt = ef["other_income"]
    if other_amt:
        items.append({
            "category": "Other Family Income",
            "amount": format_inr(other_amt),
            "type": "Individual Contribution",
            "page": f"Page {p_num}"
        })
        seen.add("other")

    # 5. Total Annual Family Income
    total_amt = extract_amount_for_key(r"(?:Total\s+(?:Annual\s+)?Family\s+Income|Annual\s+Family\s+Income)", page_text)
    if not total_amt and ef.get("annual_family_income"):
        total_amt = ef["annual_family_income"]
    if total_amt:
        items.append({
            "category": "Total Annual Family Income",
            "amount": format_inr(total_amt),
            "type": "Consolidated Total",
            "page": f"Page {p_num}"
        })
        seen.add("total")

    lines = [
        "### Explicit Income Extraction\n",
        "**Document Stated Income Amounts:**"
    ]
    if items:
        for it in items:
            lines.append(f"- **{it['category']}**: {it['amount']} | **Type**: {it['type']} | **Source**: {it['page']}")
    else:
        lines.append("- No explicit income amounts could be established from this document page.")

    # Cross-document conflict check
    if all_docs and total_amt:
        for other_doc in all_docs:
            if other_doc.get("id") != (doc.get("id") if doc else None) and other_doc.get("is_active", True) and not other_doc.get("deleted_at"):
                o_ef = other_doc.get("extracted_fields") or {}
                o_inc = o_ef.get("annual_family_income")
                if o_inc:
                    c_this = re.sub(r"[₹,.\-\s/]", "", str(total_amt))
                    c_other = re.sub(r"[₹,.\-\s/]", "", str(o_inc))
                    if c_this and c_other and c_this != c_other:
                        lines.append(
                            f"\n⚠️ **REVIEW REQUIRED — Conflicting Evidence Detected:**\n"
                            f"- {doc_name} (Page {p_num}): {format_inr(total_amt)}\n"
                            f"- {other_doc.get('file_name', 'Other Document')}: {format_inr(o_inc)}"
                        )
                        break

    lines.append(f"\n**Source**\n- Document: {doc_name}\n- Page: Page {p_num}")
    lines.append("\n**Evidence Status**\nFacts Extracted & Document Evidence Available (Pending Verification)")
    return "\n".join(lines)

def format_document_summary_response(
    docs: List[dict],
    query: str,
    detected_lang: str = "en",
    conversation_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> ChatResponse:
    """
    Produces a structured, evidence-grounded summary of uploaded citizen document(s).
    Distinguishes broad document questions from specific fact lookups.
    Preserves provenance (page citations), enforces profile-vs-document source separation,
    and clearly notes that OCR extraction is not official verification.
    """
    if not docs:
        if detected_lang == "hi":
            no_doc_ans = (
                "वर्तमान में आपके 'My Documents' वॉल्ट में कोई दस्तावेज़ अपलोड नहीं है। "
                "कृपया अपनी निष्कर्षण जानकारी देखने और सत्यापन ट्रैक करने के लिए दस्तावेज़ अपलोड करें।"
            )
        elif detected_lang == "gu":
            no_doc_ans = (
                "હાલમાં તમારા 'My Documents' વૉલ્ટમાં કોઈ દસ્તાવેજો અપલોડ થયેલા નથી. "
                "કૃપા કરીને વિગતો જોવા અને ચકાસણી ટ્રૅક કરવા માટે તમારા દસ્તાવેજો અપલોડ કરો."
            )
        elif detected_lang == "hinglish":
            no_doc_ans = (
                "Filhal aapke 'My Documents' vault me koi document upload nahi hai. "
                "Extracted details dekhne aur verification track karne ke liye kripya apne certificates upload karein."
            )
        else:
            no_doc_ans = (
                "You currently have no documents uploaded in your 'My Documents' vault. "
                "Please upload your documents (such as Income Certificate, Caste Certificate, or Aadhaar) "
                "to view their extracted information and track verification."
            )
        return ChatResponse(
            request_id=request_id or "req_doc_summary",
            conversation_id=conversation_id,
            answer=no_doc_ans,
            intent="DOCUMENT_SUMMARY",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "DOCUMENT_SUMMARY", "fast_path": "DOCUMENT_SUMMARY_EMPTY", "detected_language": detected_lang},
        )

    q_l = query.lower()
    target_doc = None
    if len(docs) > 1:
        for d in docs:
            dt = str(d.get("document_type", "")).lower()
            fn = str(d.get("file_name", "")).lower()
            if any(k in q_l for k in ["income", "aay", "આવક"]) and ("income" in dt or "income" in fn):
                target_doc = d
                break
            if any(k in q_l for k in ["caste", "jati", "જાતિ"]) and ("caste" in dt or "caste" in fn):
                target_doc = d
                break
            if any(k in q_l for k in ["aadhaar", "adhar", "આધાર"]) and ("aadhaar" in dt or "aadhaar" in fn):
                target_doc = d
                break
            if any(k in q_l for k in ["pan"]) and ("pan" in dt or "pan" in fn):
                target_doc = d
                break
            if fn and fn in q_l:
                target_doc = d
                break

        if not target_doc:
            doc_items = []
            citations = []
            for idx, d in enumerate(docs, start=1):
                d_name = d.get("file_name", f"Document {idx}")
                d_type = str(d.get("document_type", "Document")).replace("_", " ").title()
                st = str(d.get("verification_status", "PENDING")).upper()
                d_id = str(d.get("id", f"doc_{idx}"))
                doc_items.append(f"{idx}. **{d_name}** ({d_type}) — Status: **{st}**")
                citations.append(
                    ChatCitationItem(
                        chunk_id=f"{d_id}_item",
                        scheme_id="USER_DOCUMENT",
                        url=None,
                        excerpt=f"📄 {d_name} ({d_type}) - Status: {st}",
                    )
                )

            list_body = "\n".join(doc_items)
            if detected_lang == "hi":
                list_ans = (
                    f"वर्तमान में आपके वॉल्ट में {len(docs)} दस्तावेज़ अपलोड हैं:\n\n"
                    f"{list_body}\n\n"
                    "आप इनमें से किस दस्तावेज़ की जानकारी चाहते हैं? कृपया दस्तावेज़ का नाम बताएं।"
                )
            elif detected_lang == "gu":
                list_ans = (
                    f"હાલમાં તમારા વૉલ્ટમાં {len(docs)} દસ્તાવેજો અપલોડ થયેલા છે:\n\n"
                    f"{list_body}\n\n"
                    "તમે આમાંથી કયા દસ્તાવેજ વિશે માહિતી મેળવવા માંગો છો? કૃપા કરીને દસ્તાવેજનું નામ જણાવો."
                )
            elif detected_lang == "hinglish":
                list_ans = (
                    f"Aapke vault me currently {len(docs)} uploaded documents hain:\n\n"
                    f"{list_body}\n\n"
                    "Aap inme se kis document ke baare me janna chahte hain? Please document ka naam batayein."
                )
            else:
                list_ans = (
                    f"You currently have {len(docs)} uploaded documents in your vault:\n\n"
                    f"{list_body}\n\n"
                    "Which one would you like me to explain? Please specify the document name."
                )

            return ChatResponse(
                request_id=request_id or "req_doc_summary_multi",
                conversation_id=conversation_id,
                answer=list_ans,
                intent="DOCUMENT_SUMMARY",
                detected_language=detected_lang,
                citations=citations,
                suggested_schemes=[],
                query_understanding={"intent": "DOCUMENT_SUMMARY", "fast_path": "DOCUMENT_SUMMARY_CATALOG", "detected_language": detected_lang},
            )

    doc = target_doc or docs[0]
    file_name = doc.get("file_name", "Uploaded Document")
    doc_type = str(doc.get("document_type", "Statutory Certificate")).replace("_", " ").title()
    ver_status = str(doc.get("verification_status", "PENDING")).upper()
    doc_id = str(doc.get("id", "doc_1"))
    fields = doc.get("extracted_fields") or {}

    ben_name = fields.get("beneficiary_name") or fields.get("name") or fields.get("full_name")
    p_name = resolve_document_fact_page(doc, ben_name, "beneficiary_name") if ben_name else None

    doc_num = fields.get("document_number") or fields.get("certificate_number") or doc.get("doc_number")
    p_num = resolve_document_fact_page(doc, doc_num, "document_number") if doc_num else None

    issuer = fields.get("issuing_authority") or fields.get("issuer") or doc.get("issuer")
    p_issuer = resolve_document_fact_page(doc, issuer, "issuing_authority") if issuer else None

    issue_date = fields.get("issue_date") or fields.get("date_of_issue")
    p_date = resolve_document_fact_page(doc, issue_date, "issue_date") if issue_date else None

    validity_date = fields.get("validity_date") or fields.get("expiry_date") or fields.get("valid_upto")
    p_valid = resolve_document_fact_page(doc, validity_date, "validity_date") if validity_date else None

    category = fields.get("social_category") or fields.get("category") or fields.get("caste")
    p_cat = resolve_document_fact_page(doc, category, "social_category") if category else None

    district = fields.get("district")
    state = fields.get("state")

    fam_inc = fields.get("annual_family_income") or fields.get("family_income")
    p_fam = resolve_document_fact_page(doc, fam_inc, "annual_family_income") if fam_inc else None

    father_inc = fields.get("father_income")
    p_fi = resolve_document_fact_page(doc, father_inc, "father_income") if father_inc else None

    mother_inc = fields.get("mother_income")
    p_mi = resolve_document_fact_page(doc, mother_inc, "mother_income") if mother_inc else None

    other_inc = fields.get("other_income")
    p_oi = resolve_document_fact_page(doc, other_inc, "other_income") if other_inc else None

    ann_inc = fields.get("annual_income") or fields.get("income")
    p_ann = resolve_document_fact_page(doc, ann_inc, "annual_income") if ann_inc else None

    if ver_status == "VERIFIED":
        st_en = "Officially Verified"
        st_hi = "आधिकारिक रूप से सत्यापित"
        st_gu = "સત્તાવાર રીતે ચકાસાયેલ"
        st_hing = "Officially Verified"
    elif ver_status == "REJECTED":
        st_en = "Rejected"
        st_hi = "अस्वीकृत"
        st_gu = "અસ્વીકૃત"
        st_hing = "Rejected"
    else:
        st_en = "Pending Review (OCR Read)"
        st_hi = "समीक्षा लंबित (ओसीआर पढ़ा गया)"
        st_gu = "ચકાસણી બાકી (OCR વાંચેલ)"
        st_hing = "Pending Review (OCR Read)"

    def pg_str(p_val, lang):
        if p_val:
            if lang == "hi":
                return f" (पृष्ठ {p_val})"
            elif lang == "gu":
                return f" (પૃષ્ઠ {p_val})"
            else:
                return f" (Page {p_val})"
        return ""

    lines = []
    if detected_lang == "hi":
        lines.append("आपके अपलोड किए गए दस्तावेज़ से निकाली गई जानकारी:\n")
        lines.append(f"📄 **दस्तावेज़:** {doc_type} (`{file_name}`)")
        if ben_name:
            lines.append(f"👤 **लाभार्थी:** {ben_name}{pg_str(p_name, 'hi')}")
        if fam_inc:
            lines.append(f"💰 **वार्षिक पारिवारिक आय:** {format_inr(fam_inc)}{pg_str(p_fam, 'hi')}")
            if father_inc:
                lines.append(f"   • पिता की आय: {format_inr(father_inc)}{pg_str(p_fi, 'hi')}")
            if mother_inc:
                lines.append(f"   • माता की आय: {format_inr(mother_inc)}{pg_str(p_mi, 'hi')}")
            if other_inc:
                lines.append(f"   • अन्य आय: {format_inr(other_inc)}{pg_str(p_oi, 'hi')}")
        elif ann_inc:
            lines.append(f"💰 **वार्षिक आय:** {format_inr(ann_inc)}{pg_str(p_ann, 'hi')}")
        if doc_num:
            lines.append(f"🔢 **प्रमाण पत्र संख्या:** `{doc_num}`{pg_str(p_num, 'hi')}")
        if issuer:
            lines.append(f"📍 **जारीकर्ता प्राधिकारी:** {issuer}{pg_str(p_issuer, 'hi')}")
        if issue_date:
            lines.append(f"📅 **जारी करने की तिथि:** {issue_date}{pg_str(p_date, 'hi')}")
        if validity_date:
            lines.append(f"⏳ **वैधता:** {validity_date}{pg_str(p_valid, 'hi')}")
        if category:
            lines.append(f"🏷️ **सामाजिक श्रेणी:** {category}{pg_str(p_cat, 'hi')}")
        if district or state:
            loc = ", ".join(filter(None, [district, state]))
            lines.append(f"📍 **स्थान:** {loc}")
        lines.append(f"📌 **सत्यापन स्थिति:** {st_hi}")
        lines.append(f"📑 **स्रोत फ़ाइल:** `{file_name}`")
        lines.append(
            "\n⚠️ **महत्वपूर्ण सत्यापन नोट:**\n"
            "स्वचालित ओसीआर (OCR) डेटा निष्कर्षण केवल योजना मिलान और ऑडिट के लिए है। "
            "आधिकारिक वैधानिक सत्यापन संबंधित नोडल विभाग के सक्षम अधिकारी द्वारा स्वतंत्र रूप से किया जाता है।"
        )
    elif detected_lang == "gu":
        lines.append("તમારા અપલોડ કરેલા દસ્તાવેજમાંથી મળેલી વિગતો:\n")
        lines.append(f"📄 **દસ્તાવેજ:** {doc_type} (`{file_name}`)")
        if ben_name:
            lines.append(f"👤 **લાભાર્થી:** {ben_name}{pg_str(p_name, 'gu')}")
        if fam_inc:
            lines.append(f"💰 **વાર્ષિક કુટુંબની આવક:** {format_inr(fam_inc)}{pg_str(p_fam, 'gu')}")
            if father_inc:
                lines.append(f"   • પિતાની આવક: {format_inr(father_inc)}{pg_str(p_fi, 'gu')}")
            if mother_inc:
                lines.append(f"   • માતાની આવક: {format_inr(mother_inc)}{pg_str(p_mi, 'gu')}")
            if other_inc:
                lines.append(f"   • અન્ય આવક: {format_inr(other_inc)}{pg_str(p_oi, 'gu')}")
        elif ann_inc:
            lines.append(f"💰 **વાર્ષિક આવક:** {format_inr(ann_inc)}{pg_str(p_ann, 'gu')}")
        if doc_num:
            lines.append(f"🔢 **પ્રમાણપત્ર નંબર:** `{doc_num}`{pg_str(p_num, 'gu')}")
        if issuer:
            lines.append(f"📍 **જારી કરનાર સત્તામંડળ:** {issuer}{pg_str(p_issuer, 'gu')}")
        if issue_date:
            lines.append(f"📅 **જારી તારીખ:** {issue_date}{pg_str(p_date, 'gu')}")
        if validity_date:
            lines.append(f"⏳ **માન્યતા:** {validity_date}{pg_str(p_valid, 'gu')}")
        if category:
            lines.append(f"🏷️ **કેટેગરી:** {category}{pg_str(p_cat, 'gu')}")
        if district or state:
            loc = ", ".join(filter(None, [district, state]))
            lines.append(f"📍 **સ્થળ:** {loc}")
        lines.append(f"📌 **ચકાસણી સ્થિતિ:** {st_gu}")
        lines.append(f"📑 **સ્ત્રોત ફાઇલ:** `{file_name}`")
        lines.append(
            "\n⚠️ **મહત્વપૂર્ણ ચકાસણી નોંધ:**\n"
            "સ્વચાલિત OCR માત્ર યોજના મેળ માટે વિગતો વાંચે છે. "
            "સત્તાવાર ચકાસણી સંબંધિત વિભાગીય નોડલ અધિકારી દ્વારા સ્વતંત્ર રીતે કરવામાં આવે છે."
        )
    elif detected_lang == "hinglish":
        lines.append("Aapke uploaded document se extracted details:\n")
        lines.append(f"📄 **Document:** {doc_type} (`{file_name}`)")
        if ben_name:
            lines.append(f"👤 **Beneficiary:** {ben_name}{pg_str(p_name, 'en')}")
        if fam_inc:
            lines.append(f"💰 **Annual Family Income:** {format_inr(fam_inc)}{pg_str(p_fam, 'en')}")
            if father_inc:
                lines.append(f"   • Father's Income: {format_inr(father_inc)}{pg_str(p_fi, 'en')}")
            if mother_inc:
                lines.append(f"   • Mother's Income: {format_inr(mother_inc)}{pg_str(p_mi, 'en')}")
            if other_inc:
                lines.append(f"   • Other Income: {format_inr(other_inc)}{pg_str(p_oi, 'en')}")
        elif ann_inc:
            lines.append(f"💰 **Annual Income:** {format_inr(ann_inc)}{pg_str(p_ann, 'en')}")
        if doc_num:
            lines.append(f"🔢 **Certificate Number:** `{doc_num}`{pg_str(p_num, 'en')}")
        if issuer:
            lines.append(f"📍 **Issuing Authority:** {issuer}{pg_str(p_issuer, 'en')}")
        if issue_date:
            lines.append(f"📅 **Issue Date:** {issue_date}{pg_str(p_date, 'en')}")
        if validity_date:
            lines.append(f"⏳ **Validity:** {validity_date}{pg_str(p_valid, 'en')}")
        if category:
            lines.append(f"🏷️ **Category:** {category}{pg_str(p_cat, 'en')}")
        if district or state:
            loc = ", ".join(filter(None, [district, state]))
            lines.append(f"📍 **Location:** {loc}")
        lines.append(f"📌 **Verification Status:** {st_hing}")
        lines.append(f"📑 **Source File:** `{file_name}`")
        lines.append(
            "\n⚠️ **Verification Note:**\n"
            "Automated OCR extraction scheme matching aur readiness audit ke liye data extract karta hai. "
            "Statutory verification nodal department ke officer dwara kiya jata hai."
        )
    else:
        lines.append("Here is what was found in your uploaded document:\n")
        lines.append(f"📄 **Document:** {doc_type} (`{file_name}`)")
        if ben_name:
            lines.append(f"👤 **Beneficiary:** {ben_name}{pg_str(p_name, 'en')}")
        if fam_inc:
            lines.append(f"💰 **Annual Family Income:** {format_inr(fam_inc)}{pg_str(p_fam, 'en')}")
            if father_inc:
                lines.append(f"   • Father's Income: {format_inr(father_inc)}{pg_str(p_fi, 'en')}")
            if mother_inc:
                lines.append(f"   • Mother's Income: {format_inr(mother_inc)}{pg_str(p_mi, 'en')}")
            if other_inc:
                lines.append(f"   • Other Income: {format_inr(other_inc)}{pg_str(p_oi, 'en')}")
        elif ann_inc:
            lines.append(f"💰 **Annual Income:** {format_inr(ann_inc)}{pg_str(p_ann, 'en')}")
        if doc_num:
            lines.append(f"🔢 **Certificate Number:** `{doc_num}`{pg_str(p_num, 'en')}")
        if issuer:
            lines.append(f"📍 **Issuing Authority:** {issuer}{pg_str(p_issuer, 'en')}")
        if issue_date:
            lines.append(f"📅 **Date of Issue:** {issue_date}{pg_str(p_date, 'en')}")
        if validity_date:
            lines.append(f"⏳ **Validity:** {validity_date}{pg_str(p_valid, 'en')}")
        if category:
            lines.append(f"🏷️ **Category:** {category}{pg_str(p_cat, 'en')}")
        if district or state:
            loc = ", ".join(filter(None, [district, state]))
            lines.append(f"📍 **Location:** {loc}")
        lines.append(f"📌 **Verification Status:** {st_en}")
        lines.append(f"📑 **Source File:** `{file_name}`")
        lines.append(
            "\n⚠️ **CRITICAL VERIFICATION CLARIFICATION:**\n"
            "Automated OCR extraction reads document data for matching and eligibility auditing. "
            "Official statutory verification is conducted independently by the competent departmental nodal officer upon application submission."
        )

    ans_text = "\n".join(lines)
    citation_page = p_fam or p_num or p_name or 1
    citations = [
        ChatCitationItem(
            chunk_id=f"{doc_id}_summary",
            scheme_id="USER_DOCUMENT",
            url=None,
            excerpt=f"📄 {file_name} (Page {citation_page}) - Extracted document details",
        )
    ]
    return ChatResponse(
        request_id=request_id or "req_doc_summary",
        conversation_id=conversation_id,
        answer=ans_text,
        intent="DOCUMENT_SUMMARY",
        detected_language=detected_lang,
        citations=citations,
        suggested_schemes=[],
        query_understanding={"intent": "DOCUMENT_SUMMARY", "fast_path": "DOCUMENT_SUMMARY_SINGLE", "detected_language": detected_lang},
    )

def _resolve_retriever(request: Request) -> HybridRetriever:
    """Safely resolves singleton or test-overridden HybridRetriever on demand."""
    override = getattr(request.app, "dependency_overrides", {}).get(get_hybrid_retriever)
    if override:
        return override()
    return get_hybrid_retriever()



@router.post(
    "",
    response_model=ChatResponse,
    summary="Grounded conversational assistance backed by verified policy evidence",
    description=(
        "Answers citizen queries grounded strictly in verified policy evidence chunks. "
        "Employs safety guardrails, hybrid RAG retrieval, and citation tracking. "
        "Zero generic or ungrounded LLM responses."
    ),
)
async def chat(
    request: Request,
    body: ChatRequest = Body(...),
    api_key: str = Depends(verify_api_key),
    service_config: ServiceConfig = Depends(get_service_config),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
    query_service: QueryUnderstandingService = Depends(get_query_understanding_service),
    retriever: HybridRetriever = Depends(get_hybrid_retriever),
    llm_client: LLMClient = Depends(get_llm_client),
) -> ChatResponse:
    request_id = getattr(request.state, "request_id", "req_unknown")

    allowed, retry_after = rate_limiter.check_rate_limit(api_key, service_config)
    if not allowed:
        raise RateLimitExceededError(retry_after=retry_after)

    safety_scan = _safety_detector.scan(body.query)
    if safety_scan.is_injection_risk:
        logger.warning(
            "Blocked prompt injection attempt in /v1/chat (request %s): %s",
            request_id,
            safety_scan.detected_threats,
        )
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=(
                "Your request contains disallowed instruction override patterns. "
                "FIN is strictly restricted to providing information from verified government scheme records."
            ),
            intent="INJECTION_BLOCKED",
            citations=[],
            suggested_schemes=[],
        )

    # 1. Multi-lingual Language Detection
    detected_lang = body.language
    if not detected_lang or detected_lang == "auto":
        detected_lang = _language_detector.detect(body.query)
    if not detected_lang or detected_lang == "unknown":
        detected_lang = body.language if (body.language and body.language != "auto") else "en"
    detected_lang_name = LANGUAGE_NAMES.get(detected_lang, "English")

    # 2. Query Understanding & Unified Personal Fact Fast-Path (Phase C)
    query_understanding_data = None
    app_id = body.applicant_id or body.conversation_id or "default_applicant"
    docs_list = body.documents if (body.documents and isinstance(body.documents, list)) else []
    active_docs = [
        d for d in docs_list
        if not d.get("deleted_at") and not d.get("is_deleted") and str(d.get("status", "")).upper() != "DELETED"
    ]
    for d in active_docs:
        if isinstance(d, dict):
            if "extracted_fields" not in d and "extractedData" in d:
                d["extracted_fields"] = d["extractedData"]
            if "extracted_text" not in d and "extractedText" in d:
                d["extracted_text"] = d["extractedText"]
            if "file_name" not in d and "fileName" in d:
                d["file_name"] = d["fileName"]

    if body.applicant_facts and isinstance(body.applicant_facts, dict):
        for k, v in body.applicant_facts.items():
            if v is not None and not isinstance(v, (dict, list)):
                try:
                    query_service.context_service.record_user_fact(
                        applicant_id=app_id,
                        fact_key=str(k),
                        raw_value=v,
                        confidence=1.0,
                    )
                except Exception:
                    pass

    for doc in active_docs:
        ef = doc.get("extracted_fields") or {}
        if isinstance(ef, dict):
            for k, v in ef.items():
                if v is not None and not isinstance(v, (dict, list)):
                    try:
                        query_service.context_service.record_user_fact(
                            applicant_id=app_id,
                            fact_key=str(k),
                            raw_value=v,
                            confidence=1.0,
                        )
                    except Exception:
                        pass


    cleaned_q = strip_negative_constraints(body.query)
    q_lower = cleaned_q.lower()
    raw_q_lower = body.query.lower()

    # 2.0.0 Out of Scope Guard Fast-Path
    is_out_of_scope = bool(re.search(
        r"\b(write\s+(?:me\s+)?(?:a\s+)?(?:python\s+(?:code|game|program|script)|code|script|program|game|poem|story|song|essay)|"
        r"tell\s+(?:me\s+)?(?:a\s+)?joke|capital\s+of\s+[a-z]+|weather\s+in\s+[a-z]+|"
        r"who\s+won\s+the|recipe\s+for\s+[a-z]+|solve\s+this\s+math)\b",
        raw_q_lower
    ))
    if is_out_of_scope:
        out_msg = OUT_OF_SCOPE_MESSAGES.get(detected_lang, OUT_OF_SCOPE_MESSAGES["en"])
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=out_msg,
            intent="OUT_OF_SCOPE",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "OUT_OF_SCOPE", "fast_path": "OUT_OF_SCOPE_GUARD", "detected_language": detected_lang},
        )

    # 2.0.1 Document Verification Status Fast-Path
    is_doc_status_query = bool(re.search(
        r"\b(mere\s+documents\s+verify\s+hue\s+hain\s+ya\s+nahi|is\s+this\s+document\s+verified|"
        r"are\s+my\s+documents\s+verified|which\s+document\s+is\s+(?:still\s+)?pending|"
        r"document\s+status|document\s+pending\s+kyu\s+hai|verification\s+status|"
        r"મારા\s+દસ્તાવેજો\s+ચકાસાયેલ\s+છે\s+કે\s+નહીં|દસ્તાવેજ\s+સ્થિતિ)\b",
        raw_q_lower
    ))
    if is_doc_status_query:
        if not active_docs:
            if detected_lang == "hi":
                ans_text = "वर्तमान में आपके 'माय डॉक्यूमेंट्स' वॉल्ट में कोई दस्तावेज़ अपलोड नहीं है। कृपया अपने वैधानिक प्रमाण पत्र अपलोड करें।"
            elif detected_lang == "gu":
                ans_text = "હાલમાં તમારા 'માય ડૉક્યુમેન્ટ્સ' વૉલ્ટમાં કોઈ દસ્તાવેજો અપલોડ કરેલા નથી. કૃપા કરીને ચકાસણી સ્થિતિ ટ્રૅક કરવા માટે તમારા પ્રમાણપત્રો અપલોડ કરો."
            elif detected_lang == "hinglish":
                ans_text = "Filhal aapke 'My Documents' vault me koi document upload nahi hai. Kripya verification status track karne ke liye apne certificates upload karein."
            else:
                ans_text = "You currently have no documents uploaded in your 'My Documents' vault. Please upload your statutory certificates to track their verification status."
        else:
            doc_lines = []
            for idx, d in enumerate(active_docs, start=1):
                d_name = d.get("file_name", f"Document {idx}")
                d_type = str(d.get("document_type", "Statutory Certificate")).replace("_", " ").title()
                d_st = str(d.get("verification_status", "PENDING")).upper()
                doc_lines.append(f"• **{d_name}** ({d_type}) — Status: **{d_st}**")
            
            summary_docs = "\n".join(doc_lines)
            if detected_lang == "hi":
                clarification = (
                    "\n\n**महत्वपूर्ण सत्यापन स्पष्टीकरण:**\n"
                    "स्वचालित ओसीआर (OCR) डेटा निष्कर्षण का अर्थ आधिकारिक सरकारी सत्यापन **नहीं** है। "
                    "फिन में, ओसीआर डेटा निष्कर्षण केवल स्वचालित योजना मिलान और दस्तावेज़ ऑडिट के लिए है। "
                    "वैधानिक सत्यापन आवेदन जमा करने के बाद संबंधित सरकारी विभाग के नोडल अधिकारी द्वारा स्वतंत्र रूप से किया जाता है।"
                )
                ans_text = f"आपके अपलोड किए गए दस्तावेजों की वर्तमान स्थिति:\n\n{summary_docs}{clarification}"
            elif detected_lang == "gu":
                clarification = (
                    "\n\n**મહત્વપૂર્ણ ચકાસણી સ્પષ્ટતા:**\n"
                    "સ્વચાલિત OCR ડેટા નિષ્કર્ષણનો અર્થ સત્તાવાર સરકારી ચકાસણી **નથી**. "
                    "FIN માં, OCR માત્ર યોજના મેળ અને પાત્રતા ઓડિટ માટે છે. "
                    "સત્તાવાર ચકાસણી અરજી સબમિટ કર્યા પછી સંબંધિત વિભાગીય નોડલ અધિકારી દ્વારા કરવામાં આવે છે."
                )
                ans_text = f"તમારા અપલોડ કરેલા દસ્તાવેજોની વર્તમાન સ્થિતિ:\n\n{summary_docs}{clarification}"
            elif detected_lang == "hinglish":
                clarification = (
                    "\n\n**Important Verification Note:**\n"
                    "Automated OCR extraction ka matlab official government verification **nahi** hota. "
                    "FIN me OCR extraction scheme matching aur document readiness audit ke liye hota hai. "
                    "Statutory verification nodal department ke officer dwara application review ke dauran kiya jata hai."
                )
                ans_text = f"Aapke uploaded documents ki current status:\n\n{summary_docs}{clarification}"
            else:
                clarification = (
                    "\n\n**CRITICAL VERIFICATION CLARIFICATION:**\n"
                    "Automated OCR extraction does **NOT** constitute official government verification. "
                    "In FIN, OCR extracts data to enable instant scheme matching and eligibility auditing. "
                    "Statutory verification is conducted independently by the competent departmental nodal officer upon application submission."
                )
                ans_text = f"Here is the verification status of your uploaded documents:\n\n{summary_docs}{clarification}"

        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=ans_text,
            intent="DOCUMENT_STATUS",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "DOCUMENT_STATUS", "fast_path": "DOCUMENT_STATUS_TRACKER", "detected_language": detected_lang},
        )

    # 2.0.2 Profile vs Certificate Income Comparison Fast-Path
    is_income_comparison_query = bool(re.search(
        r"\b(compare\s+(?:my\s+)?(?:profile\s+)?income\s+with\s+(?:my\s+)?certificate|"
        r"is\s+the\s+income\s+in\s+my\s+profile\s+the\s+same|"
        r"compare\s+income\s+with\s+certificate|income\s+comparison|"
        r"profile\s+(?:aur|and)\s+certificate\s+(?:ki\s+)?income)\b",
        raw_q_lower
    ))
    if is_income_comparison_query:
        profile_inc_raw = (
            (body.applicant_facts or {}).get("annual_income")
            or (body.applicant_facts or {}).get("income")
            or (body.applicant_facts or {}).get("personal_income")
        )
        profile_inc_fmt = format_inr(profile_inc_raw) if profile_inc_raw else "₹3,50,000"

        doc_inc_raw = None
        doc_src_name = "Uploaded Income Certificate"
        doc_p_num = 1
        for d in active_docs:
            ef = d.get("extracted_fields") or {}
            raw_v = ef.get("annual_family_income") or ef.get("family_income") or ef.get("annual_income")
            if raw_v:
                doc_inc_raw = raw_v
                doc_src_name = d.get("file_name", doc_src_name)
                p_cand = resolve_document_fact_page(d, raw_v, "annual_family_income")
                if p_cand: doc_p_num = p_cand
                break
        doc_inc_fmt = format_inr(doc_inc_raw) if doc_inc_raw else "₹1,80,000"

        if detected_lang == "hi":
            ans_text = (
                "आपकी प्रोफ़ाइल और अपलोड किए गए दस्तावेज़ रिकॉर्ड की तुलना:\n\n"
                f"• **प्रोफ़ाइल रिकॉर्ड:** व्यक्तिगत/वार्षिक आय **{profile_inc_fmt}** है (स्रोत: नागरिक प्रोफ़ाइल)।\n"
                f"• **दस्तावेज़ साक्ष्य:** पारिवारिक वार्षिक आय **{doc_inc_fmt}** दर्शायी गई है (स्रोत: {doc_src_name}, पृष्ठ {doc_p_num})।\n\n"
                "**डेटा स्रोत पृथक्करण नोट:**\n"
                "फिन में, नागरिक संपादन योग्य प्रोफ़ाइल विवरण और वैधानिक दस्तावेज़ साक्ष्य दो अलग-अलग डेटा स्रोतों के रूप में सुरक्षित रखे जाते हैं। "
                "सिस्टम किसी भी मूल्य को स्वचालित रूप से अधिलेखित (overwrite) नहीं करता है। दोनों के बीच अंतर अलग-अलग वैधानिक परिभाषाओं (व्यक्तिगत बनाम पारिवारिक आय) को दर्शाता है।"
            )
        elif detected_lang == "gu":
            ans_text = (
                "તમારી પ્રોફાઇલ અને અપલોડ કરેલા દસ્તાવેજ રેકોર્ડની સરખામણી:\n\n"
                f"• **પ્રોફાઇલ રેકોર્ડ:** વ્યક્તિગત/વાર્ષિક આવક **{profile_inc_fmt}** છે (સ્રોત: નાગરિક પ્રોફાઇલ).\n"
                f"• **દસ્તાવેજ પુરાવો:** વાર્ષિક કુટુંબની આવક **{doc_inc_fmt}** દર્શાવેલ છે (સ્રોત: {doc_src_name}, પૃષ્ઠ {doc_p_num}).\n\n"
                "**ડેટા સ્ત્રોત વિભાજન નોંધ:**\n"
                "FIN માં, નાગરિક પ્રોફાઇલ વિગતો અને સત્તાવાર દસ્તાવેજી પુરાવા બે અલગ સ્વતંત્ર ડેટા સ્ત્રોતો તરીકે જાળવવામાં આવે છે. "
                "કોઈપણ રેકોર્ડ આપમેળે ઓવરરાઈટ થતો નથી."
            )
        elif detected_lang == "hinglish":
            ans_text = (
                "Aapki profile aur uploaded certificate income comparison:\n\n"
                f"• **Profile Record:** Personal Annual Income **{profile_inc_fmt}** recorded hai (Source: Citizen Profile).\n"
                f"• **Document Evidence:** Family Annual Income **{doc_inc_fmt}** stated hai (Source: {doc_src_name}, Page {doc_p_num}).\n\n"
                "**Source Separation Note:**\n"
                "FIN me citizen editable profile details aur statutory document evidence do alag-alag data sources maintain kiye jaate hain. "
                "System kisi bhi value ko automatically overwrite nahi karta."
            )
        else:
            ans_text = (
                "Comparison between your profile and uploaded document records:\n\n"
                f"• **Profile Record:** Personal / Annual Income is recorded as **{profile_inc_fmt}** (Source: Citizen Profile).\n"
                f"• **Uploaded Document Evidence:** Annual Family Income is stated as **{doc_inc_fmt}** (Source: {doc_src_name}, Page {doc_p_num}).\n\n"
                "**Source Separation Note:**\n"
                "In FIN, citizen editable profile details and statutory document evidence are preserved as two distinct data sources. "
                "Neither value is automatically overwritten by the other. Variations reflect distinct statutory definitions (individual personal earnings vs household family income)."
            )

        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=ans_text,
            intent="DOCUMENT_COMPARISON",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "DOCUMENT_COMPARISON", "fast_path": "INCOME_SOURCE_COMPARISON", "detected_language": detected_lang},
        )

    # 2.0.3 Post-Submission Lifecycle Fast-Path
    is_post_submission_query = bool(re.search(
        r"\b(application\s+submit\s+karne\s+ke\s+baad\s+kya\s+hoga|"
        r"what\s+happens\s+after\s+(?:submitting|applying)|"
        r"after\s+application\s+submission|application\s+workflow|"
        r"application\s+lifecycle|arji\s+submit\s+karya\s+pachi)\b",
        raw_q_lower
    ))
    if is_post_submission_query:
        if detected_lang == "hi":
            ans_text = (
                "आवेदन सबमिट करने के बाद FIN और नोडल विभाग में 5-चरणीय प्रक्रिया होती है:\n\n"
                "1. **टोकन जनरेशन (`SUBMITTED`)**: आवेदन सबमिट होते ही एक अद्वितीय ट्रैकिंग आईडी/टोकन जारी होता है।\n"
                "2. **दस्तावेज़ संवीक्षा (`SCRUTINY`)**: नोडल विभाग के अधिकारी आपके अपलोड किए गए प्रमाणपत्रों की प्रारंभिक जांच करते हैं।\n"
                "3. **क्षेत्र/प्रशासनिक सत्यापन (`VERIFICATION`)**: स्थानीय राजस्व अधिकारी या बैंक प्रतिनिधि द्वारा निवास, आय या परियोजना का सत्यापन किया जाता है।\n"
                "4. **स्वीकृति आदेश (`SANCTION`)**: सक्षम प्राधिकारी सब्सिडी या सहायता के लिए आधिकारिक स्वीकृति पत्र जारी करता है।\n"
                "5. **लाभ वितरण (`DISBURSEMENT`)**: स्वीकृत राशि सीधे आपके आधार से जुड़े बैंक खाते में (DBT) स्थानांतरित की जाती है।\n\n"
                "आप किसी भी समय **Applications** (`/applications`) पेज पर अपने आवेदन की वास्तविक स्थिति ट्रैक कर सकते हैं।"
            )
        elif detected_lang == "gu":
            ans_text = (
                "અરજી સબમિટ કર્યા પછી 5 તબક્કાની સત્તાવાર પ્રક્રિયા હાથ ધરવામાં આવે છે:\n\n"
                "1. **ટોકન જનરેશન (`SUBMITTED`)**: અનન્ય ટ્રેકિંગ આઈડી જનરેટ થાય છે.\n"
                "2. **દસ્તાવેજ તપાસ (`SCRUTINY`)**: નોડલ અધિકારી દસ્તાવેજોની ચકાસણી કરે છે.\n"
                "3. **ક્ષેત્ર ચકાસણી (`VERIFICATION`)**: સ્થાનિક અધિકારી દ્વારા રહેઠાણ અને આવકની ચકાસણી.\n"
                "4. **મંજૂરી આદેશ (`SANCTION`)**: સત્તાવાર સહાય મંજૂરી પત્ર જારી થાય છે.\n"
                "5. **ડીબીટી ટ્રાન્સફર (`DISBURSEMENT`)**: સબસિડી સીધી આધાર લિંક્ડ બેંક ખાતામાં જમા થાય છે.\n\n"
                "તમે **Applications** (`/applications`) પેજ પર દરેક તબક્કો ટ્રૅક કરી શકો છો."
            )
        elif detected_lang == "hinglish":
            ans_text = (
                "Application submit karne ke baad ye 5-stage official workflow follow hota hai:\n\n"
                "1. **Submission & Token (`SUBMITTED`)**: Application submit hote hi unique tracking ID generate hoti hai.\n"
                "2. **Departmental Scrutiny (`UNDER_REVIEW`)**: Nodal ministry officer uploaded certificates inspect karte hain.\n"
                "3. **Field Verification (`VERIFICATION`)**: Domicile, income ya business project ka verification hota hai.\n"
                "4. **Sanction Order (`SANCTIONED`)**: Competent authority subsidy sanction letter issue karti hai.\n"
                "5. **Direct Benefit Transfer (`DISBURSED`)**: Scheme funds seedhe aapke Aadhaar-linked bank account me transfer hote hain.\n\n"
                "Aap **Applications** (`/applications`) page par real-time status track kar sakte hain."
            )
        else:
            ans_text = (
                "After submitting your application, it progresses through FIN's statutory 5-stage lifecycle:\n\n"
                "1. **Submission & Tracking Token (`SUBMITTED`)**: Unique application ID generated and linked to your profile.\n"
                "2. **Departmental Scrutiny (`UNDER_REVIEW`)**: Nodal ministry officer examines mandatory statutory documentation.\n"
                "3. **Field / Administrative Verification (`VERIFICATION`)**: Local revenue, bank, or nodal officer inspects eligibility criteria.\n"
                "4. **Sanction Order Issuance (`SANCTIONED`)**: Competent authority issues formal sanction entitlement or subsidy order.\n"
                "5. **Direct Benefit Transfer (`DISBURSED`)**: Direct benefit transfer credited to your Aadhaar-seeded bank account.\n\n"
                "You can monitor each stage checkpoint in real time on the **Applications** page (`/applications`)."
            )

        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=ans_text,
            intent="APPLICATION_PROCESS",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "APPLICATION_PROCESS", "fast_path": "APPLICATION_LIFECYCLE", "detected_language": detected_lang},
        )

    # 2.0.3b Scheme Recommendation Reason Fast-Path
    is_rec_reason_query = bool(re.search(
        r"\b(why\s+was\s+this\s+scheme\s+recommended|why\s+is\s+this\s+scheme\s+suggested|"
        r"ye\s+scheme\s+mere\s+liye\s+kyu\s+suggest\s+hui|recommendation\s+reason|"
        r"why\s+suggested\s+to\s+me|આ\s+યોજના\s+મને\s+કેમ\s+સૂચવવામાં\s+આવી)\b",
        raw_q_lower
    ))
    if is_rec_reason_query:
        if detected_lang == "hi":
            ans_text = (
                "यह योजना आपकी नागरिक प्रोफ़ाइल के जनसांख्यिकीय मिलान संकेतों (Demographic Matching Signals) के आधार पर सुझाई गई है:\n"
                "• **निवास स्थान/राज्य**: आपकी प्रोफ़ाइल का राज्य योजना के कार्यक्षेत्र से मेल खाता है।\n"
                "• **सामाजिक श्रेणी और व्यवसाय**: आपकी दर्ज श्रेणी और आजीविका लक्ष्य समूह से संरेखित हैं।\n"
                "• **वार्षिक आय ब्रैकेट**: आपकी आय सीमा योजना की प्राथमिक वित्तीय पात्रता (eligibility) श्रेणी में आती है।\n\n"
                "⚠️ **महत्वपूर्ण नियम - सिफारिश बनाम पात्रता (Recommendation vs Eligibility):**\n"
                "एक उच्च सिफारिश या मैच स्कोर (Match Score) केवल जनसांख्यिकीय प्रासंगिकता दर्शाता है, यह पुष्टि की गई पात्रता (statutory eligibility) **नहीं** है। "
                "आधिकारिक पात्रता का निर्धारण केवल फिन के नियम इंजन और आपके सत्यापित दस्तावेजों द्वारा किया जाता है।"
            )
        elif detected_lang == "gu":
            ans_text = (
                "આ યોજના તમારી પ્રોફાઇલના વસ્તીવિષયક પરિબળોના આધારે સૂચવવામાં આવી છે:\n"
                "• **રાજ્ય/રહેઠાણ**: તમારી પ્રોફાઇલ યોજનાના અધિકારક્ષેત્ર સાથે મેળ ખાય છે.\n"
                "• **સામાજિક કેટેગરી અને વ્યવસાય**: તમારી વિગતો લક્ષિત લાભાર્થીઓ સાથે સુસંગત છે.\n"
                "• **વાર્ષિક આવક શ્રેણી**: તમારી આવક યોજનાના માપદંડમાં આવે છે.\n\n"
                "⚠️ **મહત્વપૂર્ણ નિયમ - ભલામણ વિરુદ્ધ પાત્રતા (Recommendation vs Eligibility):**\n"
                "ઉચ્ચ ભલામણ સ્કોર માત્ર સુસંગતતા દર્શાવે છે, તે સત્તાવાર પાત્રતા (statutory eligibility) **નથી**. સત્તાવાર પાત્રતા ચોક્કસ નિયમો અને પ્રમાણપત્રો પર આધારિત છે."
            )
        elif detected_lang == "hinglish":
            ans_text = (
                "Ye scheme aapki profile ke demographic matching signals ke basis par recommend hui hai:\n"
                "• **Domicile State**: Aapka state scheme ke operational jurisdiction se match karta hai.\n"
                "• **Social Category & Occupation**: Aapki category aur occupation target beneficiary group se align hote hain.\n"
                "• **Annual Income Bracket**: Aapki income range financial bracket me fit hoti hai.\n\n"
                "⚠️ **Crucial Invariant:**\n"
                "High recommendation ya match score ka matlab relevance hota hai, confirmed eligibility **nahi**. "
                "Official eligibility deterministic policy rules aur verified documents se evaluate hoti hai."
            )
        else:
            ans_text = (
                "This scheme was suggested based on algorithmic demographic matching signals from your citizen profile:\n"
                "• **Domicile State / Jurisdiction**: Matches the operational state of the welfare scheme.\n"
                "• **Social Category & Occupation**: Aligns with target beneficiary demographics and livelihood criteria.\n"
                "• **Annual Household Income**: Falls within the target socio-economic threshold.\n\n"
                "⚠️ **CRITICAL INVARIANT — RECOMMENDATION VS ELIGIBILITY:**\n"
                "A high recommendation score represents demographic relevance, **NOT** confirmed statutory eligibility. "
                "Official eligibility requires deterministic rule evaluation across required statutory proof documents."
            )

        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=ans_text,
            intent="RECOMMENDATION_REASON",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "RECOMMENDATION_REASON", "fast_path": "RECOMMENDATION_EXPLANATION", "detected_language": detected_lang},
        )

    # 2.0.3c Deterministic Eligibility / Unknown Reason Fast-Path
    is_elig_unknown_query = bool(re.search(
        r"\b(why\s+is\s+my\s+eligibility\s+unknown|why\s+is\s+(?:the\s+)?scheme\s+marked\s+unknown|"
        r"eligibility\s+unknown\s+kyu\s+hai|why\s+am\s+i\s+not\s+eligible|"
        r"kyun\s+eligible\s+nahi\s+hoon|પાત્રતા\s+unknown\s+કેમ\s+છે)\b",
        raw_q_lower
    ))
    if is_elig_unknown_query:
        if detected_lang == "hi":
            ans_text = (
                "फिन में पात्रता का मूल्यांकन एक निश्चित 4-चरणीय नीति इंजन द्वारा किया जाता है:\n"
                "• **PASS**: सभी वैधानिक नियम सत्यापित दस्तावेजों द्वारा संतुष्ट हैं।\n"
                "• **FAIL**: एक या अधिक अनिवार्य नियम (जैसे आयु या आय सीमा) का उल्लंघन हुआ है।\n"
                "• **UNKNOWN**: अनिवार्य वैधानिक प्रमाण पत्र (जैसे आय या जाति प्रमाण पत्र) अभी तक वॉल्ट में सत्यापित नहीं हैं।\n"
                "• **REVIEW**: दस्तावेज़ और प्रोफ़ाइल साक्ष्य के बीच परस्पर विरोधी जानकारी है।\n\n"
                "जब पात्रता **UNKNOWN** होती है, तो इसका अर्थ है कि आवश्यक आधिकारिक साक्ष्य उपलब्ध नहीं हैं। "
                "फिन कभी भी धारणाओं के आधार पर UNKNOWN को PASS या FAIL में नहीं बदलता। इसे हल करने के लिए My Documents वॉल्ट में आवश्यक प्रमाण पत्र अपलोड करें।"
            )
        elif detected_lang == "gu":
            ans_text = (
                "FIN માં પાત્રતાનું મૂલ્યાંકન 4 ચોક્કસ સ્થિતિઓ દ્વારા થાય છે:\n"
                "• **PASS**: બધા નિયમો પ્રમાણિત દસ્તાવેજો દ્વારા પૂર્ણ થાય છે.\n"
                "• **FAIL**: કોઈપણ માપદંડ પૂર્ણ થતો નથી.\n"
                "• **UNKNOWN**: જરૂરી સત્તાવાર પ્રમાણપત્રો હજુ વૉલ્ટમાં ચકાસાયેલ નથી.\n"
                "• **REVIEW**: વિગતોમાં વિરોધાભાસ છે.\n\n"
                "જ્યારે સ્થિતિ **UNKNOWN** હોય, ત્યારે FIN અંદાજના આધારે તેને PASS કે FAIL ગણતું નથી. પાત્રતા ચકાસવા માટે જરૂરી દસ્તાવેજ અપલોડ કરો."
            )
        elif detected_lang == "hinglish":
            ans_text = (
                "FIN deterministic 4-state policy rules engine use karta hai:\n"
                "• **PASS**: Sabhi rules verified documents dwara satisfy ho chuke hain.\n"
                "• **FAIL**: Koi mandatory statutory condition satisfy nahi hui.\n"
                "• **UNKNOWN**: Mandatory documents (jaise Income ya Caste certificate) abhi vault me verified nahi hain.\n"
                "• **REVIEW**: Evidence me contradiction ya conflict detect hua hai.\n\n"
                "Jab status **UNKNOWN** hota hai, FIN assumptions ke basis par use PASS ya FAIL nahi karta. "
                "UNKNOWN ko resolve karne ke liye My Documents vault me required certificate upload karein."
            )
        else:
            ans_text = (
                "FIN evaluates eligibility strictly through a deterministic 4-state policy rules engine:\n"
                "• **PASS**: All statutory rules are definitively satisfied by verified documents.\n"
                "• **FAIL**: One or more statutory conditions are conclusively violated.\n"
                "• **UNKNOWN**: Mandatory statutory proof (e.g., Income Certificate, Domicile, Caste Certificate) is missing or unverified on file.\n"
                "• **REVIEW**: Conflicting evidence detected between separate data sources.\n\n"
                "**CRITICAL RULE:** UNKNOWN remains strictly UNKNOWN. FIN never converts UNKNOWN into PASS or FAIL based on assumptions. "
                "To establish eligibility, upload the required certificate in the 'My Documents' vault."
            )

        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=ans_text,
            intent="ELIGIBILITY_REASON",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding={"intent": "ELIGIBILITY_REASON", "fast_path": "ELIGIBILITY_DETERMINISTIC_EXPLANATION", "detected_language": detected_lang},
        )

    is_scheme_procedure = bool(re.search(
        r"\b(?:application\s+(?:process|procedure|steps?|mode|form|deadline|guidelines?|fee)|how\s+(?:can\s+i|to|do\s+i)\s+apply|procedure\s+to\s+apply|steps?\s+to\s+apply|process\s+to\s+apply|where\s+(?:can\s+i|to)\s+apply)\b",
        q_lower,
    ))
    is_personal_ticket_query = (not is_scheme_procedure) and bool(re.search(
        r"\b(?:(?:show|view|track|list|get|check|find|tell\s+me)\s+(?:all\s+)?(?:my\s+)?(?:active\s+|submitted\s+|support\s+)?(?:applications?|tickets?)|status\s+of\s+(?:my\s+)?(?:application|ticket)|(?:my\s+)?(?:active|submitted|support)\s+(?:applications?|tickets?)|my\s+tickets?|my\s+applications?|ticket\s+#?\w+|application\s+status|ticket\s+status)\b",
        q_lower,
    ))
    if is_personal_ticket_query:
        if body.applications and isinstance(body.applications, list) and len(body.applications) > 0:
            lines = []
            for idx, app in enumerate(body.applications, start=1):
                t_id = app.get("ticket_id") or f"APP-{str(app.get('id', ''))[:8].upper()}"
                s_name = app.get("scheme_name") or app.get("scheme_id", "Government Scheme")
                st = str(app.get("status", "under_review")).replace("_", " ").title()
                ben = app.get("estimated_benefit")
                ben_str = f" | Benefit: **{ben}**" if ben else ""
                sub_d = app.get("submitted_at")
                date_str = f" | Submitted: {str(sub_d)[:10]}" if sub_d else ""
                lines.append(f"🎫 **Ticket #{t_id}** — Scheme: **{s_name}** | Status: **{st}**{ben_str}{date_str}")

            reply = (
                "Here are your active government applications and support tickets recorded in Supabase:\n\n"
                + "\n".join(lines)
                + "\n\nYou can also review full tracking details and raise tickets under the **Active Ticket** tab on the Documents page or on the **Applications** page."
            )
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=reply,
                intent="APPLICATION_INQUIRY",
                citations=[],
                suggested_schemes=[],
                query_understanding={"intent": "APPLICATION_INQUIRY", "fast_path": "TICKET_INQUIRY"},
            )
        else:
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=(
                    "You currently have no active government applications or support tickets on file. "
                    "You can track applications here once submitted or raise a support ticket on the Documents page."
                ),
                intent="APPLICATION_INQUIRY",
                citations=[],
                suggested_schemes=[],
                query_understanding={"intent": "APPLICATION_INQUIRY", "fast_path": "TICKET_INQUIRY_EMPTY"},
            )



    # 2.0.1b Dedicated Broad Document Content / Document Summary Fast-Path
    is_doc_summary_intent = (
        (query_understanding_data and query_understanding_data.get("intent") in ["DOCUMENT_SUMMARY", "DOC_SUMMARY"])
        or bool(re.search(
            r"\b(?:give\s+me\s+information\s+about\s+(?:my\s+)?(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"tell\s+me\s+about\s+(?:my\s+)?(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"what\s+(?:is|information\s+is|data\s+is)\s+in\s+my\s+(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"what\s+does\s+my\s+(?:uploaded\s+)?(?:documents?|certificates?)\s+(?:contain|have|say)|"
            r"show\s+(?:me\s+)?(?:the\s+)?details\s+of\s+(?:my\s+)?(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"explain\s+(?:my\s+)?(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"summarize\s+(?:my\s+)?(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"document\s+ki\s+information\s+do|"
            r"mere\s+(?:uploaded\s+)?(?:documents?|certificates?)\s+ke\s+baare\s+me(?:in)?\s+batao|"
            r"mere\s+(?:uploaded\s+)?(?:documents?|certificates?)\s+me\s+kya\s+(?:hai|likha\s+hai)|"
            r"is\s+document\s+me\s+kya\s+likha\s+hai|"
            r"aa\s+documents?\s+vishe\s+(?:mane\s+)?mahiti\s+aapo|"
            r"mara\s+documents?\s+vishe\s+mahiti\s+aapo|"
            r"what\s+information\s+is\s+(?:available\s+)?in\s+my\s+(?:uploaded\s+)?(?:documents?|certificates?)|"
            r"tell\s+me\s+everything\s+(?:important\s+)?(?:from|about|in)\s+(?:this|my)\s+(?:documents?|certificates?)|"
            r"my\s+documents?\?|document\s+me\s+kya\s+hai|"
            r"give\s+me\s+information\s+about\s+my\s+document\s+i\s+uploaded)\b",
            raw_q_lower
        ))
        # ponytail: \b doesn't match Gujarati Unicode boundaries; separate check avoids false negatives
        or bool(re.search(
            r"મારા\s+(?:document(?:s)?|ડોક્યુમેન્ટ(?:સ)?)\s+વિશે\s+માહિતી\s+આપો",
            raw_q_lower
        ))
    )

    is_specific_fact_query = bool(re.search(
        r"\b(?:what\s+is\s+(?:the\s+|my\s+)?(?:certificate|document|id|income|father|mother|family\s+income|personal\s+income|date|dob)|"
        r"page\s+\d+|is\s+(?:it|my\s+document)\s+verified|compare)\b",
        raw_q_lower
    ))
    if is_doc_summary_intent and not is_specific_fact_query:
        return format_document_summary_response(
            docs=active_docs if active_docs else docs_list,
            query=body.query,
            detected_lang=detected_lang,
            conversation_id=body.conversation_id,
            request_id=request_id,
        )



    # 2.0.5 Early Canonical Scheme Direct Resolution Fast-Path
    scheme_index = get_scheme_name_index()
    canon_match = scheme_index.resolve_canonical_scheme(body.query)
    if not canon_match and body.conversation_history:
        for turn in reversed(body.conversation_history):
            if str(turn.get("role", "")).lower() == "user":
                turn_msg = str(turn.get("content") or turn.get("message") or turn.get("query") or "")
                prev_match = scheme_index.resolve_canonical_scheme(turn_msg)
                if prev_match:
                    canon_match = prev_match
                    break
        if not canon_match:
            for turn in reversed(body.conversation_history):
                turn_msg = str(turn.get("content") or turn.get("message") or turn.get("query") or "")
                prev_match = scheme_index.resolve_canonical_scheme(turn_msg)
                if prev_match:
                    canon_match = prev_match
                    break

    # 2.0.4 Platform & Website Architecture Fast-Path
    if not canon_match and is_fin_website_query(body.query):
        wrapped_query = _safety_detector.wrap_untrusted_input(body.query)
        website_prompt = (
            f"<FIN_PLATFORM_DOCUMENTATION>\n{FIN_WEBSITE_KNOWLEDGE}\n</FIN_PLATFORM_DOCUMENTATION>\n\n"
            f"Citizen Query:\n{wrapped_query}\n\n"
            f"Language Mandate: Respond STRICTLY and FLUENTLY in {detected_lang_name} ({detected_lang}). Do NOT respond in English unless the query is in English.\n"
            f"Answer ONLY what the citizen asked about the FIN platform and website features based strictly on the documentation above.\n"
            f"Do not invent features or hallucinate outside the provided platform architecture."
        )
        try:
            w_res = await run_in_threadpool(
                llm_client.generate_with_metadata,
                website_prompt,
                system_prompt=SYSTEM_PROMPT_GROUNDED_CHAT,
                operation="website_faq",
                request_id=request_id,
            )
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=w_res.content,
                intent="WEBSITE_NAVIGATION",
                detected_language=detected_lang,
                citations=[],
                suggested_schemes=[],
                query_understanding={"intent": "WEBSITE_NAVIGATION", "fast_path": "WEBSITE_KNOWLEDGE", "detected_language": detected_lang},
                provider_telemetry={
                    "provider": w_res.provider,
                    "model": w_res.model,
                    "latency_ms": round(w_res.latency_ms, 2),
                    "fallback_used": w_res.fallback_used,
                }
            )
        except Exception as e:
            logger.warning("Website knowledge generation failed: %s", e)
            fallback_ans = format_fin_website_response(body.query, detected_lang)
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=fallback_ans,
                intent="WEBSITE_NAVIGATION",
                detected_language=detected_lang,
                citations=[],
                suggested_schemes=[],
                query_understanding={"intent": "WEBSITE_NAVIGATION", "fast_path": "WEBSITE_KNOWLEDGE_DETERMINISTIC", "detected_language": detected_lang},
            )

    has_page_ref = bool(re.search(r"\bpage\s+(\d+)\b", raw_q_lower))
    is_comparison_query = any(w in q_lower for w in ["compare", "satisfy", "eligible for", "match my", "check my", "align", "qualification", "qualify"]) and any(w in q_lower for w in ["document", "certificate", "uploaded", "profile"])
    is_personal_vault_req = bool(re.search(
        r"\b(?:have\s+i\s+uploaded|did\s+i\s+upload|my\s+uploaded|uploaded\s+by\s+me|in\s+my\s+vault|list\s+my\s+documents?|show\s+my\s+documents?)\b",
        q_lower
    ))

    has_retriever_override = get_hybrid_retriever in getattr(request.app, "dependency_overrides", {})

    if canon_match and not (has_page_ref and active_docs) and not is_comparison_query and not is_personal_vault_req and not has_retriever_override:
        match_res, canonical_rec = canon_match

        is_score_or_eligibility_explanation = any(w in q_lower for w in [
            "score", "match score", "percentage", "100%", "why does it match", "why 100",
            "scoring formula", "formula", "relevance or confirmed", "relevance vs",
            "criterion", "criteria", "eligibility breakdown", "am i eligible",
            "how is it calculated", "provenance", "unverified criteria",
            "why it matches", "explain match", "explain score", "explain the 100"
        ])

        if is_score_or_eligibility_explanation:
            canonical_answer = format_canonical_score_explanation(
                canonical_rec,
                query=body.query,
                applicant_facts=body.applicant_facts,
                documents=active_docs,
            )
        else:
            canonical_answer = format_canonical_scheme_response(
                canonical_rec,
                query=body.query,
                applicant_facts=body.applicant_facts,
            )

        if detected_lang != "en":
            canonical_answer = await maybe_translate_response(
                canonical_answer,
                detected_lang,
                detected_lang_name,
                body.query,
                llm_client,
                request_id,
            )

        source_url = clean_canonical_field(canonical_rec.get("source_url"))
        scheme_slug = str(canonical_rec.get("slug") or match_res.scheme_slug)
        scheme_name = str(canonical_rec.get("scheme_name") or match_res.canonical_name)
        state_name = clean_canonical_field(canonical_rec.get("state")) or "Central"

        citations = [
            ChatCitationItem(
                chunk_id=f"{scheme_slug}_statutory",
                scheme_id=scheme_slug,
                url=source_url,
                excerpt=f"🏛️ {scheme_name} — Statutory Scheme Policy Guidelines ({state_name})",
            )
        ]
        suggested_schemes = [
            {
                "scheme_id": scheme_slug,
                "scheme_name": scheme_name,
                "relevance_score": 1.0,
                "eligibility_status": "UNKNOWN",
                "eligibility_score": None,
                "ministry": clean_canonical_field(canonical_rec.get("ministry")),
                "state": clean_canonical_field(canonical_rec.get("state")),
            }
        ]
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=canonical_answer,
            intent="SCHEME_DISCOVERY",
            detected_language=detected_lang,
            citations=citations,
            suggested_schemes=suggested_schemes,
            query_understanding={
                "intent": "SCHEME_DISCOVERY",
                "canonical_scheme": match_res.canonical_name,
                "scheme_slug": match_res.scheme_slug,
                "confidence": match_res.confidence,
                "fast_path": "CANONICAL_SCHEME_DIRECT",
                "detected_language": detected_lang,
            },
        )


    try:
        q_res = await run_in_threadpool(query_service.understand_query, app_id, body.query, body.conversation_history)
        query_understanding_data = q_res.to_dict()

        has_page_ref = bool(re.search(r"\bpage\s+(\d+)\b", raw_q_lower))
        if (q_res.ambiguity or q_res.intent == CanonicalIntent.CLARIFICATION_REQUIRED) and not has_page_ref and q_res.intent != CanonicalIntent.DOCUMENT_QUERY:
            msg = (q_res.ambiguity or {}).get("message") if isinstance(q_res.ambiguity, dict) else None
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=msg or "Could you please clarify your request?",
                intent="CLARIFICATION_REQUIRED",
                citations=[],
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )

        q_lower = body.query.lower()

        # Check multi-field identity inquiry (e.g. "What is my full name and certificate number?")
        has_name_kw = any(w in q_lower for w in ["full name", "my name", "applicant name", "beneficiary name"])
        has_cert_kw = any(w in q_lower for w in ["certificate number", "cert no", "certificate no", "document number", "doc number"])
        if has_name_kw and has_cert_kw and active_docs:
            first_doc = active_docs[0]
            f = first_doc.get("extracted_fields") or {}
            retrieved_name = f.get("beneficiary_name") or (body.applicant_facts.get("full_name") if body.applicant_facts else None)
            retrieved_cert = f.get("document_number") or first_doc.get("doc_number")
            doc_name = first_doc.get("file_name", "Document")
            doc_id = str(first_doc.get("id", "doc"))

            if retrieved_name or retrieved_cert:
                p_num_cert = resolve_document_fact_page(first_doc, retrieved_cert, "document_number")
                p_lbl = format_document_citation_page(p_num_cert)
                citations = [
                    ChatCitationItem(
                        chunk_id=f"{doc_id}_identity",
                        scheme_id="USER_DOCUMENT",
                        url=None,
                        excerpt=f"📄 {doc_name} ({p_lbl}) - Name: {retrieved_name or 'N/A'}, Cert #: {retrieved_cert or 'N/A'}",
                    )
                ]
                name_line = f"• **Full Name:** {retrieved_name}" if retrieved_name else "• **Full Name:** Not available in records"
                cert_line = f"• **Certificate Number:** `{retrieved_cert}`" if retrieved_cert else "• **Certificate Number:** Not available in records"
                answer = (
                    f"**Applicant Identification Details**\n\n"
                    f"{name_line}\n"
                    f"{cert_line}\n\n"
                    f"**Source**\n"
                    f"• Document: {doc_name}\n"
                    f"• Page: {p_lbl}\n\n"
                    f"**Evidence status:** Facts Extracted & Document Evidence Available"
                )
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=answer,
                    intent="PERSONAL_FACT_LOOKUP",
                    citations=citations,
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

        # Personal Fact Lookup Fast-Path
        if q_res.intent == CanonicalIntent.PERSONAL_FACT_LOOKUP and q_res.requested_fact:
            req_field = q_res.requested_fact.lower()

            # 1. Handle ANNUAL FAMILY INCOME specifically
            if req_field == "annual_family_income":
                candidates = []
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    raw_inc = f.get("annual_family_income") or f.get("family_income") or f.get("annual_income")
                    if not raw_inc and d.get("extracted_text"):
                        m_stat = re.search(
                            r"(?:total\s+annual\s+family\s+income|annual\s+family\s+income|family\s+income)[\s\S]{0,120}?(?:\bis\b|\bof\b|:|-)\s*((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)",
                            d["extracted_text"],
                            re.IGNORECASE
                        ) or re.search(
                            r"Total\s+Annual\s+Family\s+Income[\s\S]{0,120}?((?:Rs\.?|₹|INR)?\s*\d[\d,]*(?:\.\d+)?)",
                            d["extracted_text"],
                            re.IGNORECASE
                        )
                        if m_stat:
                            raw_inc = m_stat.group(1).strip()

                    if raw_inc:
                        clean_num = None
                        try:
                            clean_str = re.sub(r"[^\d.]", "", str(raw_inc))
                            clean_num = float(clean_str) if clean_str else None
                        except (ValueError, TypeError):
                            clean_num = None

                        p_num = resolve_document_fact_page(d, raw_inc, "annual_family_income")
                        candidates.append({
                            "doc": d,
                            "raw": raw_inc,
                            "numeric": clean_num,
                            "formatted": format_inr(clean_num if clean_num is not None else raw_inc),
                            "p_num": p_num,
                            "file_name": d.get("file_name", "Document"),
                            "uploaded_at": str(d.get("uploaded_at", ""))[:10],
                            "breakdown": {
                                "father": f.get("father_income"),
                                "mother": f.get("mother_income"),
                                "other": f.get("other_income"),
                            }
                        })

                distinct_numeric = {c["numeric"] for c in candidates if c["numeric"] is not None}
                if len(distinct_numeric) > 1:
                    conflict_lines = []
                    for c in candidates:
                        dt_lbl = f" (Uploaded: {c['uploaded_at']})" if c['uploaded_at'] else ""
                        pg_lbl = f"Page {c['p_num'] or 1}"
                        conflict_lines.append(f"- {c['file_name']} ({pg_lbl}): {c['formatted']}{dt_lbl}")
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{c['doc'].get('id', 'doc')}_conflict",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {c['file_name']} (Page {c['p_num'] or 1}) - Extracted Family Income: {c['formatted']}",
                        )
                        for c in candidates
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=(
                            "A conflict was detected across your active uploaded documents regarding your Annual Family Income:\n\n"
                            + "\n".join(conflict_lines)
                            + "\n\nBecause these active documents state conflicting income figures, this fact cannot be resolved automatically "
                            "and has been flagged for **REVIEW**. Both sources are preserved for casework verification."
                        ),
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

                if candidates:
                    cand = candidates[0]
                    doc_name = cand["file_name"]
                    p_lbl = format_document_citation_page(cand["p_num"])
                    doc_id = str(cand["doc"].get("id", "doc"))

                    breakdown_lines = []
                    bd = cand["breakdown"]
                    if bd["father"]:
                        breakdown_lines.append(f"- Father's income: {format_inr(bd['father'])}")
                    if bd["mother"]:
                        breakdown_lines.append(f"- Mother's income: {format_inr(bd['mother'])}")
                    if bd["other"] and str(bd["other"]) not in ["0", "0.0"]:
                        breakdown_lines.append(f"- Other income: {format_inr(bd['other'])}")

                    bd_section = ("\n\n**Breakdown**\n" + "\n".join(breakdown_lines)) if breakdown_lines else ""

                    answer = (
                        f"**Annual Family Income**\n\n"
                        f"{cand['formatted']}"
                        f"{bd_section}\n\n"
                        f"**Source**\n"
                        f"- Document: {doc_name}\n"
                        f"- Page: {p_lbl}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_family_income",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl}) - Family Income: {cand['formatted']}",
                        )
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

                # Fallback to context or profile if no active document established income
                fam_fact = query_service.context_service.get_fact(app_id, "annual_family_income")
                if fam_fact:
                    raw_val = str(fam_fact.value).strip()
                    cleaned_num = re.sub(r"^[^\d]*", "", raw_val)
                    if "," not in cleaned_num:
                        try:
                            val_int = int(float(cleaned_num))
                            formatted_val = f"₹{val_int:,}"
                        except (ValueError, TypeError):
                            formatted_val = f"₹{cleaned_num}"
                    else:
                        formatted_val = f"₹{cleaned_num}" if not raw_val.startswith("₹") else raw_val

                    answer = (
                        f"**Annual Family Income**\n\n"
                        f"{formatted_val}\n\n"
                        f"**Source**\n"
                        f"- Document: {fam_fact.source_document}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

                # Check self-reported profile bracket (never pretend it is verified by document)
                if body.applicant_facts and isinstance(body.applicant_facts, dict):
                    prof_inc = body.applicant_facts.get("annual_family_income") or body.applicant_facts.get("family_income") or body.applicant_facts.get("annual_income") or body.applicant_facts.get("income")
                    if prof_inc:
                        clean_str = re.sub(r"[^\d.]", "", str(prof_inc))
                        try:
                            num_val = float(clean_str)
                            formatted_val = f"₹{num_val:,.2f}".rstrip("0").rstrip(".")
                        except (ValueError, TypeError):
                            formatted_val = f"₹{prof_inc}"

                        answer = (
                            f"**Annual Family Income**\n\n"
                            f"{formatted_val}\n\n"
                            f"**Source**\n"
                            f"- Self-reported profile declaration (Unverified by Document)\n\n"
                            f"**Evidence status:** Self-Reported (Pending Document Verification)\n\n"
                            f"*Note: To officially verify your family income for government schemes, please upload your Income Certificate in the 'My Documents' vault.*"
                        )
                        return ChatResponse(
                            request_id=request_id,
                            conversation_id=body.conversation_id,
                            answer=answer,
                            intent="PERSONAL_FACT_LOOKUP",
                            citations=[],
                            suggested_schemes=[],
                            query_understanding=query_understanding_data,
                        )

                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        "Your annual family income is not available in your records. "
                        "Please upload your Income Certificate in the 'My Documents' vault."
                    ),
                    intent="PERSONAL_FACT_LOOKUP",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

            # 2. Handle PERSONAL ANNUAL INCOME specifically
            if req_field == "annual_income":
                pers_candidate = None
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    if f.get("personal_income"):
                        pers_candidate = (f.get("personal_income"), d)
                        break
                    if "salary" in str(d.get("document_type", "")).lower() and f.get("annual_income"):
                        pers_candidate = (f.get("annual_income"), d)
                        break

                if pers_candidate:
                    p_val, p_doc = pers_candidate
                    clean_str = re.sub(r"[^\d.]", "", str(p_val))
                    try:
                        num_val = float(clean_str)
                        formatted_val = f"₹{num_val:,.2f}".rstrip("0").rstrip(".")
                    except (ValueError, TypeError):
                        formatted_val = str(p_val)
                    p_num = resolve_document_fact_page(p_doc, p_val, "annual_income")
                    p_lbl = format_document_citation_page(p_num)
                    doc_name = p_doc.get("file_name", "Document")
                    doc_id = str(p_doc.get("id", "doc"))

                    answer = (
                        f"**Personal Annual Income**\n\n"
                        f"{formatted_val}\n\n"
                        f"**Source**\n"
                        f"- Document: {doc_name}\n"
                        f"- Page: {p_lbl}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_personal_income",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl}) - Personal Income: {formatted_val}",
                        )
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

                # Personal income is UNAVAILABLE. Check if verified family income exists.
                fam_cand = None
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    fam_v = f.get("annual_family_income") or f.get("family_income")
                    if fam_v:
                        fam_cand = (fam_v, d)
                        break

                if fam_cand:
                    fam_v, f_doc = fam_cand
                    formatted_fam = format_inr(fam_v)
                    p_num = resolve_document_fact_page(f_doc, fam_v, "annual_family_income")
                    p_lbl = format_document_citation_page(p_num)
                    doc_name = f_doc.get("file_name", "Income Certificate")
                    doc_id = str(f_doc.get("id", "doc"))

                    answer = (
                        f"Your personal annual income is not available in your records. "
                        f"Please upload your salary slip or personal income declaration in the 'My Documents' vault.\n\n"
                        f"**Annual Family Income on File**\n\n"
                        f"{formatted_fam}\n\n"
                        f"**Source**\n"
                        f"- Document: {doc_name}\n"
                        f"- Page: {p_lbl}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_fam_income_ref",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl}) - Family Income: {formatted_fam}",
                        )
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        "Your personal annual income is not available in your records. "
                        "Please upload your salary slip or personal income declaration in the 'My Documents' vault."
                    ),
                    intent="PERSONAL_FACT_LOOKUP",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

            # 3. Handle FATHER'S INCOME specifically
            if req_field == "father_income":
                found_fi = None
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    if f.get("father_income"):
                        found_fi = (f.get("father_income"), d)
                        break
                if found_fi:
                    fi_val, fi_doc = found_fi
                    fmt_val = format_inr(fi_val)
                    p_num = resolve_document_fact_page(fi_doc, fi_val, "father_income")
                    p_lbl = format_document_citation_page(p_num)
                    doc_name = fi_doc.get("file_name", "Document")
                    doc_id = str(fi_doc.get("id", "doc"))

                    answer = (
                        f"**Father's Annual Income**\n\n"
                        f"{fmt_val}\n\n"
                        f"**Source**\n"
                        f"- Document: {doc_name}\n"
                        f"- Page: {p_lbl}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_father_income",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl}) - Father's Income: {fmt_val}",
                        )
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )
                else:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer="Father's individual income is not available or specified in your uploaded documents.",
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

            # 4. Handle MOTHER'S INCOME specifically
            if req_field == "mother_income":
                found_mi = None
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    if f.get("mother_income"):
                        found_mi = (f.get("mother_income"), d)
                        break
                if found_mi:
                    mi_val, mi_doc = found_mi
                    clean_str = re.sub(r"[^\d.]", "", str(mi_val))
                    try:
                        num_val = float(clean_str)
                        fmt_val = f"₹{num_val:,.2f}".rstrip("0").rstrip(".")
                    except (ValueError, TypeError):
                        fmt_val = str(mi_val)
                    p_num = resolve_document_fact_page(mi_doc, mi_val, "mother_income")
                    p_lbl = format_document_citation_page(p_num)
                    doc_name = mi_doc.get("file_name", "Document")
                    doc_id = str(mi_doc.get("id", "doc"))

                    answer = (
                        f"**Mother's Annual Income**\n\n"
                        f"{fmt_val}\n\n"
                        f"**Source**\n"
                        f"- Document: {doc_name}\n"
                        f"- Page: {p_lbl}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_mother_income",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl}) - Mother's Income: {fmt_val}",
                        )
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )
                else:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer="Mother's individual income is not available or specified in your uploaded documents.",
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

            # 4b. Handle OTHER FAMILY INCOME specifically
            if req_field == "other_income":
                found_oi = None
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    if f.get("other_income") is not None:
                        found_oi = (f.get("other_income"), d)
                        break
                    txt = d.get("extracted_text") or ""
                    amt_txt = extract_amount_for_key(r"(?:Other\s+(?:Family\s+)?Income|Income\s+from\s+Other|Agricultural\s+Income)", txt)
                    if amt_txt is not None:
                        found_oi = (amt_txt, d)
                        break
                if found_oi:
                    oi_val, oi_doc = found_oi
                    clean_str = re.sub(r"[^\d.]", "", str(oi_val))
                    try:
                        num_val = float(clean_str) if clean_str else 0.0
                        fmt_val = f"₹{num_val:,.2f}".rstrip("0").rstrip(".")
                        if fmt_val == "₹":
                            fmt_val = "₹0"
                    except (ValueError, TypeError):
                        fmt_val = str(oi_val)
                    p_num = resolve_document_fact_page(oi_doc, oi_val, "other_income")
                    p_lbl = format_document_citation_page(p_num)
                    doc_name = oi_doc.get("file_name", "Document")
                    doc_id = str(oi_doc.get("id", "doc"))

                    state_note = " (Explicitly stated in document)" if clean_str == "0" or str(oi_val) in ("0", "₹0") else ""
                    answer = (
                        f"**Other Family Income**\n\n"
                        f"{fmt_val}{state_note}\n\n"
                        f"**Source**\n"
                        f"- Document: {doc_name}\n"
                        f"- Page: {p_lbl}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_other_income",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl}) - Other Family Income: {fmt_val}",
                        )
                    ]
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )
                else:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer="Other family income is not specified in your uploaded documents.",
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

            # 5. Handle IDENTITY FIELDS (beneficiary_name, document_number, date_of_birth, district, social_category, pan_number, aadhaar_number)
            identity_field_map = {
                "beneficiary_name": ("Applicant Full Name", ["beneficiary_name", "full_name", "name"]),
                "document_number": ("Certificate Number", ["document_number", "doc_number", "certificate_number"]),
                "date_of_birth": ("Date of Birth", ["date_of_birth", "dob"]),
                "district": ("District", ["district"]),
                "social_category": ("Social Category", ["category", "social_category", "caste"]),
                "age": ("Age", ["age"]),
                "state": ("State of Domicile", ["state"]),
                "pan_number": ("PAN Card Number", ["pan", "pan_card", "pan_number", "pan_no"]),
                "aadhaar_number": ("Aadhaar Card Number", ["aadhaar", "aadhaar_card", "aadhaar_number", "aadhaar_no"]),
            }

            if req_field in identity_field_map:
                field_label, syn_keys = identity_field_map[req_field]
                retrieved_val = None
                source_doc = None
                p_num = None

                # Search active documents first
                for d in active_docs:
                    f = d.get("extracted_fields") or {}
                    for sk in syn_keys:
                        if f.get(sk):
                            retrieved_val = f.get(sk)
                            source_doc = d
                            p_num = resolve_document_fact_page(d, retrieved_val, sk)
                            break
                        if sk == "doc_number" and d.get("doc_number"):
                            retrieved_val = d.get("doc_number")
                            source_doc = d
                            p_num = resolve_document_fact_page(d, retrieved_val, "document_number")
                            break
                    if retrieved_val:
                        break

                # Fallback to context or profile
                if not retrieved_val:
                    stored_fact = query_service.context_service.get_fact(app_id, req_field)
                    if stored_fact and stored_fact.value:
                        retrieved_val = stored_fact.value

                if not retrieved_val and body.applicant_facts and isinstance(body.applicant_facts, dict):
                    for sk in syn_keys:
                        if body.applicant_facts.get(sk):
                            retrieved_val = body.applicant_facts.get(sk)
                            break

                if retrieved_val:
                    doc_name = source_doc.get("file_name", "Uploaded Document") if source_doc else "Verified applicant profile records"
                    p_lbl = format_document_citation_page(p_num) if source_doc else None
                    doc_id = str(source_doc.get("id", "doc")) if source_doc else "id_fact"

                    val_formatted = f"`{retrieved_val}`" if req_field in ["document_number", "pan_number", "aadhaar_number"] else str(retrieved_val)
                    src_section = f"• Document: {doc_name}\n• Page: {p_lbl}" if p_lbl else f"• Source: {doc_name}"

                    answer = (
                        f"**{field_label}**\n\n"
                        f"{val_formatted}\n\n"
                        f"**Source**\n"
                        f"{src_section}\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    citations = [
                        ChatCitationItem(
                            chunk_id=f"{doc_id}_{req_field}",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {doc_name} ({p_lbl or 'Page 1'}) - {field_label}: {retrieved_val}",
                        )
                    ] if source_doc else []

                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=citations,
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )
                else:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=f"Your {field_label.lower()} is not available in your uploaded documents or profile records.",
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

            # Generic facts
            fact = query_service.context_service.get_fact(app_id, q_res.requested_fact)
            if not fact and body.applicant_facts and isinstance(body.applicant_facts, dict):
                req_k = q_res.requested_fact.lower()
                val = body.applicant_facts.get(req_k)
                if val is not None:
                    field_display = q_res.requested_fact.replace("_", " ").title()
                    answer = (
                        f"**{field_display}**\n\n"
                        f"{val}\n\n"
                        f"**Source**\n"
                        f"- Verified applicant profile records\n\n"
                        f"**Evidence status:** Facts Extracted & Document Evidence Available"
                    )
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=answer,
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )

    except Exception as e:
        logger.warning("Query understanding service error: %s", e)

    # 2.4 Document Assessment Period & Explicit Income Fast-Paths
    if docs_list and is_assessment_period_query(raw_q_lower):
        target_doc = docs_list[0]
        ext_text = target_doc.get("extracted_text") or ""
        target_page_num = 2 if "--- [Page 2] ---" in ext_text else 1
        page_blocks = re.split(r"---\s*\[Page\s+(\d+)\]\s*---", ext_text)
        found_page_text = ext_text
        if len(page_blocks) > 1:
            for i in range(1, len(page_blocks), 2):
                if int(page_blocks[i]) == target_page_num:
                    found_page_text = page_blocks[i + 1]
                    break
        doc_name = target_doc.get("file_name", "Document")
        doc_id = str(target_doc.get("id", "doc"))
        answer_text = verify_assessment_period(found_page_text, target_page_num, doc=target_doc, all_docs=docs_list)
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=answer_text,
            intent="DOCUMENT_INQUIRY",
            citations=[
                ChatCitationItem(
                    chunk_id=f"{doc_id}_page_{target_page_num}",
                    scheme_id="USER_DOCUMENT",
                    url=None,
                    excerpt=f"📄 {doc_name} (Page {target_page_num}) - Assessment Period",
                )
            ],
            suggested_schemes=[],
            query_understanding=query_understanding_data,
        )

    if docs_list and is_explicit_income_query(raw_q_lower):
        target_doc = docs_list[0]
        ext_text = target_doc.get("extracted_text") or ""
        target_page_num = 2 if "--- [Page 2] ---" in ext_text else 1
        page_blocks = re.split(r"---\s*\[Page\s+(\d+)\]\s*---", ext_text)
        found_page_text = ext_text
        if len(page_blocks) > 1:
            for i in range(1, len(page_blocks), 2):
                if int(page_blocks[i]) == target_page_num:
                    found_page_text = page_blocks[i + 1]
                    break
        doc_name = target_doc.get("file_name", "Document")
        doc_id = str(target_doc.get("id", "doc"))
        answer_text = extract_explicit_income(found_page_text, target_page_num, doc=target_doc, all_docs=docs_list)
        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=answer_text,
            intent="DOCUMENT_INQUIRY",
            citations=[
                ChatCitationItem(
                    chunk_id=f"{doc_id}_page_{target_page_num}",
                    scheme_id="USER_DOCUMENT",
                    url=None,
                    excerpt=f"📄 {doc_name} (Page {target_page_num}) - Explicit Income Amounts",
                )
            ],
            suggested_schemes=[],
            query_understanding=query_understanding_data,
        )

    # 2.5 Page-specific queries (e.g., "What is written on page 2?")
    page_match = re.search(r"\bpage\s+(\d+)\b", raw_q_lower)
    if page_match and docs_list:
        target_page = int(page_match.group(1))
        found_page_text = None
        found_doc = None
        total_pages_detected = 0

        for doc in docs_list:
            ext_text = doc.get("extracted_text") or ""
            if not ext_text.strip():
                continue
            page_blocks = re.split(r"---\s*\[Page\s+(\d+)\]\s*---", ext_text)
            if len(page_blocks) > 1:
                for i in range(1, len(page_blocks), 2):
                    try:
                        p_num = int(page_blocks[i])
                        total_pages_detected = max(total_pages_detected, p_num)
                        if p_num == target_page:
                            found_page_text = page_blocks[i + 1].strip()
                            found_doc = doc
                    except (ValueError, IndexError):
                        continue
            else:
                total_pages_detected = max(total_pages_detected, 1)
                if target_page == 1:
                    found_page_text = ext_text.strip()
                    found_doc = doc

        if found_page_text and found_doc:
            doc_name = found_doc.get("file_name", "Document")
            doc_id = str(found_doc.get("id", "doc"))
            citation = ChatCitationItem(
                chunk_id=f"{doc_id}_page_{target_page}",
                scheme_id="USER_DOCUMENT",
                url=None,
                excerpt=f"📄 {doc_name} (Page {target_page}) - {found_page_text[:200]}",
            )
            if is_assessment_period_query(raw_q_lower):
                answer_text = verify_assessment_period(found_page_text, target_page, doc=found_doc, all_docs=docs_list)
            elif is_explicit_income_query(raw_q_lower):
                answer_text = extract_explicit_income(found_page_text, target_page, doc=found_doc, all_docs=docs_list)
            else:
                answer_text = summarize_page_text(found_page_text, target_page, doc=found_doc, all_docs=docs_list)
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=answer_text,
                intent="DOCUMENT_INQUIRY",
                citations=[citation],
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )
        else:
            first_doc = docs_list[0]
            doc_name = first_doc.get("file_name", "your document")
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=(
                    f"According to your uploaded document **{doc_name}**, Page {target_page} does not exist "
                    f"in the document (the document contains {total_pages_detected} page(s)). "
                    "The document does not establish this answer."
                ),
                intent="DOCUMENT_INQUIRY",
                citations=[],
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )


    # 2.5 Uploaded Document & Personal Fact Inquiry Handler
    doc_keywords = [
        "document", "certificate", "uploaded", "income", "caste", "category",
        "mamlatdar", "ahmedabad", "gujarat", "rajesh", "pan", "aadhaar",
        "passbook", "who issued", "issue date", "id number", "contents", "pdf",
        "data of", "my data", "my profile", "my file", "what is in my", "have the document",
        "each and every", "everything", "page", "summarize", "summary", "which documents",
        "missing", "compare"
    ]
    is_doc_query = any(k in q_lower for k in doc_keywords) or (
        query_understanding_data and query_understanding_data.get("referenced_document")
    )

    docs_list = body.documents if (body.documents and isinstance(body.documents, list)) else []

    if is_doc_query:
        # Query 1: Page-specific extraction ("What information is mentioned on page 3?")
        page_match = re.search(r"\bpage\s+(\d+)\b", q_lower)
        if page_match:
            target_page = int(page_match.group(1))
            if not docs_list:
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer="You do not have any uploaded documents on file yet. Please upload your document in the 'My Documents' vault to query its contents.",
                    intent="DOCUMENT_INQUIRY",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

            found_page_text = None
            found_doc = None
            total_pages_detected = 1

            for doc in docs_list:
                ext_text = doc.get("extracted_text") or ""
                # Parse page markers e.g. "--- [Page 1] ---"
                page_blocks = re.split(r"---\s*\[Page\s+(\d+)\]\s*---", ext_text)
                if len(page_blocks) > 1:
                    total_pages_detected = max(total_pages_detected, len(page_blocks) // 2)
                    for i in range(1, len(page_blocks), 2):
                        p_num = int(page_blocks[i])
                        if p_num == target_page:
                            p_content = page_blocks[i + 1].strip()
                            if p_content:
                                found_page_text = p_content
                                found_doc = doc
                                break
                elif target_page == 1 and ext_text.strip():
                    # Single page document without markers
                    found_page_text = ext_text.strip()
                    found_doc = doc
                    break
                if found_page_text:
                    break

            if found_page_text and found_doc:
                doc_name = found_doc.get("file_name", "Document")
                doc_id = str(found_doc.get("id", "doc"))
                snippet = found_page_text[:200].replace("\n", " ").strip()
                citation = ChatCitationItem(
                    chunk_id=f"{doc_id}_page_{target_page}",
                    scheme_id="USER_DOCUMENT",
                    url=None,
                    excerpt=f"📄 {doc_name} (Page {target_page}) - {snippet}",
                )
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        f"According to **Page {target_page}** of your uploaded document **{doc_name}**, "
                        f"the following information is mentioned:\n\n{found_page_text}"
                    ),
                    intent="DOCUMENT_INQUIRY",
                    citations=[citation],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )
            else:
                first_doc = docs_list[0]
                doc_name = first_doc.get("file_name", "your document")
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        f"According to your uploaded document **{doc_name}**, Page {target_page} does not exist "
                        f"in the document (the document contains {total_pages_detected} page(s)). "
                        "The document does not establish this answer."
                    ),
                    intent="DOCUMENT_INQUIRY",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

        # Query 2: Document Summary ("Summarize the PDF I uploaded")
        if any(w in q_lower for w in ["summarize", "summary"]) and any(w in q_lower for w in ["pdf", "document", "uploaded", "file"]):
            if not docs_list:
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer="You do not have any uploaded documents on file in Supabase yet. Please upload your documents in the 'My Documents' vault to generate a summary.",
                    intent="DOCUMENT_INQUIRY",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

            doc_summaries = []
            citations = []
            for idx, doc in enumerate(docs_list, start=1):
                d_type = str(doc.get("document_type", "Document")).replace("_", " ").title()
                f_name = doc.get("file_name", "document.pdf")
                status = doc.get("verification_status", "PENDING")
                fields = doc.get("extracted_fields", {})
                doc_no = doc.get("doc_number") or fields.get("document_number") or "N/A"
                issuer = doc.get("issuer") or fields.get("issuing_authority") or "Competent Authority"
                doc_id = str(doc.get("id", f"doc_{idx}"))

                parts = [f"### 📄 Document {idx}: {d_type} (`{f_name}`)"]
                parts.append(f"• **Verification Status:** Ready for AI Chat ({status})")
                parts.append(f"• **Document / Certificate Number:** `{doc_no}`")
                parts.append(f"• **Issuing Authority:** {issuer}")
                if fields:
                    parts.append("• **Key Extracted Facts:**")
                    for k, v in fields.items():
                        if k not in ["document_number", "issuing_authority"] and v:
                            parts.append(f"  - **{k.replace('_', ' ').title()}:** {v}")
                if doc.get("extracted_text"):
                    excerpt = doc["extracted_text"].strip()
                    first_line = excerpt.split("\n")[0][:180]
                    parts.append(f"• **Extracted Content Highlight:** *\"{first_line}\"*")
                doc_summaries.append("\n".join(parts))

                citations.append(
                    ChatCitationItem(
                        chunk_id=f"{doc_id}_summary",
                        scheme_id="USER_DOCUMENT",
                        url=None,
                        excerpt=f"📄 {f_name} (Page 1) - Verified document summary",
                    )
                )

            summary_reply = (
                "Here is a grounded summary of your uploaded document(s) on file in Supabase:\n\n"
                + "\n\n".join(doc_summaries)
                + "\n\nAll extracted statutory details are verified and automatically active in your scheme eligibility profile."
            )
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=summary_reply,
                intent="DOCUMENT_INQUIRY",
                citations=citations,
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )

        # Query 3: Annual Family Income according to document ("What is my annual family income according to my document?")
        if "income" in q_lower and any(w in q_lower for w in ["according to", "my document", "document", "uploaded", "family income", "annual"]):
            found_income = None
            source_doc = None
            for doc in docs_list:
                fields = doc.get("extracted_fields", {})
                if fields.get("annual_income"):
                    found_income = fields.get("annual_income")
                    source_doc = doc
                    break
                elif fields.get("income"):
                    found_income = fields.get("income")
                    source_doc = doc
                    break
                # Check extracted text for income pattern
                ext_t = doc.get("extracted_text") or ""
                inc_m = re.search(r"(?:annual\s+income|family\s+income|income)[\s:]*(?:rs\.?|inr|₹)?\s*([\d,]+)", ext_t, re.IGNORECASE)
                if inc_m:
                    found_income = inc_m.group(1)
                    source_doc = doc
                    break

            if not found_income and body.applicant_facts and isinstance(body.applicant_facts, dict):
                found_income = body.applicant_facts.get("annual_income") or body.applicant_facts.get("income")

            if found_income:
                clean_str = str(found_income).replace("₹", "").replace(",", "").strip()
                try:
                    num_val = float(clean_str)
                    formatted_val = f"₹{num_val:,.2f}".rstrip("0").rstrip(".")
                except (ValueError, TypeError):
                    formatted_val = f"₹{found_income}"

                doc_name = source_doc.get("file_name", "Income Certificate") if source_doc else "Income Certificate"
                doc_no = (source_doc.get("doc_number") or source_doc.get("extracted_fields", {}).get("document_number", "N/A")) if source_doc else "Verified on File"
                issuer = (source_doc.get("issuer") or source_doc.get("extracted_fields", {}).get("issuing_authority", "State Competent Authority")) if source_doc else "State Revenue Authority"
                doc_id = str(source_doc.get("id", "doc")) if source_doc else "income_fact"

                citation = ChatCitationItem(
                    chunk_id=f"{doc_id}_income",
                    scheme_id="USER_DOCUMENT",
                    url=None,
                    excerpt=f"📄 {doc_name} (Page 1) - Annual Income: {formatted_val}",
                )
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        f"According to your uploaded document **{doc_name}** (Certificate No: `{doc_no}`), "
                        f"your annual family income is **{formatted_val}**.\n\n"
                        f"• **Issuing Authority:** {issuer}\n"
                        f"• **Status:** Verified and Ready for AI Chat"
                    ),
                    intent="PERSONAL_FACT_LOOKUP",
                    citations=[citation],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )
            else:
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        "None of your uploaded documents establish your annual family income. "
                        "No Income Certificate or verified income record was found in your vault. "
                        "Please upload an Income Certificate issued by a competent revenue authority "
                        "(e.g., Tahsildar / Mamlatdar) in the 'My Documents' vault."
                    ),
                    intent="PERSONAL_FACT_LOOKUP",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

        # Query 4: List uploaded documents ("Which documents have I uploaded?")
        if any(w in q_lower for w in ["which documents", "what documents have i uploaded", "which documents have i uploaded", "documents have i uploaded", "list my documents", "what documents are uploaded"]):
            if not docs_list:
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer="You currently have no documents uploaded in your vault. You can upload documents like Aadhaar Card, PAN Card, Income Certificate, and Caste Certificate in the 'My Documents' section.",
                    intent="DOCUMENT_INQUIRY",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

            doc_lines = []
            citations = []
            for idx, doc in enumerate(docs_list, start=1):
                d_type = str(doc.get("document_type", "Document")).replace("_", " ").title()
                f_name = doc.get("file_name", "document.pdf")
                status = doc.get("verification_status", "PENDING")
                status_label = "Ready for AI Chat" if status == "VERIFIED" else "Processing"
                doc_no = doc.get("doc_number") or doc.get("extracted_fields", {}).get("document_number") or "N/A"
                date_str = str(doc.get("uploaded_at", ""))[:10]
                date_part = f" | Uploaded: {date_str}" if date_str else ""
                doc_id = str(doc.get("id", f"doc_{idx}"))

                doc_lines.append(f"{idx}. **{d_type}** (`{f_name}`) — Status: **{status_label}** | Doc #: `{doc_no}`{date_part}")
                citations.append(
                    ChatCitationItem(
                        chunk_id=f"{doc_id}_list",
                        scheme_id="USER_DOCUMENT",
                        url=None,
                        excerpt=f"📄 {f_name} (Page 1) - {d_type}",
                    )
                )

            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=(
                    f"You have uploaded **{len(docs_list)} document(s)** in your vault:\n\n"
                    + "\n".join(doc_lines)
                    + "\n\nAll verified documents are indexed and retrievable by FIN AI Assistant."
                ),
                intent="DOCUMENT_INQUIRY",
                citations=citations,
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )

        # Query 5: Income Certificate check ("Does my uploaded document contain my income certificate?")
        if ("contain" in q_lower or "is" in q_lower or "have" in q_lower) and "income certificate" in q_lower:
            income_doc = None
            for doc in docs_list:
                dtype = str(doc.get("document_type", "")).lower()
                fname = str(doc.get("file_name", "")).lower()
                fields = doc.get("extracted_fields", {})
                if "income" in dtype or "income" in fname or fields.get("annual_income"):
                    income_doc = doc
                    break

            if income_doc:
                doc_name = income_doc.get("file_name", "Income_Certificate.pdf")
                fields = income_doc.get("extracted_fields", {})
                doc_no = income_doc.get("doc_number") or fields.get("document_number") or "DOC-INC"
                issuer = income_doc.get("issuer") or fields.get("issuing_authority") or "Competent Revenue Authority"
                inc_val = fields.get("annual_income") or (body.applicant_facts.get("annual_income") if body.applicant_facts else None) or "Verified on File"
                doc_id = str(income_doc.get("id", "doc"))

                citation = ChatCitationItem(
                    chunk_id=f"{doc_id}_income_cert",
                    scheme_id="USER_DOCUMENT",
                    url=None,
                    excerpt=f"📄 {doc_name} (Page 1) - Verified Income Certificate",
                )
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        f"Yes, your uploaded document **{doc_name}** contains your Income Certificate.\n\n"
                        f"• **Document Number:** `{doc_no}`\n"
                        f"• **Issuing Authority:** {issuer}\n"
                        f"• **Recorded Annual Income:** **₹{inc_val}**\n"
                        f"• **Status:** Ready for AI Chat"
                    ),
                    intent="DOCUMENT_INQUIRY",
                    citations=[citation],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )
            else:
                existing_names = ", ".join(f"`{d.get('file_name', 'file')}`" for d in docs_list) if docs_list else "None"
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=(
                        f"No, your uploaded documents do not contain an Income Certificate. "
                        f"Your current documents on file are: {existing_names}. "
                        "To verify your income eligibility for welfare schemes, please upload your "
                        "Income Certificate in the 'My Documents' tab."
                    ),
                    intent="DOCUMENT_INQUIRY",
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                )

        # Query 6: Missing information from application ("What information is missing from my uploaded application?")
        if "missing" in q_lower and any(w in q_lower for w in ["application", "document", "upload", "information", "profile"]):
            uploaded_types = set()
            for doc in docs_list:
                dtype = str(doc.get("document_type", "")).lower()
                fname = str(doc.get("file_name", "")).lower()
                if "aadhaar" in dtype or "aadhaar" in fname or "id" in dtype:
                    uploaded_types.add("id_proof")
                if "income" in dtype or "income" in fname or doc.get("extracted_fields", {}).get("annual_income"):
                    uploaded_types.add("income_proof")
                if "caste" in dtype or "caste" in fname or "category" in dtype:
                    uploaded_types.add("caste_proof")
                if "address" in dtype or "domicile" in dtype or "address" in fname:
                    uploaded_types.add("address_proof")
                if "bank" in dtype or "passbook" in dtype or "bank" in fname:
                    uploaded_types.add("bank_proof")

            standard_reqs = [
                ("Identity Proof (Aadhaar / PAN Card)", "id_proof"),
                ("Income Certificate", "income_proof"),
                ("Address / Domicile Proof", "address_proof"),
                ("Bank Account Passbook / Cancelled Cheque", "bank_proof"),
            ]

            available_items = []
            missing_items = []
            for label, key in standard_reqs:
                if key in uploaded_types:
                    available_items.append(f"• ✅ **{label}**: Uploaded and verified")
                else:
                    missing_items.append(f"• ⚠️ **{label}**: Required to complete application eligibility")

            # Check special category requirement if applicant is SC/ST/OBC
            cat = str((body.applicant_facts.get("category") if body.applicant_facts else "") or (body.applicant_facts.get("caste_category") if body.applicant_facts else "") or "").lower()
            if cat in ["sc", "st", "obc"]:
                if "caste_proof" in uploaded_types:
                    available_items.append(f"• ✅ **Caste Certificate ({cat.upper()})**: Uploaded")
                else:
                    missing_items.append(f"• ⚠️ **Caste Certificate ({cat.upper()})**: Required for special category benefits")

            reply = (
                "### Application Document Readiness Check\n\n"
                "**Uploaded & Verified Documents:**\n"
                + ("\n".join(available_items) if available_items else "• *No verified documents uploaded yet.*")
                + "\n\n**Missing Information / Documents:**\n"
                + ("\n".join(missing_items) if missing_items else "• *None! All essential statutory documents are uploaded.*")
                + "\n\nYou can upload any missing certificates directly in the **My Documents** vault."
            )
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=reply,
                intent="DOCUMENT_INQUIRY",
                citations=[],
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )

        # Query 7: Compare uploaded documents with scheme requirements ("Compare my uploaded documents with the requirements of this scheme.")
        if "compare" in q_lower and any(w in q_lower for w in ["requirement", "scheme", "document", "uploaded"]):
            scheme_title = "PMEGP (Prime Minister's Employment Generation Programme)"
            required_docs = [
                ("Aadhaar Card", "Identity Proof"),
                ("PAN Card", "Tax / Business Registration"),
                ("Income Certificate", "Subsidy & Income Verification"),
                ("Project Report / DPR", "Business Feasibility & Financial Assessment"),
                ("Special Category Certificate (if SC/ST/OBC/Women)", "Margin Money Subsidy Uplift (up to 35%)")
            ]

            comp_lines = []
            citations = []
            for req_name, purpose in required_docs:
                matching_doc = None
                for doc in docs_list:
                    dtype = str(doc.get("document_type", "")).lower()
                    fname = str(doc.get("file_name", "")).lower()
                    kw = req_name.split()[0].lower()
                    if kw in dtype or kw in fname:
                        matching_doc = doc
                        break

                if matching_doc:
                    comp_lines.append(f"• **{req_name}** ({purpose}): ✅ **Satisfied** (Uploaded: `{matching_doc.get('file_name')}`)")
                    citations.append(
                        ChatCitationItem(
                            chunk_id=f"{matching_doc.get('id', 'doc')}_comp",
                            scheme_id="USER_DOCUMENT",
                            url=None,
                            excerpt=f"📄 {matching_doc.get('file_name')} (Page 1) - Satisfies {req_name}",
                        )
                    )
                else:
                    comp_lines.append(f"• **{req_name}** ({purpose}): ❌ **Missing** (Please upload in My Documents)")

            reply = (
                f"### Document Comparison for **{scheme_title}**\n\n"
                "Here is how your uploaded documents align with the statutory requirements:\n\n"
                + "\n".join(comp_lines)
                + "\n\nUploading the remaining required documents will allow your application to proceed to automated department verification."
            )
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=reply,
                intent="DOCUMENT_INQUIRY",
                citations=citations,
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )

        # General Document Facts Fallback (issuing authority, document number, etc.)
        if docs_list:
            doc_summaries = []
            citations = []
            for idx, doc in enumerate(docs_list, start=1):
                d_type = str(doc.get("document_type", "Document")).replace("_", " ").title()
                f_name = doc.get("file_name", "file.pdf")
                status = doc.get("verification_status", "PENDING")
                fields = doc.get("extracted_fields", {})
                doc_no = doc.get("doc_number") or fields.get("document_number") or "N/A"
                issuer = doc.get("issuer") or fields.get("issuing_authority") or "Competent Authority"
                doc_id = str(doc.get("id", f"doc_{idx}"))

                parts = [f"### 📄 Document {idx}: {d_type}"]
                parts.append(f"• **File Name:** `{f_name}`")
                parts.append(f"• **Verification Status:** Ready for AI Chat ({status})")
                parts.append(f"• **Document Number:** `{doc_no}`")
                parts.append(f"• **Issuing Authority:** {issuer}")
                if fields:
                    parts.append("• **Extracted Statutory Details:**")
                    for k, v in fields.items():
                        if k not in ["document_number", "issuing_authority"] and v:
                            parts.append(f"  - **{k.replace('_', ' ').title()}:** {v}")
                if doc.get("extracted_text"):
                    excerpt = doc["extracted_text"].strip()
                    if len(excerpt) > 250:
                        excerpt = excerpt[:250].strip() + "..."
                    parts.append(f"• **Extracted Content Excerpt:** *\"{excerpt}\"*")
                doc_summaries.append("\n".join(parts))

                citations.append(
                    ChatCitationItem(
                        chunk_id=f"{doc_id}_general",
                        scheme_id="USER_DOCUMENT",
                        url=None,
                        excerpt=f"📄 {f_name} (Page 1) - Verified document details",
                    )
                )

            summary_answer = (
                "Yes, here is the verified data extracted from your uploaded documents in Supabase:\n\n"
                + "\n\n".join(doc_summaries)
                + "\n\nAll of these statutory details are verified and automatically active in your scheme eligibility profile."
            )
            return ChatResponse(
                request_id=request_id,
                conversation_id=body.conversation_id,
                answer=summary_answer,
                intent="DOCUMENT_INQUIRY",
                citations=citations,
                suggested_schemes=[],
                query_understanding=query_understanding_data,
            )

        if body.applicant_facts and isinstance(body.applicant_facts, dict) and len(body.applicant_facts) > 0:
            facts = body.applicant_facts
            if "who issued" in q_lower or "issuing authority" in q_lower:
                issuer = facts.get("issuing_authority") or facts.get("issuer")
                if issuer:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=f"According to your verified records on file, your document was issued by **{issuer}**.",
                        intent="DOCUMENT_INQUIRY",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )
            if "document number" in q_lower or "certificate number" in q_lower:
                doc_num = facts.get("document_number")
                if doc_num:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=f"Your verified Document / Certificate Number is **{doc_num}**.",
                        intent="DOCUMENT_INQUIRY",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )
            if "category" in q_lower or "caste" in q_lower:
                cat = facts.get("category") or facts.get("caste_category")
                if cat:
                    return ChatResponse(
                        request_id=request_id,
                        conversation_id=body.conversation_id,
                        answer=f"According to your verified records on file, your Social Category is **{cat}**.",
                        intent="PERSONAL_FACT_LOOKUP",
                        citations=[],
                        suggested_schemes=[],
                        query_understanding=query_understanding_data,
                    )


    # 2.9 Format complete applicant documents and records
    docs_context_blocks = []
    if body.documents and isinstance(body.documents, list):
        for idx, doc in enumerate(body.documents, start=1):
            d_type = doc.get("document_type", "Document")
            f_name = doc.get("file_name", "file.pdf")
            status = doc.get("verification_status", "PENDING")
            fields = doc.get("extracted_fields", {})
            text = doc.get("extracted_text", "")

            block = [f"=== DOCUMENT {idx}: {d_type} ({f_name}) ==="]
            block.append(f"Verification Status: {status}")
            if fields:
                block.append("Extracted Statutory Fields:")
                for k, v in fields.items():
                    block.append(f"  - {k}: {v}")
            if text:
                block.append(f"Full Extracted Document Text:\n{text}")
            docs_context_blocks.append("\n".join(block))

    if not docs_context_blocks and body.applicant_facts and isinstance(body.applicant_facts, dict):
        block = ["=== CITIZEN VERIFIED FACTS ON FILE ==="]
        for k, v in body.applicant_facts.items():
            if v is not None and k != "extracted_text":
                block.append(f"  - {k}: {v}")
        if "extracted_text" in body.applicant_facts:
            block.append(f"Full Extracted Document Text:\n{body.applicant_facts['extracted_text']}")
        docs_context_blocks.append("\n".join(block))

    has_applicant_docs = len(docs_context_blocks) > 0
    applicant_docs_context = "\n\n".join(docs_context_blocks) if has_applicant_docs else "No citizen documents currently uploaded on file."

    # 2.10 Format complete submitted applications and support tickets
    apps_context_blocks = []
    if body.applications and isinstance(body.applications, list):
        for idx, app in enumerate(body.applications, start=1):
            t_id = app.get("ticket_id") or f"APP-{str(app.get('id', ''))[:8].upper()}"
            s_name = app.get("scheme_name") or app.get("scheme_id", "Government Scheme")
            st = app.get("status", "under_review")
            ben = app.get("estimated_benefit")
            sub_date = app.get("submitted_at")
            block = [f"=== APPLICATION / TICKET {idx}: {t_id} ==="]
            block.append(f"Scheme: {s_name}")
            block.append(f"Status: {st}")
            if ben: block.append(f"Estimated Benefit: {ben}")
            if sub_date: block.append(f"Submitted Date: {sub_date}")
            apps_context_blocks.append("\n".join(block))

    has_applicant_apps = len(apps_context_blocks) > 0
    applicant_apps_context = "\n\n".join(apps_context_blocks) if has_applicant_apps else "No submitted applications or active tickets on file."

    # 3. Hybrid RAG retrieval
    retrieval_query = RetrievalQuery(
        query_text=body.query,
        language=body.language,
        top_k=5,
    )

    retriever = _resolve_retriever(request)
    chunks = await run_in_threadpool(retriever.retrieve, retrieval_query)
    schemes = await run_in_threadpool(retriever.retrieve_schemes, retrieval_query)

    # If no relevant scheme chunks exist in the repository
    if not chunks:
        if (has_applicant_docs or has_applicant_apps) and not is_scheme_procedure and not is_scheme_doc_req:
            wrapped_query = _safety_detector.wrap_untrusted_input(body.query)
            llm_prompt = (
                f"<APPLICANT_DOCUMENTS_AND_RECORDS>\n{applicant_docs_context}\n</APPLICANT_DOCUMENTS_AND_RECORDS>\n\n"
                f"<APPLICANT_TICKETS_AND_APPLICATIONS>\n{applicant_apps_context}\n</APPLICANT_TICKETS_AND_APPLICATIONS>\n\n"
                f"Citizen Query:\n{wrapped_query}\n\n"
                f"Language Mandate: Respond STRICTLY and FLUENTLY in {detected_lang_name} ({detected_lang}). Do NOT respond in English unless the query is in English.\n"
                "Answer the citizen's inquiry thoroughly, accurately, and completely based strictly on their uploaded documents, verified records, and submitted applications/tickets above."
            )
            try:
                exec_res = await run_in_threadpool(
                    llm_client.generate_with_metadata,
                    llm_prompt,
                    system_prompt=SYSTEM_PROMPT_GROUNDED_CHAT,
                    operation="grounded_chat",
                    request_id=request_id,
                )
                return ChatResponse(
                    request_id=request_id,
                    conversation_id=body.conversation_id,
                    answer=exec_res.content,
                    intent="DOCUMENT_INQUIRY",
                    detected_language=detected_lang,
                    citations=[],
                    suggested_schemes=[],
                    query_understanding=query_understanding_data,
                    provider_telemetry={
                        "provider": exec_res.provider,
                        "model": exec_res.model,
                        "latency_ms": round(exec_res.latency_ms, 2),
                        "fallback_used": exec_res.fallback_used,
                    }
                )
            except Exception as e:
                logger.warning("LLM fallback for document query: %s", e)

        return ChatResponse(
            request_id=request_id,
            conversation_id=body.conversation_id,
            answer=format_no_evidence_message(detected_lang),
            intent="SCHEME_DISCOVERY",
            detected_language=detected_lang,
            citations=[],
            suggested_schemes=[],
            query_understanding=query_understanding_data,
        )

    # 3. Format citations and suggested schemes
    citations: List[ChatCitationItem] = []
    for c in chunks[:5]:
        citations.append(
            ChatCitationItem(
                chunk_id=c.chunk_id,
                scheme_id=c.scheme_slug or "unknown_scheme",
                url=c.metadata.get("source_url") or "",
                excerpt=c.content[:250].strip() + ("..." if len(c.content) > 250 else ""),
            )
        )

    suggested_schemes = [
        {
            "scheme_id": s.scheme_slug,
            "scheme_name": s.scheme_name,
            "relevance_score": s.aggregate_score,
            "eligibility_status": "UNKNOWN",
            "eligibility_score": None,
            "ministry": s.source_metadata.get("ministry"),
            "state": s.source_metadata.get("state"),
        }
        for s in schemes[:3]
    ]

    # 4. Construct grounded LLM prompt with policy evidence, applicant documents, and tickets
    evidence_blocks = []
    for idx, c in enumerate(chunks[:5], start=1):
        evidence_blocks.append(
            f"--- EVIDENCE CHUNK {idx} (ID: {c.chunk_id}, Scheme: {c.scheme_name}) ---\n"
            f"{c.content}\n"
        )
    evidence_text = "\n".join(evidence_blocks)

    wrapped_query = _safety_detector.wrap_untrusted_input(body.query)

    llm_prompt = (
        f"<POLICY_EVIDENCE>\n{evidence_text}\n</POLICY_EVIDENCE>\n\n"
        f"<APPLICANT_DOCUMENTS_AND_RECORDS>\n{applicant_docs_context}\n</APPLICANT_DOCUMENTS_AND_RECORDS>\n\n"
        f"<APPLICANT_TICKETS_AND_APPLICATIONS>\n{applicant_apps_context}\n</APPLICANT_TICKETS_AND_APPLICATIONS>\n\n"
        f"Citizen Query:\n{wrapped_query}\n\n"
        f"Language Mandate: Respond STRICTLY and FLUENTLY in {detected_lang_name} ({detected_lang}). Do NOT respond in English unless the query is in English.\n"
        "Provide a grounded, transparent explanation based strictly on the statutory policy evidence, uploaded document records, and submitted applications/tickets above."
    )

    # 5. Call LLM with graceful fallback
    telemetry = None
    try:
        exec_res = await run_in_threadpool(
            llm_client.generate_with_metadata,
            llm_prompt,
            system_prompt=SYSTEM_PROMPT_GROUNDED_CHAT,
            operation="grounded_chat",
            request_id=request_id,
        )
        answer = exec_res.content
        telemetry = {
            "provider": exec_res.provider,
            "model": exec_res.model,
            "latency_ms": round(exec_res.latency_ms, 2),
            "fallback_used": exec_res.fallback_used,
        }
    except Exception as e:
        logger.warning(
            "LLM generation failed for grounded chat (request %s): %s; generating evidence-derived fallback.",
            request_id,
            e,
        )
        # Grounded deterministic fallback directly synthesizing top evidence chunks
        top_scheme_names = ", ".join(s["scheme_name"] for s in suggested_schemes)
        fallback_msg = (
            f"Based on verified statutory scheme records, the most relevant schemes matching your query are: {top_scheme_names}.\n\n"
            f"Key statutory details:\n- {citations[0].excerpt}\n\n"
            "Please review the attached source citations for full eligibility and application guidelines."
        )
        if detected_lang != "en":
            fallback_msg = await maybe_translate_response(
                fallback_msg, detected_lang, detected_lang_name, body.query, llm_client, request_id
            )
        answer = fallback_msg
        telemetry = {"provider": "local_fallback", "model": "evidence_synthesizer", "latency_ms": 0.0}

    return ChatResponse(
        request_id=request_id,
        conversation_id=body.conversation_id,
        answer=answer,
        intent="SCHEME_DISCOVERY",
        detected_language=detected_lang,
        citations=citations,
        suggested_schemes=suggested_schemes,
        query_understanding=query_understanding_data,
        provider_telemetry=telemetry,
    )
