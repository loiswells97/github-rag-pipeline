import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI
import psycopg2
from psycopg2.extras import DictCursor
from pgvector.psycopg2 import register_vector
import numpy as np
import anthropic
from log import log_query, log_results, log_response

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

openai = OpenAI()

def perform_vector_search(query, k=5, metadata_filters={}, relevance_limit=0.5):
    embedding = openai.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = np.array(embedding.data[0].embedding)
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    register_vector(conn)
    cursor = conn.cursor(cursor_factory=DictCursor)
    if metadata_filters:
        cursor.execute("SELECT *, 1 - (embedding <=> %s) AS similarity FROM documents WHERE metadata @> %s AND 1 - (embedding <=> %s) >= %s ORDER BY similarity DESC LIMIT %s", (query_embedding, json.dumps(metadata_filters), query_embedding, relevance_limit, k))
    else:
        cursor.execute("SELECT *, 1 - (embedding <=> %s) AS similarity FROM documents WHERE 1 - (embedding <=> %s) >= %s ORDER BY similarity DESC LIMIT %s", (query_embedding, query_embedding, relevance_limit, k))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def generate_response(question, chunks):
    """Ask Claude to answer the question using the retrieved context."""
    client = anthropic.Anthropic()

    context = ""
    for chunk in chunks:
        context += f"\n--- Similarity: {chunk['similarity']} (Source: {chunk['source']}, Metadata: {chunk['metadata']} ) ---\n{chunk['text']}\n"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="You are a helpful assistant. Answer questions based only on the provided context. If the context doesn't contain enough information to answer, say so. Include citations from the context in academic citation format for every assertion made in the answer.",
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            }
        ],
    )

    return response.content[0].text

def rag_query(query, metadata_filters={}, relevance_limit=0.5, with_logging=False):
    if with_logging:
        log_query(query, metadata_filters, relevance_limit)
    results = perform_vector_search(query, metadata_filters=metadata_filters, relevance_limit=relevance_limit)
    if with_logging:
        log_results(results)
    response = generate_response(query, results)
    if with_logging:
        log_response(response)
    return response
