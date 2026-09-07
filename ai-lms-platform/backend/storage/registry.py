import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("lms.storage.registry")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def register_uploaded_document(
    document_id: str,
    original_filename: str,
    stored_filename: str,
) -> Dict[str, Any]:
    """
    Persists document metadata associating document_id, original_filename, and stored_filename.
    """
    meta_path = UPLOAD_DIR / f"{document_id}.meta.json"
    data = {
        "document_id": document_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        logger.warning("Could not persist document metadata file: %s", exc)
    return data


def resolve_source_pdf(identifier: Optional[str]) -> Tuple[Optional[str], Optional[Path]]:
    """
    Resolves a document_id, original filename, or stored UUID filename
    to the actual stored physical PDF path.

    Returns:
        (stored_filename, physical_path) or (None, None) if not found.
    """
    if not identifier:
        return None, None

    clean_id = identifier.strip()

    # 1. Check if identifier is a document_id with a companion .meta.json file
    meta_file = UPLOAD_DIR / f"{clean_id}.meta.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            stored_name = meta.get("stored_filename")
            if stored_name:
                stored_path = UPLOAD_DIR / stored_name
                if stored_path.exists():
                    return stored_name, stored_path
        except Exception as exc:
            logger.debug("Failed to read meta file %s: %s", meta_file, exc)

    # 2. Check if clean_id is a document_id whose .pdf exists directly
    pdf_by_id = UPLOAD_DIR / f"{clean_id}.pdf"
    if pdf_by_id.exists():
        return f"{clean_id}.pdf", pdf_by_id

    # 3. Check if clean_id is already the stored_filename
    pdf_direct = UPLOAD_DIR / clean_id
    if pdf_direct.exists() and pdf_direct.is_file():
        return clean_id, pdf_direct

    # 4. Check if clean_id matches the original_filename in any .meta.json file
    for m_file in UPLOAD_DIR.glob("*.meta.json"):
        try:
            with open(m_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("original_filename") == clean_id:
                stored_name = meta.get("stored_filename")
                if stored_name:
                    stored_path = UPLOAD_DIR / stored_name
                    if stored_path.exists():
                        return stored_name, stored_path
        except Exception:
            continue

    # 5. Check if it's an absolute path that exists
    try:
        path_obj = Path(clean_id)
        if path_obj.is_absolute() and path_obj.exists():
            return path_obj.name, path_obj
    except Exception:
        pass

    return None, None
