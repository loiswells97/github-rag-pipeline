import os
from dotenv import load_dotenv
import pymupdf4llm
import json
from chonkie import RecursiveChunker
from openai import OpenAI
import psycopg2
from psycopg2.extras import DictCursor

from ingest_from_github import load_documents

load_dotenv()

GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH")
GITHUB_DIRECTORIES = os.getenv("GITHUB_DIRECTORIES").split(",")
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

def load_documents_metadata(filepath):
    """Load the metadata for a document."""
    try:
        with open(filepath, "r") as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        print(f"Error loading metadata from {filepath}: {e}")
        return []

def chunk_documents(documents, chunk_size=1500):
    """Chunk the documents using the RecursiveChunker."""

    chunker = RecursiveChunker(tokenizer="character", chunk_size=chunk_size)
    chunks = []

    for document in documents:
        try:
            text_chunks = chunker(document["text"])
            for text_chunk in text_chunks:
                chunk = {
                    "text": text_chunk.text,
                    "source": document["source"],
                    "metadata": document["metadata"]
                }
                chunks.append(chunk)
        except Exception as e:
            print(f"Error chunking document {document['source']}: {e}")
            continue
    return chunks

def embed_chunks(chunks):
    chunks_with_embeddings = []
    openai = OpenAI()
    for chunk in chunks:
        try:
            embedding = openai.embeddings.create(
                input=chunk["text"],
                model="text-embedding-3-small"
            )
            chunk["embedding"] = embedding.data[0].embedding
            chunks_with_embeddings.append(chunk)
        except Exception as e:
            print(f"Error embedding chunk {chunk['source']}: {e}")
            continue
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
        try:
            batch = chunks[i:i+batch_size]
            values = [(chunk["text"], chunk["embedding"], chunk["source"], chunk["metadata"]) for chunk in batch]
            cursor.executemany("INSERT INTO documents (text, embedding, source, metadata) VALUES (%s, %s, %s, %s)", values)
            conn.commit()
        except Exception as e:
            print(f"Error storing embedded chunks: {e}")
            continue
    cursor.close()
    conn.close()

def ingest(github_repository, github_branch, github_directories, skip_existing=True):
    docs = load_documents(github_repository, github_branch, github_directories, skip_existing=skip_existing)
    print(f"Loaded {len(docs)} documents")
    chunks = chunk_documents(docs)
    print(f"Created {len(chunks)} chunks")
    chunks_with_embeddings = embed_chunks(chunks)
    print(f"Embedded {len(chunks_with_embeddings)} chunks")
    store_embedded_chunks(chunks_with_embeddings)
    print("Embedded chunks stored successfully")

if __name__ == "__main__":
    ingest(GITHUB_REPOSITORY, GITHUB_BRANCH, GITHUB_DIRECTORIES)