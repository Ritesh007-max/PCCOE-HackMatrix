# Phase 11: Multilingual Guidance & Localization

## 1. Supported Languages

FIN Phase 11 supports three distinct linguistic representations:
1. **English (`en`)**
2. **Hindi (`hi`)**
3. **Hinglish (`hinglish`)**

Language detection leverages the Phase 6 query understanding pipeline or explicit parameter specification.

---

## 2. Machine Stability Contract

Regardless of the target language, **statutory machine identifiers remain strictly unmutated**:
- `application_id`: Unaltered (e.g. `app_e2a39fd84c71`)
- `scheme_id`: Unaltered (e.g. `sc_post_matric_scholarship`)
- `rule_id`: Unaltered (e.g. `rule_sc_01`)
- `document_type`: Unaltered (e.g. `income_certificate`)
- `action_type`: Unaltered (e.g. `UPLOAD_DOCUMENT`)
- `official_portal_url`: Unaltered URL

---

## 3. Localization Examples

### Action Titles:
- **English**: "Upload your caste certificate."
- **Hindi**: "अपना जाति प्रमाण पत्र अपलोड करें।"
- **Hinglish**: "Apna caste certificate upload karein."

### Eligibility Summaries:
- **English**: "Your available profile information and verified documents satisfy the evaluated statutory eligibility criteria."
- **Hindi**: "आपकी प्रोफ़ाइल इस योजना के मूल्यांकन किए गए पात्रता मानदंडों को पूरा करती है।"
- **Hinglish**: "Aapki profile is scheme ke evaluated eligibility criteria ko satisfy karti hai."
