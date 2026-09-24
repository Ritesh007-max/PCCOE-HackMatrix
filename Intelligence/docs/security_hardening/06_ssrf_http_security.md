# FIN SSRF Protection & Outbound HTTP Security

## 1. Threat Model & Boundaries
Data acquisition crawls external government portals (e.g., `myscheme.gov.in`, `data.gov.in`) to keep scheme rules up to date. This exposes the system to potential Server-Side Request Forgery (SSRF) and malicious redirect attacks.

---

## 2. Inbound URL & Domain Validation Rules

### 2.1 Domain Whitelist Enforcement
Outbound HTTP requests are restricted to authorized government domains:
- Official suffixes: `.gov.in`, `.nic.in` (excluding spoofed patterns such as `*-gov.in`).
- Approved explicit hosts: `myscheme.gov.in`, `india.gov.in`, `digitalindia.gov.in`, `data.gov.in`, `web.umang.gov.in`, `jansuraksha.gov.in`.

### 2.2 Private Network & SSRF Blocking
All destination addresses are validated against private, link-local, and loopback IP ranges:
- **Loopback**: `127.0.0.1`, `::1`, `localhost`
- **Private RFC 1918**: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- **Link-Local & Cloud Metadata**: `169.254.169.254` (AWS/GCP/Azure IMDSv1), `fd00:ec2::254` (IMDSv2 IPv6), `metadata.google.internal`
- **Encoded IP Representations**: Integer formats (`2130706433`), hexadecimal representations (`0x7f000001`), and octal forms are rejected.
- **Direct IP Literal Access**: Direct IP address connections to government endpoints are prohibited; queries must resolve via legitimate DNS hostnames.

---

## 3. Safe Outbound HTTP Client (`SafeHttpClient`)

### 3.1 Timeouts & Bounded Execution
- **Connection Timeout**: 5.0 seconds.
- **Read Timeout**: 20.0 seconds.
- **Total Timeout**: 30.0 seconds.
- **Maximum Retries**: Bounded to 5 attempts with exponential backoff and jitter.

### 3.2 Safe Redirection Handling (`SafeRedirectHandler`)
- Maximum redirection depth is capped at 3 hops.
- Every intermediate and target redirect URL is re-validated through `AcquisitionSecurityValidator.is_safe_url()`.
- HTTPS downgrade to HTTP is strictly rejected.
- Any attempt to redirect to an internal or private address aborts the connection with HTTP 403.

### 3.3 Response Body Caps
- Maximum permissible response payload is 25 MB (`MAX_RESPONSE_SIZE`).
- Responses exceeding this threshold are immediately truncated and recorded as `PAYLOAD_OVERSIZE` crawl failures.
