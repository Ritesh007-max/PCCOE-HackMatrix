import sys
import os
import zipfile
import json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

raw_dir = Path("data/raw")
zip_path = raw_dir / "archive (1).zip"

zip_info = {
    "dataset_name": "State and Central Scheme Documents Corpus (Archive)",
    "file_name": "archive (1).zip",
    "file_type": "ZIP (text documents archive)",
    "size_bytes": zip_path.stat().st_size,
    "size_mb": round(zip_path.stat().st_size / (1024 * 1024), 2),
    "folder_breakdown": {},
    "total_files": 0,
    "file_extensions": {},
    "sample_files": [],
}

with zipfile.ZipFile(zip_path, 'r') as z:
    infolist = z.infolist()
    zip_info["total_files"] = len(infolist)
    for info in infolist:
        parts = info.filename.split('/')
        folder = parts[0] if len(parts) > 1 else "root"
        zip_info["folder_breakdown"][folder] = zip_info["folder_breakdown"].get(folder, 0) + 1
        ext = Path(info.filename).suffix
        zip_info["file_extensions"][ext] = zip_info["file_extensions"].get(ext, 0) + 1
    
    # Read 3 sample text files
    for sample_name in ["uttar-pradesh/state_uttar-pradesh_doc_1.txt", "central/central_doc_1.txt", "maharashtra/state_maharashtra_doc_1.txt"]:
        if sample_name in z.namelist():
            content = z.read(sample_name).decode('utf-8', errors='ignore')
            zip_info["sample_files"].append({
                "filename": sample_name,
                "length_chars": len(content),
                "snippet": content[:1000]
            })

with open("scripts/zip_audit_out.json", "w", encoding="utf-8") as f:
    json.dump(zip_info, f, indent=2, ensure_ascii=False)

print("ZIP Audit completed successfully. Total files:", zip_info["total_files"])
