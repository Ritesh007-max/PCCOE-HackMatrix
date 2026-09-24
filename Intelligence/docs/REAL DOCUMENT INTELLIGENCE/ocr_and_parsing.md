# FIN OCR and Multi-Format Document Parsing Engine

## 1. Multi-Format Ingestion Overview

The document ingestion pipeline decouples raw uploaded citizen files from downstream LLM models, extracting normalized text, tables, and spatial metadata into provider-neutral `DocumentContent` containers.

Supported document formats:
- **PDF**: Native, scanned, and hybrid digital/scanned documents.
- **DOCX**: Microsoft Word documents containing structured paragraphs and tables.
- **Images**: PNG, JPEG, TIFF, WEBP certificates and identification cards.

## 2. The 5-Stage Layered PDF Parsing Pipeline

PDF documents undergo a 5-stage layered extraction process:
```
Stage 1: Native Text Extraction (PyMuPDF blocks, font sizes, bounding boxes)
    ↓
Stage 2: Scan / Raster Detection (ScanDetector evaluates text density and image coverage)
    ↓
Stage 3: Page Rasterization (Renders scanned pages at 200 DPI for high-accuracy OCR)
    ↓
Stage 4: Optical Character Recognition (PaddleOCR with Heuristic Fallback Engine)
    ↓
Stage 5: Dual-Stream Preservation (Maintains separate native and OCR text streams)
```

## 3. Scan & Raster Detection

The `ScanDetector` inspects every page and classifies it into one of four states:
- `NATIVE_TEXT`: Text density exceeds threshold (≥ 50 characters, < 70% raster image area). Native text blocks extracted directly.
- `SCANNED`: Less than 50 characters of native text and page consists primarily of raster image(s). Routed to OCR rasterization.
- `HYBRID`: Native text present alongside substantial embedded images (e.g. digital form with scanned certificate attachment). Both native extraction and targeted OCR are performed.
- `EMPTY`: No text and no images detected on the page.

## 4. OCR Engine Architecture

- **Primary OCR Engine**: `PaddleOCREngine` supporting Hindi and English scripts with bounding box tracking.
- **Heuristic OCR Fallback**: `HeuristicOCREngine` provides deterministic keyword and text-pattern recovery if PaddleOCR is not installed or dependencies are missing.
- **EXIF Auto-Rotation**: `ImageParser` inspects EXIF orientation tags before OCR to ensure certificates photographed sideways or upside down are rotated upright.

## 5. Structured Table Extraction

Tables in PDFs and DOCXs are parsed into structured `TableContent` objects:
- Headers are preserved as distinct column identifiers.
- Cell values are normalized into tabular row arrays.
- Rendered as Markdown (`get_table_markdown()`) when presented to LLMs for extraction.
