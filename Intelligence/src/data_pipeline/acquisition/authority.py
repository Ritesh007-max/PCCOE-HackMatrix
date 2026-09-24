"""
FIN Authority Hierarchy & Precedence Engine.
Implements the 7-tier statutory source authority hierarchy.
Enforces that Tier 0/1/2 official sources can never be overridden by Tier 5 supplementary data.
"""

from urllib.parse import urlparse
from typing import Optional, Dict, Any
from .models import AuthorityTierName


class AuthorityHierarchy:
    """
    Deterministically evaluates and ranks source authority tiers.
    Enforces strict precedence:
      Tier 0 (Statutory/Acts) > Tier 1 (Ministry Portals) > Tier 2 (myScheme Discovery) >
      Tier 3 (National Portals) > Tier 4 (PIB/Press) > Tier 5 (Supplementary) > Tier 6 (Untrusted)
    """

    # Tier 0: Statutory / Acts / Gazettes
    TIER_0_DOMAINS = {
        "egazette.gov.in",
        "www.egazette.gov.in",
        "indiacode.nic.in",
        "www.indiacode.nic.in",
        "legislative.gov.in",
        "www.legislative.gov.in",
        "dsel.education.gov.in",  # Gazette repository
    }

    # Tier 2: myScheme discovery portal subdomains
    TIER_2_DOMAINS = {
        "myscheme.gov.in",
        "www.myscheme.gov.in",
        "search.myscheme.gov.in",
        "rules.myscheme.gov.in",
        "api.myscheme.gov.in",
        "cdn.myscheme.in",
    }

    # Tier 3: National portals
    TIER_3_DOMAINS = {
        "india.gov.in",
        "www.india.gov.in",
        "digitalindia.gov.in",
        "www.digitalindia.gov.in",
        "data.gov.in",
        "www.data.gov.in",
        "web.umang.gov.in",
        "services.india.gov.in",
    }

    # Tier 4: Official government press & publications
    TIER_4_DOMAINS = {
        "pib.gov.in",
        "www.pib.gov.in",
        "newsonair.gov.in",
        "www.newsonair.gov.in",
    }

    # Tier 5: Supplementary platforms
    TIER_5_DOMAINS = {
        "huggingface.co",
        "www.huggingface.co",
        "kaggle.com",
        "www.kaggle.com",
        "github.com",
        "www.github.com",
    }

    @classmethod
    def classify_url(cls, url: Optional[str], context: Optional[str] = None) -> AuthorityTierName:
        """
        Classifies an official or supplementary URL into its exact Authority Tier.
        """
        if not url or not url.strip():
            return AuthorityTierName.TIER_6_UNTRUSTED

        clean_url = url.strip()
        parsed = urlparse(clean_url)
        host = (parsed.netloc or "").lower().split(":")[0]
        path = (parsed.path or "").lower()

        # Reject deceptive domains where .gov.in or .nic.in appears as spoofing subdomains
        if any(tok in host for tok in (".gov.in.", ".nic.in.", "gov-in", "nic-in")):
            return AuthorityTierName.TIER_6_UNTRUSTED

        # 1. Check Tier 0 Statutory
        if host in cls.TIER_0_DOMAINS or "gazette" in host or "indiacode" in host:
            return AuthorityTierName.TIER_0_LEGAL_STATUTORY
        if "gazette" in path or "act" in path or "statutory-order" in path:
            if host.endswith(".gov.in") or host.endswith(".nic.in"):
                return AuthorityTierName.TIER_0_LEGAL_STATUTORY

        # 2. Check Tier 2 myScheme Discovery
        if host in cls.TIER_2_DOMAINS or "myscheme.gov.in" in host:
            return AuthorityTierName.TIER_2_MYSCHEME

        # 3. Check Tier 3 National Portals
        if host in cls.TIER_3_DOMAINS:
            return AuthorityTierName.TIER_3_NATIONAL_OFFICIAL

        # 4. Check Tier 4 Official Publications
        if host in cls.TIER_4_DOMAINS:
            return AuthorityTierName.TIER_4_OFFICIAL_PUBLICATION

        # 5. Check Tier 1 First-Party Ministry & Operational Portals (.gov.in / .nic.in)
        if (host.endswith(".gov.in") or host.endswith(".nic.in")) and not host.endswith("-gov.in"):
            return AuthorityTierName.TIER_1_FIRST_PARTY_OPERATIONAL

        # 6. Check Tier 5 Supplementary Data
        if host in cls.TIER_5_DOMAINS or "supplementary" in str(context).lower():
            return AuthorityTierName.TIER_5_SUPPLEMENTARY

        # 7. Untrusted / Third-party
        return AuthorityTierName.TIER_6_UNTRUSTED

    @classmethod
    def compare_precedence(cls, tier_a: AuthorityTierName, tier_b: AuthorityTierName) -> int:
        """
        Returns:
          > 0 if tier_a has higher precedence than tier_b
          < 0 if tier_b has higher precedence than tier_a
          == 0 if both tiers have equal precedence
        """
        return tier_a.rank - tier_b.rank

    @classmethod
    def field_precedence_tier(cls, field_name: str, preferred_source_tier: AuthorityTierName) -> AuthorityTierName:
        """
        Priority decision model from Section 28:
        - Eligibility: Tier 0 > Tier 1 > Tier 2
        - Benefit: Tier 0 > Tier 1 > Tier 2
        - Statutory Conditions: Tier 0 > Tier 1 > Tier 2
        - Application Steps: Tier 1 > Tier 2
        - Application URL: Tier 1 > Tier 2
        - FAQs: Tier 1 > Tier 2 > Tier 5
        - Supplementary Data (Tier 5): Discovery only, NEVER statutory truth.
        """
        return preferred_source_tier
