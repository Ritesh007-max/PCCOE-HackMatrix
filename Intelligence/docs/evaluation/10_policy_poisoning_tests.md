# Policy Poisoning & Source Authority Red Team

## 1. Attack Vectors Evaluated
The policy poisoning suite (`Intelligence/data/evaluation/red_team_policy_poisoning.jsonl` and `red_team_hf.jsonl`) evaluates adversarial data ingestion attacks against Phase 12 activation gates and source hierarchy:

1. **Unrealistic Income Threshold Jump**: Candidate source raises income threshold from Rs 2,50,000 to Rs 25,00,000 (10x jump). Blocked by Gate 10 (Realistic Boundary Gate).
2. **Missing Eligibility Criteria**: Candidate source drops mandatory eligibility conditions. Blocked by Gate 6 (Mandatory Criteria Gate).
3. **Catastrophic Deletion Attack**: Candidate dataset drops 90% of active schemes (4,749 -> 450). Blocked by Gate 12 (Corpus Drop Threshold <= 10%).
4. **Spoofed Government Domain**: Candidate source points to `https://myscheme-gov-in.phishing-portal.com`. Blocked by Gate 3 (Allowed Source Domain Whitelist).
5. **Malicious Redirect**: Source redirects to unapproved external domain. Sync rejected immediately.
6. **Hugging Face Statutory Field Injection**: Supplementary HF dataset introduces columns `is_eligible` or `statutory_pass`. Fields are automatically stripped; HF records cannot define statutory rules.
7. **Assistant Answers as Rules**: Dataset `BharatSchemes` contains generated chatbot answers. Engine prevents conversational text from entering statutory rule sets.
8. **Equal-Authority Primary Disagreement**: Two primary gazettes disagree on income limit. Automatic mutation is halted; decision status falls back to `REVIEW`.

## 2. Benchmark Defense Results
- **Gate Interception Rate**: 100.0%
- **Unsafe Policy Activation Rate**: 0.0%
- **Unauthorized Mutation Rate**: 0.0%
- **Active Snapshot Stability**: 100.0% (Remains `snapshot_20260921_193823`)
