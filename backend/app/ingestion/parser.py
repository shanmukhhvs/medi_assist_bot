import os
import re
from typing import Any, Dict, List

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.hierarchical_chunker import ChunkingDocSerializer, ChunkingSerializerProvider
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.serializer.markdown import MarkdownTableSerializer
from docling_core.types.doc import DocItemLabel, DoclingDocument, SectionHeaderItem, TitleItem
from transformers import AutoTokenizer

from app.RAG.vector_store import DENSE_MODEL

# Map collections to allowed roles
COLLECTION_ROLE_MAP = {
    "general": ["doctor", "nurse", "billing_executive", "technician", "admin"],
    "clinical": ["doctor", "admin"],
    "nursing": ["nurse", "doctor", "admin"],
    "billing": ["billing_executive", "admin"],
    "equipment": ["technician", "admin"]
}

# Token budget per chunk, counted with the dense embedder's own tokenizer. all-MiniLM-L6-v2 truncates input at
# 256 tokens, so a larger chunk would be silently cut at embedding time.
MAX_CHUNK_TOKENS = 256
# HybridChunker budgets the chunk body only; contextualize() then prepends the heading path. The longest heading
# path in the provided documents is 34 tokens (measured), so the body gets MAX_CHUNK_TOKENS - 40; parse_file
# fails loudly if a chunk still exceeds MAX_CHUNK_TOKENS.
HEADING_TOKEN_RESERVE = 40

SUPPORTED_EXTENSIONS = (".pdf", ".md")

# Section numbering used by the provided PDFs: "A. Patient Monitoring ...", "1. Scope", "SOP 4 - IV Cannula ...".
_NUMBERED_SECTION = re.compile(r"^(?:[A-Z]\.|\d+(?:\.\d+)*\.?|SOP\s+\d+\b)\s*\S")


def _restore_heading_levels(doc: DoclingDocument) -> None:
    """
    Docling reports every PDF heading in the provided documents at level 1, so the chunk heading path would be
    just the last heading seen (e.g. "Fault codes", which appears under four devices in the equipment manual).
    Rebuild the hierarchy: first heading = document title (1), numbered section (2), unnumbered sub-heading (3).
    Only applied when all headings share one level; Markdown input keeps its native levels.
    """
    headers = [item for item, _ in doc.iterate_items() if isinstance(item, SectionHeaderItem)]
    if not headers or len({h.level for h in headers}) > 1 or any(isinstance(i, TitleItem) for i, _ in doc.iterate_items()):
        return
    headers[0].level = 1
    for h in headers[1:]:
        h.level = 2 if _NUMBERED_SECTION.match(h.text.strip()) else 3


class _MarkdownTableSerializerProvider(ChunkingSerializerProvider):
    """Serialize tables as Markdown (whole rows, header repeated on every split) instead of Docling's default
    "row, column = value" triplets, which split a dosage or billing row across chunks."""

    def get_serializer(self, doc):
        return ChunkingDocSerializer(doc=doc, table_serializer=MarkdownTableSerializer())


def _chunk_type(doc_items) -> str:
    labels = {item.label for item in doc_items}
    if DocItemLabel.TABLE in labels:
        return "table"
    if DocItemLabel.CODE in labels:
        return "code"
    if labels and labels <= {DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE}:
        return "heading"
    return "text"


class DoclingHybridParser:
    """
    Structure-aware ingestion: Docling parses PDF/Markdown into a DoclingDocument (headings, tables, lists, code),
    then Docling's HybridChunker splits along that structure first and enforces the token budget second.
    Each chunk's embedded text is HybridChunker.contextualize(chunk), i.e. its heading path + body.
    """

    def __init__(self, max_tokens: int = MAX_CHUNK_TOKENS):
        # The provided PDFs have a text layer, so OCR is off; TableFormer table-structure recognition stays on.
        pdf_options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.MD],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)},
        )
        self.max_tokens = max_tokens
        hf_tokenizer = AutoTokenizer.from_pretrained(DENSE_MODEL)
        self.tokenizer = HuggingFaceTokenizer(tokenizer=hf_tokenizer, max_tokens=max_tokens)
        self.chunker = HybridChunker(
            tokenizer=HuggingFaceTokenizer(tokenizer=hf_tokenizer, max_tokens=max_tokens - HEADING_TOKEN_RESERVE),
            merge_peers=True,
            repeat_table_header=True,
            serializer_provider=_MarkdownTableSerializerProvider(),
        )

    def count_tokens(self, text: str) -> int:
        return self.tokenizer.count_tokens(text)

    def parse_file(self, file_path: str, collection: str) -> List[Dict[str, Any]]:
        if not file_path.lower().endswith(SUPPORTED_EXTENSIONS):
            return []
        filename = os.path.basename(file_path)
        access_roles = COLLECTION_ROLE_MAP[collection]

        doc = self.converter.convert(file_path).document
        _restore_heading_levels(doc)

        chunks = []
        for chunk in self.chunker.chunk(dl_doc=doc):
            text = self.chunker.contextualize(chunk=chunk).strip()
            if not text:
                continue
            if self.count_tokens(text) > self.max_tokens:
                raise ValueError(f"{filename}: chunk exceeds {self.max_tokens} tokens; raise HEADING_TOKEN_RESERVE")
            headings = chunk.meta.headings or [os.path.splitext(filename)[0].replace("_", " ").title()]
            chunks.append({
                "text": text,
                "source_document": filename,
                "collection": collection,
                "access_roles": access_roles,
                "section_title": " > ".join(headings),
                "chunk_type": _chunk_type(chunk.meta.doc_items),
            })
        return chunks
