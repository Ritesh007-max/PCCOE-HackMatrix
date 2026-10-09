# 🚀 PCCOE HackMatrix

### **Financial Policy Discovery, Eligibility & Application Assistant**

> **Turning complex government policies into clear, personalized financial opportunities.**

---

## 🏆 The Problem

Government subsidies, financial assistance programs, tax deductions, and support schemes can provide significant benefits to individuals and small businesses.

The problem?

**Finding the right scheme is often harder than applying for it.**

Eligibility criteria are scattered across:

* Government portals
* Policy documents
* PDF guidelines
* Notifications
* Scheme-specific documents
* Application instructions

Applicants often have to manually determine:

> **"Am I eligible?"**

> **"What documents do I need?"**

> **"How much benefit can I receive?"**

> **"Which rule makes me eligible?"**

This creates information overload and causes potentially eligible applicants to miss valuable financial support.

---

# 💡 Our Solution

## **An intelligent Financial Policy Discovery & Eligibility Assistant**

PCCOE HackMatrix transforms scattered policy information into a **personalized scheme discovery system**.

The platform takes:

**Applicant Information + Uploaded Documents + Government Scheme Rules**

and produces:

**Relevant Schemes + Eligibility Explanation + Benefit Estimate + Missing Documents + Evidence**

Instead of simply saying:

> ❌ Eligible

our system aims to explain:

> ✅ **Eligible**
>
> **Why:** Applicant's annual income satisfies the scheme's income threshold.
>
> **Evidence:** Scheme Rule 3.2 — Annual income must be below ₹X.
>
> **Source:** Official Government Scheme Document.

This makes every decision **traceable and explainable**.

---

# 🎯 Core Objectives

Our system is designed around five major objectives:

### 1️⃣ Discover

Identify government schemes relevant to an applicant's profile.

### 2️⃣ Verify

Compare applicant information against the actual eligibility rules.

### 3️⃣ Explain

Show **why** an applicant qualifies or does not qualify.

### 4️⃣ Estimate

Calculate the potential financial benefit wherever the scheme provides quantifiable benefits.

### 5️⃣ Guide

Tell applicants what documents are missing and what steps are required for application.

---

# ✨ Key Features

## 🔐 1. Secure Authentication

Users can securely create accounts and authenticate using JWT-based authentication.

**Features:**

* User registration
* Login
* JWT token generation
* Protected API routes
* Profile management
* Secure user-specific resources

---

## 👤 2. Applicant Profile

Applicants can maintain their personal and financial information.

Example information:

```text
Name
Age
Gender
Location
Occupation
Annual Income
Business Type
Business Turnover
Category
Employment Status
Family Details
```

This information becomes the foundation for scheme matching.

---

## 📄 3. Intelligent Document Processing

Applicants can upload supporting documents such as:

* Income certificates
* Identity documents
* Business documents
* Registration certificates
* Tax-related documents
* Other supporting PDFs

### Workflow

```text
Upload Document
       ↓
Store Securely
       ↓
Extract Text / Data
       ↓
Identify Relevant Fields
       ↓
Validate Applicant Information
       ↓
Use Verified Information
for Scheme Matching
```

The goal is to minimize repetitive manual form filling.

---

# 🤖 4. AI-Powered Scheme Matching

The system can compare applicant information against scheme eligibility requirements.

Instead of showing hundreds of schemes, the system focuses on **relevant opportunities**.

Example:

```text
Applicant
   │
   ├── Income: ₹2.4 Lakh
   ├── Location: Gujarat
   ├── Occupation: Farmer
   ├── Age: 24
   └── Business: No
          │
          ▼
    Eligibility Engine
          │
          ▼
 ┌───────────────────────────┐
 │ Scheme A → Eligible       │
 │ Scheme B → Ineligible     │
 │ Scheme C → Borderline     │
 │ Scheme D → Eligible       │
 └───────────────────────────┘
```

---

# 🧠 5. Explainable Eligibility

One of the core principles of PCCOE HackMatrix is:

## **No unexplained eligibility decisions.**

Every result should provide:

```text
Eligibility Status
        ↓
Reason
        ↓
Matched Applicant Data
        ↓
Eligibility Rule
        ↓
Official Source
```

### Example

```text
Scheme: Example Education Support Scheme

Status: ✅ Eligible

Matched Rule:
Annual family income must be below ₹3,00,000.

Applicant:
Annual family income = ₹2,40,000

Result:
₹2,40,000 < ₹3,00,000

Source:
Official Government Scheme Document
```

This makes the system **auditable and transparent**.

---

# ⚠️ 6. Borderline Case Detection

Real-world eligibility is not always simply YES or NO.

Some applications contain:

* Missing information
* Conflicting information
* Ambiguous policy rules
* Documents that require verification
* Values close to eligibility thresholds

Instead of generating a false-confidence result:

```text
⚠️ MANUAL REVIEW REQUIRED
```

The system can identify uncertain cases and explain **what information is missing or ambiguous**.

---

# 📑 7. Missing Document Detection

For every potential scheme, the system can identify required documents.

Example:

```text
Scheme: Small Business Support Scheme

Required:
✅ PAN Card
✅ Aadhaar
✅ Business Registration
❌ Income Certificate

Action:
Upload Income Certificate
```

This converts scheme discovery into an actionable process.

---

# 💰 8. Benefit Estimation

Where scheme rules provide measurable benefits, the platform can estimate potential financial support.

Example:

```text
Eligible Amount: ₹50,000

Estimated Benefit:
₹50,000

Calculation:
Eligible Assistance = 50% of approved expense
Approved Expense = ₹1,00,000

Estimated Benefit = ₹50,000
```

> Estimates are clearly distinguished from guaranteed benefits and depend on the official scheme rules and applicant verification.

---

# 🔎 9. Evidence-Based Results

Every eligibility determination should be connected to its underlying policy evidence.

### Result Structure

```text
┌─────────────────────────────────────┐
│ Scheme: XYZ Financial Assistance    │
├─────────────────────────────────────┤
│ Status: ✅ Eligible                  │
│                                     │
│ Reason: Income requirement satisfied│
│                                     │
│ Rule: Section 4.2                   │
│                                     │
│ Source: Official Government PDF     │
│                                     │
│ Missing Documents: None             │
└─────────────────────────────────────┘
```

This creates a system where users can **verify the reasoning instead of blindly trusting AI**.

---

# 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │      Frontend        │
                         │  Web / Dashboard     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Express API       │
                         │      Node.js         │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
          │ Auth / JWT  │    │  Documents  │    │   Schemes    │
          └─────────────┘    └──────┬──────┘    └──────┬───────┘
                                    │                    │
                                    ▼                    ▼
                            ┌────────────────────────────────┐
                            │          Supabase               │
                            │                                │
                            │ PostgreSQL + Storage            │
                            └───────────────┬────────────────┘
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │ AI / Eligibility Engine │
                              │                         │
                              │ Extraction              │
                              │ Retrieval               │
                              │ Rule Matching            │
                              │ Explanation              │
                              │ Confidence / Review     │
                              └─────────────────────────┘
```

---

# 🔄 End-to-End Workflow

```text
                 USER
                  │
                  ▼
        ┌───────────────────┐
        │ Create Profile    │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Upload Documents  │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Extract Applicant │
        │ Information       │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Retrieve Relevant │
        │ Scheme Rules      │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ Eligibility       │
        │ Evaluation        │
        └─────────┬─────────┘
                  │
             ┌────┴────┐
             ▼         ▼
         CONFIDENT   UNCLEAR
             │         │
             ▼         ▼
       ┌──────────┐  ┌──────────────┐
       │ Result   │  │ Manual Review│
       └────┬─────┘  └──────────────┘
            │
            ▼
   ┌───────────────────────┐
   │ Explain + Estimate    │
   │ + Missing Documents   │
   │ + Source Evidence     │
   └───────────────────────┘
```

---

# 🧠 AI / RAG Architecture

For policy documents, a Retrieval-Augmented Generation approach can help ground responses in official scheme information.

```text
Government Scheme PDFs
          │
          ▼
     PDF Extraction
          │
          ▼
     Text Chunking
          │
          ▼
       Embeddings
          │
          ▼
     Vector Database
          │
          ▼
    Relevant Rule Retrieval
          │
          ▼
   Eligibility Evaluation
          │
          ▼
  Evidence-Grounded Response
```

### Why RAG?

Government policies can be long and difficult to interpret.

Instead of sending an entire policy document to an LLM, the system retrieves the **relevant sections** and uses them as evidence.

This helps provide:

* More relevant context
* Source-grounded answers
* Lower unnecessary token usage
* Better traceability
* Easier policy updates

---

# 🛡️ Safety & Reliability

Financial assistance decisions should not rely on an unexplained AI response.

Therefore, the architecture emphasizes:

### Evidence First

AI responses should be grounded in retrieved policy content.

### Rule-Based Verification

Critical eligibility conditions can be checked using deterministic logic.

### Confidence Handling

Unclear cases should be flagged instead of forcing a YES/NO decision.

### Source Traceability

Each result should point back to the relevant scheme document and rule.

### Human Review

Ambiguous cases can be escalated for manual verification.

---

# 🗄️ Database & Storage

## Supabase PostgreSQL

Used for structured application data.

Potential entities:

```text
users
profiles
documents
schemes
eligibility_rules
eligibility_results
applications
```

### Example Relationship

```text
User
 │
 ├── Profile
 │
 ├── Documents
 │
 ├── Eligibility Results
 │
 └── Applications

Scheme
 │
 ├── Eligibility Rules
 │
 ├── Required Documents
 │
 └── Benefit Rules
```

---

# ☁️ Supabase Storage

Uploaded applicant documents are stored securely using Supabase Storage.

Example:

```text
documents/
 ├── user_001/
 │    ├── income_certificate.pdf
 │    ├── identity.pdf
 │    └── business_registration.pdf
 │
 └── user_002/
      └── income_certificate.pdf
```

---

# 🔐 Authentication

Authentication is implemented using **JWT**.

### Authentication Flow

```text
Register
   ↓
Password Validation
   ↓
User Created
   ↓
Login
   ↓
JWT Generated
   ↓
Authenticated Requests
   ↓
Protected API Routes
```

---

# 🧩 API Endpoints

## 👤 Users

| Method   | Endpoint              | Description                  |
| -------- | --------------------- | ---------------------------- |
| `POST`   | `/api/users/register` | Register a new user          |
| `POST`   | `/api/users/login`    | Authenticate and receive JWT |
| `GET`    | `/api/users/:id`      | Get user                     |
| `PUT`    | `/api/users/:id`      | Update user                  |
| `DELETE` | `/api/users/:id`      | Delete user                  |

---

## 📄 Documents

| Method   | Endpoint                 | Description                   |
| -------- | ------------------------ | ----------------------------- |
| `POST`   | `/api/documents/process` | Upload and process document   |
| `POST`   | `/api/documents/extract` | Extract applicant information |
| `GET`    | `/api/documents/`        | List documents                |
| `GET`    | `/api/documents/:id`     | Get document                  |
| `DELETE` | `/api/documents/:id`     | Delete document               |

---

## 🏛️ Schemes

| Method   | Endpoint           | Description     |
| -------- | ------------------ | --------------- |
| `POST`   | `/api/schemes`     | Create scheme   |
| `GET`    | `/api/schemes`     | List schemes    |
| `GET`    | `/api/schemes/:id` | Retrieve scheme |
| `DELETE` | `/api/schemes/:id` | Delete scheme   |

---

# 🧪 Testing Strategy

The system should be evaluated against three major categories.

### 🟢 Clearly Eligible

Applicant satisfies all mandatory requirements.

Expected:

```text
ELIGIBLE
```

with supporting evidence.

---

### 🔴 Clearly Ineligible

Applicant violates one or more mandatory requirements.

Expected:

```text
NOT ELIGIBLE
```

with the exact failed condition.

---

### 🟡 Borderline / Unclear

Applicant information is incomplete, conflicting, or falls into an ambiguous policy condition.

Expected:

```text
MANUAL REVIEW REQUIRED
```

with the reason for escalation.

---

# 📊 Example Evaluation

| Case   |  Income | Business | Required Docs | Result           |
| ------ | ------: | -------- | ------------- | ---------------- |
| Case A |     ₹2L | Yes      | Complete      | 🟢 Eligible      |
| Case B |     ₹8L | Yes      | Complete      | 🔴 Ineligible    |
| Case C | Unknown | Yes      | Incomplete    | 🟡 Manual Review |

The goal is not simply to maximize the number of "eligible" predictions.

## **The goal is to produce trustworthy decisions with evidence.**

---

# 🛠️ Tech Stack

### Backend

* Node.js
* Express.js
* JavaScript

### Database

* PostgreSQL
* Supabase

### Storage

* Supabase Storage

### Authentication

* JSON Web Tokens (JWT)

### File Processing

* Multer
* PDF/document extraction pipeline

### Configuration

* dotenv

### AI Layer

* Retrieval-Augmented Generation (RAG)
* Embeddings
* Vector retrieval
* Rule-based eligibility evaluation

---

# 📁 Repository Structure

The repository root contains only the core functional modules:

```text
PCCOE-HackMatrix/
├── BackEnd/         # Express.js REST API gateway, RBAC, and Supabase integration (Port 5000)
├── FrontEnd/        # React 19 + Vite citizen portal and reviewer dashboard (Port 5173)
├── docs/            # Product requirements (PRD/MVP), design specs, and Postman collections
├── Intelligence/    # FastAPI microservice: hybrid RAG, document OCR, and deterministic rule engine (Port 8000)
├── .gitignore       # Git tracking configuration excluding secrets, caches, and bulk models
└── README.md        # Primary project documentation & onboarding guide
```

---

# ⚙️ Prerequisites & Setup Guide

### System Prerequisites
- **Node.js**: v18.0.0 or higher
- **npm**: v9.0.0 or higher
- **Python**: v3.10 or v3.11
- **Git**: Installed and configured

---

### 1️⃣ BackEnd Setup (Express Gateway)

The Express backend connects to Supabase, enforces citizen/reviewer RBAC, orchestrates notifications, and routes AI requests to the Intelligence microservice.

```bash
cd BackEnd

# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env with your Supabase credentials (SUPABASE_URL, SUPABASE_ANON_ROLE_KEY, etc.)

# 3. Start development server (Port 5000)
npm run dev
```

---

### 2️⃣ FrontEnd Setup (React + Vite)

The frontend provides the responsive citizen portal, AI assistant interface, document readiness viewer, and reviewer decision dashboard.

```bash
cd FrontEnd

# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
# Default points to VITE_API_URL=http://localhost:5000

# 3. Start development server (Port 5173)
npm run dev

# 4. Production build verification
npm run build
```

---

### 3️⃣ Intelligence Microservice Setup (FastAPI + Python)

The Intelligence microservice powers document intelligence, hybrid vector/lexical scheme retrieval across 4,752 schemes, and deterministic eligibility evaluation.

```bash
cd Intelligence

# 1. Create and activate a Python virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
# source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Configure your LLM API keys (e.g. GEMINI_API_KEY, OPENROUTER_API_KEY)

# 4. Start the FastAPI microservice (Port 8000)
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

---

# 🧪 Running Automated Tests

All three layers of the FIN architecture have automated test suites:

### FrontEnd Tests
```bash
cd FrontEnd
npm test
```

### BackEnd Tests
```bash
cd BackEnd
npm test
```

### Intelligence Tests
```bash
cd Intelligence
# Activate virtual environment first
pytest tests/security/ tests/rules/ tests/api/test_health.py tests/nlp/test_language.py -q
```

---

# 🌍 Real-World Impact

PCCOE HackMatrix is designed around a simple idea:

> **Financial assistance should not be inaccessible simply because policy documents are difficult to understand.**

The platform can help:

### 👨‍🌾 Individuals

Discover subsidies and financial assistance relevant to their circumstances.

### 🏪 Small Businesses

Find support programs, incentives, and applicable financial policies.

### 🎓 Students

Discover scholarships and educational assistance.

### 🏛️ Organizations

Build a structured interface over complex policy information.

---

# 🚀 Future Scope

The architecture can be extended with:

* 🔎 Semantic policy search
* 🤖 Conversational AI assistant
* 📄 Advanced document OCR
* 🌐 Multilingual support
* 🗣️ Voice-based assistance
* 📱 Mobile application
* 🧾 Application form auto-filling
* 📊 Personalized benefit dashboard
* 🔔 Scheme deadline notifications
* 🏛️ Government API integrations
* 📚 Automatic policy document updates
* 👨‍⚖️ Human-review workflow

---

# 🏆 Why This Project Stands Out

### **1. Personalized**

The system evaluates schemes against the **individual applicant**, rather than providing generic search results.

### **2. Explainable**

Users see **why** a scheme matched or failed.

### **3. Evidence-Based**

Eligibility decisions are connected to policy documents and specific rules.

### **4. Uncertainty-Aware**

The system can say:

> **"We don't have enough information to decide."**

instead of generating a confident but potentially incorrect answer.

### **5. Action-Oriented**

The platform doesn't stop at discovering a scheme.

It tells users:

```text
What you qualify for
        ↓
Why you qualify
        ↓
How much you may receive
        ↓
What documents are missing
        ↓
What to do next
```

---

# 👥 Team

## **hexSlayerz**

Building technology that makes complex financial policies easier to discover, understand and act upon.
