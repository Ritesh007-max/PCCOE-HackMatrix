# PCCOE HackMatrix

## Tech Stack
- **Backend**: Node.js, Express
- **Database**: Supabase (PostgreSQL)
- **File Storage**: Supabase Storage
- **Authentication**: JWT
- **Environment**: JavaScript, npm
- **Utilities**: Multer (file uploads), dotenv (environment variables)

## Overview
A full‑stack hackathon project showcasing a **backend** API built with **Node.js** and **Express**, leveraging **Supabase** for database and storage. It includes user authentication, profile management, document upload & extraction, and scheme management.

## Features
- **User Authentication** with JWT
- **Profile Management** (create, read, update, delete)
- **Document Handling**: upload, extract applicant data, list, retrieve, delete
- **Scheme Management**: create, list, retrieve, delete
- **Supabase Integration** for data persistence and file storage
- **Robust Validation** and error handling

## Description
A full‑stack hackathon project that provides user authentication, profile management, document upload/extraction, and scheme management.

## Setup & Installation
```bash
# Clone the repository
git clone <repository-url>
cd PCCOE-HackMatrix/BackEnd

# Install dependencies
npm install

# Copy env file and configure variables
cp .env.example .env
# Edit .env to add your Supabase credentials and JWT secret

# Run the development server
npm run dev
```
The server will start at `http://localhost:3000`.

## Running Tests
```bash
npm test
```
(Ensure you have the test suite configured.)

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to your fork and open a Pull Request

## License
MIT License

## Team
hexSlyerz

## Overview
A full‑stack hackathon project showcasing a **backend** API built with **Node.js** and **Express**, leveraging **Supabase** for database and storage. It includes user authentication, profile management, document upload & extraction, and scheme management.

### Problem Statement
Financial Policy Discovery, Eligibility & Application Assistant
People and small businesses often miss out on government subsidies, tax deductions, and financial assistance simply because eligibility rules and application steps are scattered across many sources. Build an assistant that uses an applicant's information to identify relevant schemes, explain eligibility, estimate benefit amounts, and guide them through the application process.

### Expected Outcomes
- Extracts relevant details from applicant‑provided documents.
- Matches and ranks applicable government schemes against verified eligibility rules, with a clear explanation for each match.
- Shows benefit estimates and any missing‑document requirements.
- Is tested against clearly eligible, clearly ineligible, and borderline cases.
- Shows the source scheme document and specific rule behind every eligibility determination.
- Flags unclear cases as needing manual review rather than giving a false‑confident yes/no.

## Features
- **User Authentication** with JWT
- **Profile Management** (create, read, update, delete)
- **Document Handling**: upload, extract applicant data, list, retrieve, delete
- **Scheme Management**: create, list, retrieve, delete
- **Supabase Integration** for data persistence and file storage
- **Robust Validation** and error handling

## Tech Stack
- **Backend**: Node.js, Express
- **Database**: Supabase (PostgreSQL)
- **File Storage**: Supabase Storage
- **Authentication**: JWT
- **Environment**: JavaScript, npm
- **Utilities**: Multer (file uploads), dotenv (environment variables)

## API Endpoints
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/users/register` | Register a new user |
| `POST` | `/api/users/login` | Authenticate and receive JWT |
| `GET/PUT/DELETE` | `/api/users/:id` | CRUD operations on users |
| `POST` | `/api/documents/process` | Upload a document for storage |
| `POST` | `/api/documents/extract` | Extract data from a stored document |
| `GET` | `/api/documents/` | List all documents |
| `GET` | `/api/documents/:id` | Get a single document |
| `DELETE` | `/api/documents/:id` | Delete a document |
| `POST` | `/api/schemes` | Create a new scheme |
| `GET` | `/api/schemes` | List schemes |
| `GET` | `/api/schemes/:id` | Retrieve a scheme |
| `DELETE` | `/api/schemes/:id` | Delete a scheme |

## Setup & Installation
```bash
# Clone the repository
git clone <repository-url>
cd PCCOE-HackMatrix/BackEnd

# Install dependencies
npm install

# Copy env file and configure variables
cp .env.example .env
# Edit .env to add your Supabase credentials and JWT secret

# Run the development server
npm run dev
```
The server will start at `http://localhost:3000`.

## Running Tests
```bash
npm test
```
(Ensure you have the test suite configured.)

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push to your fork and open a Pull Request

## License
MIT License

## Team
hexSlyerz

## Tech Stack
- **Backend**: Node.js, Express
- **Database**: Supabase (PostgreSQL)
- **File Storage**: Supabase Storage
- **Authentication**: JWT
- **Environment**: JavaScript, npm
- **Other**: Multer for file uploads, dotenv for config

## Description
A full‑stack hackathon project that provides user authentication, profile management, document upload/extraction, and scheme management.

## Running the Project
```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env

# Start the server
npm run dev
```

## Team
hexSlyerz