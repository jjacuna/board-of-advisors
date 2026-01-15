"""
Knowledge Base module for RAG (Retrieval Augmented Generation)
Handles document upload, chunking, embedding, and retrieval.
"""

import os
import re
import hashlib
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Pinecone settings
PINECONE_INDEX = "board-of-directors"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# Chunking settings
CHUNK_SIZE = 500  # tokens
CHUNK_OVERLAP = 50  # tokens


def get_pinecone_index():
    """Initialize and return Pinecone index."""
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY environment variable is not set")

    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Create index if it doesn't exist
    if PINECONE_INDEX not in pc.list_indexes().names():
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )

    return pc.Index(PINECONE_INDEX)


def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from Word document."""
    from docx import Document

    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def extract_text_from_file(file_path: str, filename: str) -> str:
    """Extract text from various file types."""
    ext = filename.lower().split('.')[-1]

    if ext == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext == 'docx':
        return extract_text_from_docx(file_path)
    elif ext in ['txt', 'md', 'markdown']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    import tiktoken

    # Use cl100k_base tokenizer (same as text-embedding-3-small)
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)

        # Clean up the chunk
        chunk_text = chunk_text.strip()
        if chunk_text:
            chunks.append(chunk_text)

        start = end - overlap

    return chunks


def generate_chunk_id(doc_id: int, chunk_index: int) -> str:
    """Generate unique ID for a chunk."""
    return f"doc_{doc_id}_chunk_{chunk_index}"


def process_document(doc_id: int, file_path: str, filename: str) -> int:
    """Process a document: extract text, chunk, embed, and store in Pinecone."""
    # Extract text
    text = extract_text_from_file(file_path, filename)

    if not text.strip():
        raise ValueError("No text could be extracted from the document")

    # Chunk the text
    chunks = chunk_text(text)

    if not chunks:
        raise ValueError("Document is too short to process")

    # Get Pinecone index
    index = get_pinecone_index()

    # Process each chunk
    vectors = []
    for i, chunk in enumerate(chunks):
        chunk_id = generate_chunk_id(doc_id, i)
        embedding = get_embedding(chunk)

        vectors.append({
            "id": chunk_id,
            "values": embedding,
            "metadata": {
                "doc_id": doc_id,
                "chunk_index": i,
                "text": chunk[:1000],  # Store first 1000 chars of chunk
                "filename": filename
            }
        })

    # Upsert vectors in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)

    return len(chunks)


def search_knowledge(query: str, top_k: int = 5) -> List[Dict]:
    """Search knowledge base for relevant chunks."""
    try:
        # Get query embedding
        query_embedding = get_embedding(query)

        # Search Pinecone
        index = get_pinecone_index()
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )

        # Format results
        chunks = []
        for match in results.matches:
            if match.score > 0.3:  # Only include relevant matches
                chunks.append({
                    "text": match.metadata.get("text", ""),
                    "filename": match.metadata.get("filename", "Unknown"),
                    "score": match.score
                })

        return chunks

    except Exception as e:
        print(f"Knowledge search error: {e}")
        return []


def delete_document_vectors(doc_id: int):
    """Delete all vectors for a document from Pinecone."""
    try:
        index = get_pinecone_index()

        # Delete by prefix (all chunks for this doc)
        # Note: Pinecone serverless requires listing then deleting
        prefix = f"doc_{doc_id}_chunk_"

        # List vectors with this prefix and delete them
        # This is a workaround since serverless doesn't support delete by prefix directly
        for i in range(1000):  # Assume max 1000 chunks per doc
            chunk_id = f"{prefix}{i}"
            try:
                index.delete(ids=[chunk_id])
            except:
                break

    except Exception as e:
        print(f"Error deleting vectors: {e}")


def get_context_for_query(query: str) -> str:
    """Get relevant context from knowledge base for a query."""
    chunks = search_knowledge(query, top_k=5)

    if not chunks:
        return ""

    context_parts = []
    for chunk in chunks:
        context_parts.append(f"[From: {chunk['filename']}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    return f"""
RELEVANT CONTEXT FROM KNOWLEDGE BASE:
{context}

---
Use the above context to inform your response when relevant.
"""


def check_knowledge_base_configured() -> bool:
    """Check if knowledge base is properly configured."""
    return bool(OPENAI_API_KEY and PINECONE_API_KEY)
