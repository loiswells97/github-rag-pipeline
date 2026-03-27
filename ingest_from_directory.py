import os
from dotenv import load_dotenv
import pymupdf4llm
import json
from chonkie import RecursiveChunker
from openai import OpenAI
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()

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
        try:
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
        except Exception as e:
            print(f"Error loading document {filename}: {e}")
            continue
    return documents