"""
PolicySetu LLM Provider Layer.
Implements Google Gemini (Primary), OpenRouter (Fallback), and MockLLMProvider (Offline).
Strictly classifies operational failures vs authentication/configuration errors.
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
_CUR = Path(__file__).resolve()
while _CUR.name != "AI" and _CUR.parent != _CUR:
    _CUR = _CUR.parent
_AI_DIR = _CUR
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
        ProviderRateLimitError,
        ProviderNetworkError,
        ProviderAuthenticationError,
        ProviderConfigurationError,
        ProviderInvalidResponseError,
        ProviderStructuredOutputError,
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
        ProviderRateLimitError,
        ProviderNetworkError,
        ProviderAuthenticationError,
        ProviderConfigurationError,
        ProviderInvalidResponseError,
        ProviderStructuredOutputError,
        MalformedOutputError,
        SchemaValidationError,
    )
    from src.llm.structured_output import parse_structured_json, validate_and_instantiate
    from src.extraction.models import FactVerificationStatus, CANONICAL_PROFILE_FIELDS

T = TypeVar("T")


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

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


class GeminiProvider(LLMProvider):
    """
    Primary Provider: Google Gemini API via the official `google-genai` SDK.
    Used for multimodal document understanding, structured candidate fact extraction,
    and grounded policy explanations.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.gemini_api_key or config.api_key
        self._model = config.gemini_model or "gemini-2.5-flash"
        self._client = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _get_client(self):
        if not self.is_available():
            raise ProviderConfigurationError("Gemini API key is not configured. Set GEMINI_API_KEY.")
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                raise ProviderConfigurationError(f"Failed to initialize google-genai client: {exc}") from exc
        return self._client

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        client = self._get_client()
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                system_instruction=system_prompt if system_prompt else None,
            )
            resp = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            if not resp or not resp.text:
                raise ProviderInvalidResponseError("Gemini returned an empty response.")
            return resp.text.strip()
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            self._translate_and_raise_error(exc)
            raise exc

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> T:
        json_instruction = (
            f"\nYou must output your response STRICTLY as a valid JSON object conforming to "
            f"the {schema_cls.__name__} schema. Do not include markdown preamble or conversational text. "
            f"Enclose strictly in ```json ```."
        )
        full_prompt = f"{prompt}\n{json_instruction}"
        raw_text = self.generate(full_prompt, system_prompt=system_prompt, **kwargs)

        try:
            parsed_dict = parse_structured_json(raw_text)
            return validate_and_instantiate(parsed_dict, schema_cls)
        except Exception as exc:
            raise ProviderStructuredOutputError(
                f"Failed to parse Gemini structured JSON into {schema_cls.__name__}: {exc}. Output was: {raw_text[:200]}"
            ) from exc

    def _translate_and_raise_error(self, exc: Exception) -> None:
        """Classifies Gemini exceptions strictly into typed operational or auth errors."""
        err_str = str(exc).lower()
        err_type = type(exc).__name__

        # Authentication / Configuration errors (NEVER fallback on auth errors)
        if any(w in err_str for w in ("api_key_invalid", "unauthenticated", "401", "403", "permission_denied", "invalid api key")):
            raise ProviderAuthenticationError(f"Gemini authentication failed: {exc}") from exc

        # Rate limits / Quota
        if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str:
            raise ProviderRateLimitError(f"Gemini rate limit exceeded: {exc}") from exc

        # Timeout
        if "timeout" in err_str or "timed out" in err_str or "deadline_exceeded" in err_str:
            raise ProviderTimeoutError(f"Gemini request timed out: {exc}") from exc

        # Network / Transport
        if any(w in err_str for w in ("connection", "network", "socket", "dns", "unreachable", "handshake")):
            raise ProviderNetworkError(f"Gemini network transport failure: {exc}") from exc

        # 5xx Server Error / Outage
        if any(w in err_str for w in ("500", "502", "503", "504", "internal_server_error", "unavailable")):
            raise ProviderUnavailableError(f"Gemini service unavailable (5xx): {exc}") from exc

        # Default provider operational failure
        raise ProviderUnavailableError(f"Gemini provider failure ({err_type}): {exc}") from exc


class OpenRouterProvider(LLMProvider):
    """
    Fallback Provider: OpenRouter API (OpenAI-compatible REST endpoint).
    Invoked strictly when Gemini suffers eligible operational failures.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.openrouter_api_key
        self.base_url = (config.openrouter_base_url or "https://openrouter.ai/api/v1").rstrip("/")
        self._model = config.openrouter_model or "google/gemini-2.5-flash"

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        if not self.is_available():
            raise ProviderConfigurationError("OpenRouter API key is not configured. Set OPENROUTER_API_KEY.")

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
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://policysetu.gov.in",
            "X-Title": "PolicySetu AI Subsystem",
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data_bytes,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if "error" in result:
                    err_msg = result["error"].get("message", str(result["error"]))
                    raise ProviderUnavailableError(f"OpenRouter returned error: {err_msg}")
                choices = result.get("choices", [])
                if not choices or "message" not in choices[0]:
                    raise ProviderInvalidResponseError("OpenRouter returned invalid response payload structure.")
                message = choices[0]["message"]
                content = message.get("content")
                if not content:
                    content = message.get("reasoning") or ""
                return content.strip()
        except urllib.error.HTTPError as exc:
            self._translate_http_error(exc)
            raise exc
        except (urllib.error.URLError, TimeoutError) as exc:
            reason = str(getattr(exc, "reason", exc)).lower()
            if "timed out" in reason or "timeout" in reason:
                raise ProviderTimeoutError(f"OpenRouter request timed out: {exc}") from exc
            raise ProviderNetworkError(f"Failed to connect to OpenRouter endpoint: {exc}") from exc
        except Exception as exc:
            raise ProviderUnavailableError(f"OpenRouter request failed: {exc}") from exc

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> T:
        json_instruction = (
            f"\nYou must output your response STRICTLY as a valid JSON object conforming to "
            f"the {schema_cls.__name__} schema. Do not include preamble or conversational text. "
            f"Enclose strictly in ```json ```."
        )
        full_prompt = f"{prompt}\n{json_instruction}"
        raw_text = self.generate(full_prompt, system_prompt=system_prompt, **kwargs)

        try:
            parsed_dict = parse_structured_json(raw_text)
            return validate_and_instantiate(parsed_dict, schema_cls)
        except Exception as exc:
            raise ProviderStructuredOutputError(
                f"Failed to parse OpenRouter structured JSON into {schema_cls.__name__}: {exc}. Output: {raw_text[:200]}"
            ) from exc

    def _translate_http_error(self, exc: urllib.error.HTTPError) -> None:
        code = exc.code
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass

        if code in (401, 403):
            raise ProviderAuthenticationError(f"OpenRouter authentication failed (HTTP {code}): {body}") from exc
        elif code in (402, 429):
            raise ProviderRateLimitError(f"OpenRouter rate limit / quota / payment required (HTTP {code}): {body}") from exc
        elif code in (500, 502, 503, 504):
            raise ProviderUnavailableError(f"OpenRouter upstream service error (HTTP {code}): {body}") from exc
        else:
            raise ProviderUnavailableError(f"OpenRouter HTTP {code} error: {body}") from exc


class OpenAICompatibleProvider(LLMProvider):
    """
    Standard OpenAI-compatible provider for generic custom deployments (vLLM, Ollama, OpenAI).
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
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=data_bytes,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise ProviderAuthenticationError(f"OpenAI authentication failed: {exc}") from exc
            elif exc.code == 429:
                raise ProviderRateLimitError(f"OpenAI rate limit: {exc}") from exc
            raise ProviderUnavailableError(f"OpenAI HTTP {exc.code}: {exc.reason}") from exc
        except Exception as exc:
            raise ProviderUnavailableError(f"OpenAI error: {exc}") from exc

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> T:
        json_instruction = (
            f"\nYou must output your response STRICTLY as a valid JSON object conforming to "
            f"the {schema_cls.__name__} schema. Do not enclose in anything other than ```json ```."
        )
        full_prompt = f"{prompt}\n{json_instruction}"
        raw_output = self.generate(full_prompt, system_prompt=system_prompt, **kwargs)
        parsed_dict = parse_structured_json(raw_output)
        return validate_and_instantiate(parsed_dict, schema_cls)


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

        # 2. Income extraction
        inc_match = re.search(
            r"(?:income|aamdani|आय)\s*(?:is|=|:)?\s*(?:₹|rs\.?|inr)?\s*([\d,]+(?:\.\d+)?\s*(?:lakh|lac|crore|hazaar|k|cr)?)|"
            r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?\s*(?:lakh|lac|crore)?)",
            raw,
            re.IGNORECASE
        )
        if inc_match:
            val = inc_match.group(1) or inc_match.group(2)
            facts.append(
                ApplicantFactCandidate(
                    field="annual_family_income",
                    raw_value=val.strip(),
                    data_type="numeric",
                    confidence=0.95,
                    evidence_text=inc_match.group(0),
                    suggested_verification_status=FactVerificationStatus.SELF_REPORTED,
                )
            )

        # 3. State extraction
        if self.query_parser.is_self_declaration(raw):
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

        # 4. Social Category extraction
        if self.query_parser.is_self_declaration(raw):
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
                    statement="Statutory criteria according to official policy documentation.",
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


def get_llm_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """Factory function returning the configured primary LLM provider."""
    cfg = config or LLMConfig.from_env()
    provider_type = cfg.provider.strip().lower()

    if provider_type in ("gemini", "auto"):
        return GeminiProvider(cfg)
    elif provider_type == "openrouter":
        return OpenRouterProvider(cfg)
    elif provider_type == "openai":
        return OpenAICompatibleProvider(cfg)
    elif provider_type == "mock":
        return MockLLMProvider(cfg)
    else:
        raise ValueError(f"Unsupported LLM provider: '{cfg.provider}'. Supported: 'auto', 'gemini', 'openrouter', 'openai', 'mock'")


__all__ = [
    "LLMProvider",
    "GeminiProvider",
    "OpenRouterProvider",
    "OpenAICompatibleProvider",
    "MockLLMProvider",
    "get_llm_provider",
]
