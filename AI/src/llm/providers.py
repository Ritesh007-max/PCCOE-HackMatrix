"""
PolicySetu LLM Provider Abstraction Layer.
Provides a pluggable interface for language models.
Includes MockLLMProvider (offline, deterministic, rule-assisted) and OpenAICompatibleProvider.
CRITICAL INVARIANT: Production provider failure MUST NOT silently fall back to Mock.
"""

from abc import ABC, abstractmethod
import json
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Type, TypeVar
import sys
from pathlib import Path

# Ensure AI directory is on sys.path
_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

try:
    from .models import (
        QueryIntent,
        ApplicantFactCandidate,
        FactExtractionResult,
        GroundedExplanation,
        FactualClaim,
        UserIntent,
        ExtractionConfidence,
        ClaimSupportStatus,
    )
    from .config import LLMConfig
    from .errors import (
        ProviderUnavailableError,
        ProviderTimeoutError,
        MalformedOutputError,
        SchemaValidationError,
    )
    from .structured_output import parse_structured_json, validate_and_instantiate
    from ..extraction.models import FactVerificationStatus, CANONICAL_PROFILE_FIELDS
except (ImportError, ValueError):
    from src.llm.models import (
        QueryIntent,
        ApplicantFactCandidate,
        FactExtractionResult,
        GroundedExplanation,
        FactualClaim,
        UserIntent,
        ExtractionConfidence,
        ClaimSupportStatus,
    )
    from src.llm.config import LLMConfig
    from src.llm.errors import (
        ProviderUnavailableError,
        ProviderTimeoutError,
        MalformedOutputError,
        SchemaValidationError,
    )
    from src.llm.structured_output import parse_structured_json, validate_and_instantiate
    from src.extraction.models import FactVerificationStatus, CANONICAL_PROFILE_FIELDS

T = TypeVar("T")


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider service."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the underlying model."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if provider service is reachable / configured."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generates raw text response."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> T:
        """Generates and validates structured output conforming to schema_cls."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Deterministic, rule-and-regex-assisted LLM provider for 100% offline testing.
    Processes English, Hindi, and Hinglish queries into structured schemas
    without external API calls or network connectivity.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        super().__init__(config or LLMConfig(provider="mock"))
        try:
            from ..nlp.language import LanguageDetector
            from ..nlp.intent import IntentClassifier
            from ..nlp.query_parser import QueryParser
            from ..nlp.ambiguity import AmbiguityDetector
        except (ImportError, ValueError):
            from src.nlp.language import LanguageDetector
            from src.nlp.intent import IntentClassifier
            from src.nlp.query_parser import QueryParser
            from src.nlp.ambiguity import AmbiguityDetector

        self.language_detector = LanguageDetector()
        self.intent_classifier = IntentClassifier()
        self.query_parser = QueryParser()
        self.ambiguity_detector = AmbiguityDetector()

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self.config.model

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        return f"Mock response for prompt length {len(prompt)}"

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> T:
        """Deterministically parses prompt into structured schemas."""
        if schema_cls == QueryIntent:
            return self._build_query_intent(prompt)  # type: ignore
        elif schema_cls == FactExtractionResult:
            return self._build_fact_extraction(prompt)  # type: ignore
        elif schema_cls == GroundedExplanation:
            return self._build_grounded_explanation(prompt, kwargs)  # type: ignore
        else:
            raise SchemaValidationError(f"MockLLMProvider does not support schema: {schema_cls.__name__}")

    def _build_query_intent(self, text: str) -> QueryIntent:
        lang_res = self.language_detector.detect(text)
        primary, secondary, conf = self.intent_classifier.classify_intent(text)
        hints = self.query_parser.extract_search_hints(text)
        ambiguities = self.ambiguity_detector.detect_ambiguities(text)

        return QueryIntent(
            original_query=text,
            normalized_query=text.strip().lower(),
            language=lang_res.language,
            intent=primary,
            secondary_intent=secondary,
            state=hints["state"],
            social_category=hints["social_category"],
            beneficiary_type=hints["beneficiary_type"],
            policy_domain=hints["policy_domain"],
            benefit_type=hints.get("benefit_type"),
            keywords=hints["keywords"],
            confidence=conf,
            ambiguities=ambiguities,
            is_search_hint_only=True,
        )

    def _build_fact_extraction(self, text: str) -> FactExtractionResult:
        facts: List[ApplicantFactCandidate] = []
        ambiguities = self.ambiguity_detector.detect_ambiguities(text)
        raw = text.strip()

        # 1. Age extraction
        age_match = re.search(
            r"\b(?:age\s*(?:is|=|:)?\s*|उम्र\s*|meri\s+age\s*(?:is|=|:)?\s*)(\d{1,3})\b|"
            r"\b(\d{1,3}\s*years?)(?:\s*old)?\b|"
            r"\b(\d{1,3})\s*(?:saal|साल|वर्ष)\b",
            raw,
            re.IGNORECASE
        )
        if age_match:
            val = age_match.group(1) or age_match.group(2) or age_match.group(3)
            facts.append(
                ApplicantFactCandidate(
                    field="age",
                    raw_value=val,
                    data_type="numeric",
                    confidence=0.95,
                    evidence_text=age_match.group(0),
                    suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                )
            )

        # 2. State extraction (first-person only!)
        if self.query_parser.is_self_declaration(raw) or re.search(r"\b(from|rehta|rehti|live\s+in|resident\s+of)\b", raw, re.IGNORECASE):
            hints = self.query_parser.extract_search_hints(raw)
            if hints["state"]:
                facts.append(
                    ApplicantFactCandidate(
                        field="state",
                        raw_value=hints["state"],
                        data_type="string",
                        confidence=0.90,
                        evidence_text=hints["state"],
                        suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                    )
                )

        # 3. Income extraction
        income_match = re.search(
            r"(?:income\s*(?:is|=|:)?\s*|आय\s*|aay\s*|earns?\s*|कमाई\s*|family\s+income\s*(?:is|=|:)?\s*)"
            r"([₹\d\.,\s]+(?:\s*(?:lakh|lakhs|lac|crore|k|thousand|लाख|रुपये|rupaye|rs))?)",
            raw,
            re.IGNORECASE
        )
        if income_match:
            val_str = income_match.group(1).strip()
            # If val_str has digits, create fact candidate
            if re.search(r"\d", val_str):
                facts.append(
                    ApplicantFactCandidate(
                        field="annual_family_income",
                        raw_value=val_str,
                        data_type="numeric",
                        confidence=0.90,
                        evidence_text=income_match.group(0),
                        suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                    )
                )

        # 4. Social Category extraction (first-person declaration only)
        if re.search(r"\b(?:i\s+am\s+(?:an?\s+)?|my\s+(?:social\s+)?category\s+is\s+|belong\s+to\s+(?:the\s+)?|caste\s*:\s*|category\s*:\s*|main\s+[a-z\u0900-\u097F]+\s+(?:se|hoon)|मेरी\s+जाति\s*|mera\s+caste\s*)\b", raw, re.IGNORECASE) or (self.query_parser.is_self_declaration(raw) and re.search(r"\b(certificate|category|caste|जाति|वर्ग)\b", raw, re.IGNORECASE)):
            hints = self.query_parser.extract_search_hints(raw)
            if hints["social_category"]:
                facts.append(
                    ApplicantFactCandidate(
                        field="social_category",
                        raw_value=hints["social_category"],
                        data_type="string",
                        confidence=0.90,
                        evidence_text=hints["social_category"],
                        suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                    )
                )

        # 5. Landholding extraction
        land_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:acres?|hectares?|bigha|guntha|एकड़|हेक्टेयर)",
            raw,
            re.IGNORECASE
        )
        if land_match:
            facts.append(
                ApplicantFactCandidate(
                    field="landholding_hectares",
                    raw_value=land_match.group(0),
                    data_type="numeric",
                    confidence=0.90,
                    evidence_text=land_match.group(0),
                    suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                )
            )

        # 6. Occupation extraction
        occ_match = re.search(
            r"\b(?:i\s+am\s+a\s+|main\s+|hoon\s+)?(farmer|kisan|artisan|weaver|laborer|driver|teacher)\b|"
            r"(किसान|कारीगर|मजदूर)",
            raw,
            re.IGNORECASE
        )
        if occ_match and self.query_parser.is_self_declaration(raw):
            val = occ_match.group(1) or occ_match.group(2)
            facts.append(
                ApplicantFactCandidate(
                    field="occupation",
                    raw_value="farmer" if val in ("farmer", "kisan", "किसान") else val,
                    data_type="string",
                    confidence=0.90,
                    evidence_text=occ_match.group(0),
                    suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                )
            )

        return FactExtractionResult(
            facts=facts,
            candidate_missing_fields=[],
            ambiguities=ambiguities,
            extraction_confidence=ExtractionConfidence.HIGH if facts else ExtractionConfidence.MEDIUM,
            source_text=raw,
        )

    def _build_grounded_explanation(self, prompt: str, kwargs: Dict[str, Any]) -> GroundedExplanation:
        status_val = kwargs.get("authoritative_decision", "UNKNOWN")
        scheme_id = kwargs.get("scheme_id", "scheme_default")
        retrieved_chunks = kwargs.get("retrieved_chunks", [])
        
        chunk_ids = [c.get("id") or c.get("chunk_id") for c in retrieved_chunks if c.get("id") or c.get("chunk_id")]
        urls = [c.get("source_url") for c in retrieved_chunks if c.get("source_url")]

        claims = []
        if chunk_ids:
            claims.append(
                FactualClaim(
                    statement=f"Statutory criteria according to official policy documentation.",
                    cited_chunk_ids=chunk_ids[:2],
                    cited_urls=urls[:2],
                    support_status=ClaimSupportStatus.SUPPORTED,
                    support_score=0.85,
                )
            )

        answer = (
            f"Statutory evaluation for scheme '{scheme_id}' returned {status_val}. "
            f"All findings are grounded strictly in retrieved official documentation."
        )

        return GroundedExplanation(
            authoritative_decision=status_val,
            scheme_id=scheme_id,
            answer=answer,
            claims=claims,
            supporting_chunk_ids=chunk_ids[:3],
            supporting_source_urls=urls[:3],
            passed_rules=kwargs.get("passed_rules", []),
            failed_rules=kwargs.get("failed_rules", []),
            missing_fields=kwargs.get("missing_fields", []),
            conflicted_fields=kwargs.get("conflicted_fields", []),
            review_required=status_val == "REVIEW",
        )


class OpenAICompatibleProvider(LLMProvider):
    """
    Production OpenAI-compatible API provider (supports OpenAI, vLLM, Ollama, etc.).
    CRITICAL INVARIANT: On network or HTTP error, raises explicit exceptions;
    NEVER silently falls back to MockLLMProvider.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_base = (config.api_base or "https://api.openai.com/v1").rstrip("/")
        self.api_key = config.api_key

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.config.model

    def is_available(self) -> bool:
        return bool(self.api_key or "localhost" in self.api_base or "127.0.0.1" in self.api_base)

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        if not self.is_available():
            raise ProviderUnavailableError("OpenAI API key or reachable endpoint is not configured.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=data_bytes,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            raise ProviderUnavailableError(f"OpenAI API HTTP Error {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            if "timed out" in str(exc.reason).lower():
                raise ProviderTimeoutError(f"OpenAI API request timed out after {self.config.timeout_seconds}s") from exc
            raise ProviderUnavailableError(f"Failed to reach OpenAI API: {exc.reason}") from exc
        except Exception as exc:
            raise ProviderUnavailableError(f"Unexpected error communicating with LLM provider: {exc}") from exc

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> T:
        """Generates structured response by instructing JSON format and validating."""
        json_instruction = (
            f"\nYou must output your response STRICTLY as a valid JSON object conforming to "
            f"the {schema_cls.__name__} schema. Do not enclose in anything other than ```json ```."
        )
        full_prompt = prompt + "\n" + json_instruction
        raw_output = self.generate(full_prompt, system_prompt=system_prompt, **kwargs)
        parsed_dict = parse_structured_json(raw_output)
        return validate_and_instantiate(parsed_dict, schema_cls)


def get_llm_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """Factory function for instantiating the configured LLM provider."""
    cfg = config or LLMConfig.from_env()
    provider_type = cfg.provider.strip().lower()

    if provider_type == "mock":
        return MockLLMProvider(cfg)
    elif provider_type == "openai":
        return OpenAICompatibleProvider(cfg)
    else:
        raise ValueError(f"Unsupported LLM provider: '{cfg.provider}'. Supported: 'mock', 'openai'")
