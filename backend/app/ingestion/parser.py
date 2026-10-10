import os
import re
from typing import List, Dict, Any

# Map collections to allowed roles
COLLECTION_ROLE_MAP = {
    "general": ["doctor", "nurse", "billing_executive", "technician", "admin"],
    "clinical": ["doctor", "admin"],
    "nursing": ["nurse", "doctor", "admin"],
    "billing": ["billing_executive", "admin"],
    "equipment": ["technician", "admin"]
}

class HierarchicalDocumentParser:
    """
    Parses Markdown and PDF documents with structural awareness:
    Preserves headings, tables, and code blocks.
    Applies hierarchical chunking (section -> subsection -> paragraph/table)
    and attaches parent section title as explicit context prefix.
    """
    def __init__(self, max_chunk_tokens: int = 400, overlap_tokens: int = 50):
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = overlap_tokens

    def estimate_tokens(self, text: str) -> int:
        return len(text.split())

    def parse_file(self, file_path: str, collection: str) -> List[Dict[str, Any]]:
        filename = os.path.basename(file_path)
        access_roles = COLLECTION_ROLE_MAP.get(collection, ["admin"])

        if file_path.endswith(".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self._parse_markdown_structure(content, filename, collection, access_roles)
        elif file_path.endswith(".pdf"):
            return self._parse_pdf_structure(file_path, filename, collection, access_roles)
        else:
            return []

    def _parse_markdown_structure(self, content: str, filename: str, collection: str, access_roles: List[str]) -> List[Dict[str, Any]]:
        lines = content.split("\n")
        chunks = []
        
        current_h1 = filename.replace(".md", "").replace("_", " ").title()
        current_h2 = ""
        current_h3 = ""
        
        buffer = []
        current_chunk_type = "text"

        def flush_buffer(b_lines, section_title, chunk_type):
            if not b_lines:
                return
            raw_text = "\n".join(b_lines).strip()
            if not raw_text:
                return
            
            # Construct context prefix
            context_prefix = f"[Document: {filename} | Context: {section_title}]\n"
            full_text = context_prefix + raw_text
            
            # Sub-split if token limit exceeded
            if self.estimate_tokens(full_text) > self.max_chunk_tokens:
                sub_parts = self._split_large_text(raw_text, self.max_chunk_tokens)
                for part in sub_parts:
                    chunks.append({
                        "text": f"{context_prefix}{part}",
                        "source_document": filename,
                        "collection": collection,
                        "access_roles": access_roles,
                        "section_title": section_title,
                        "chunk_type": chunk_type
                    })
            else:
                chunks.append({
                    "text": full_text,
                    "source_document": filename,
                    "collection": collection,
                    "access_roles": access_roles,
                    "section_title": section_title,
                    "chunk_type": chunk_type
                })

        is_in_table = False

        for line in lines:
            line_str = line.strip()

            # Heading 1 (# ...)
            if line_str.startswith("# "):
                flush_buffer(buffer, f"{current_h1} > {current_h2}".strip(" >"), current_chunk_type)
                buffer = []
                current_h1 = line_str.replace("# ", "").strip()
                current_h2 = ""
                current_h3 = ""
                current_chunk_type = "heading"

            # Heading 2 (## ...)
            elif line_str.startswith("## "):
                flush_buffer(buffer, f"{current_h1} > {current_h2}".strip(" >"), current_chunk_type)
                buffer = []
                current_h2 = line_str.replace("## ", "").strip()
                current_h3 = ""
                current_chunk_type = "heading"

            # Heading 3 (### ...)
            elif line_str.startswith("### "):
                flush_buffer(buffer, f"{current_h1} > {current_h2} > {current_h3}".strip(" >"), current_chunk_type)
                buffer = []
                current_h3 = line_str.replace("### ", "").strip()
                current_chunk_type = "heading"

            # Table line
            elif line_str.startswith("|"):
                if not is_in_table:
                    # Flush prior text buffer
                    flush_buffer(buffer, f"{current_h1} > {current_h2} > {current_h3}".strip(" >"), current_chunk_type)
                    buffer = []
                    is_in_table = True
                    current_chunk_type = "table"
                buffer.append(line)

            else:
                if is_in_table:
                    # End of table
                    flush_buffer(buffer, f"{current_h1} > {current_h2} > {current_h3}".strip(" >"), "table")
                    buffer = []
                    is_in_table = False
                    current_chunk_type = "text"
                buffer.append(line)

        # Final flush
        active_title = f"{current_h1} > {current_h2} > {current_h3}".strip(" >")
        flush_buffer(buffer, active_title, current_chunk_type if not is_in_table else "table")

        return chunks

    def _parse_pdf_structure(self, file_path: str, filename: str, collection: str, access_roles: List[str]) -> List[Dict[str, Any]]:
        # Fallback PDF structural extractor using PyPDF2 or Docling if installed
        try:
            import PyPDF2
            chunks = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text.strip():
                        continue
                    section_title = f"Page {idx + 1}"
                    context_prefix = f"[Document: {filename} | Context: {section_title}]\n"
                    full_text = context_prefix + text.strip()
                    chunks.append({
                        "text": full_text,
                        "source_document": filename,
                        "collection": collection,
                        "access_roles": access_roles,
                        "section_title": section_title,
                        "chunk_type": "text"
                    })
            return chunks
        except Exception as e:
            print(f"Error parsing PDF {filename}: {e}")
            return []

    def _split_large_text(self, text: str, max_words: int) -> List[str]:
        words = text.split()
        sub_chunks = []
        for i in range(0, len(words), max_words - self.overlap_tokens):
            chunk_words = words[i:i + max_words]
            sub_chunks.append(" ".join(chunk_words))
        return sub_chunks
