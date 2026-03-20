import os
from dotenv import load_dotenv
import pymupdf4llm
import json
from chonkie import RecursiveChunker
from openai import OpenAI
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()

DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

def load_documents(directory, metadata):
    """Load all pdf files from the directory."""
    documents = []
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT metadata FROM documents")
    existing_documents = cursor.fetchall()
    existing_document_names = [doc["metadata"]["pdf_filename"] for doc in existing_documents]
    cursor.close()
    conn.close()
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith((".pdf")) or filename in existing_document_names:
            print(f"Skipping {filename}")
            continue
        print(f"Processing {filename}")
        filepath = os.path.join(directory, filename)
        md_text = pymupdf4llm.to_markdown(filepath)
        file_metadata = next((item for item in metadata if item["pdf_filename"] == filename), None)
        file_metadata = {k: v for k, v in file_metadata.items() if k != "abstract"}
        file_metadata["published_year"] = file_metadata["published"].split("-")[0]
        file_metadata["published_month"] = file_metadata["published"].split("-")[1]
        file_metadata["published_day"] = file_metadata["published"].split("-")[2]
        documents.append({
            "text": md_text,
            "source": filename,
            "metadata": json.dumps(file_metadata)
        })
    return documents

def load_documents_metadata(filepath):
    """Load the metadata for a document."""
    with open(filepath, "r") as f:
        metadata = json.load(f)
    return metadata

def chunk_documents(documents, chunk_size=1500):
    """Chunk the documents using the RecursiveChunker."""

    chunker = RecursiveChunker(tokenizer="character", chunk_size=chunk_size)
    chunks = []

    for document in documents:
        text_chunks = chunker(document["text"])
        for text_chunk in text_chunks:
            chunk = {
                "text": text_chunk.text,
                "source": document["source"],
                "metadata": document["metadata"]
            }
            chunks.append(chunk)
    return chunks

def embed_chunks(chunks):
    chunks_with_embeddings = []
    openai = OpenAI()
    for chunk in chunks:
        embedding = openai.embeddings.create(
            input=chunk["text"],
            model="text-embedding-3-small"
        )
        chunk["embedding"] = embedding.data[0].embedding
        chunks_with_embeddings.append(chunk)
    return chunks_with_embeddings

def store_embedded_chunks(chunks, batch_size=500):
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        values = [(chunk["text"], chunk["embedding"], chunk["source"], chunk["metadata"]) for chunk in batch]
        cursor.executemany("INSERT INTO documents (text, embedding, source, metadata) VALUES (%s, %s, %s, %s)", values)
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    metadata = load_documents_metadata(f"{DOCUMENTS_DIR}/metadata.json")
    docs = load_documents(f"{DOCUMENTS_DIR}/pdfs", metadata)
    print(f"Loaded {len(docs)} documents")
    chunks = chunk_documents(docs)
    print(f"Created {len(chunks)} chunks")
    chunks_with_embeddings = embed_chunks(chunks)
    print(f"Embedded {len(chunks_with_embeddings)} chunks")
    store_embedded_chunks(chunks_with_embeddings)
    print("Embedded chunks stored successfully")