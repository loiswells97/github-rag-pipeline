import os
import json
from dotenv import load_dotenv
from github import Github
import psycopg2
from psycopg2.extras import DictCursor

load_dotenv()

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

def filter_files(files, directories):
    filtered_files = []
    for directory in directories:
        for file in files:
            if file.startswith(directory + "/"):
                filtered_files.append(file)
    return filtered_files

def delete_document(source):
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("DELETE FROM documents WHERE source = %s", (source,))
    conn.commit()
    cursor.close()
    conn.close()

def load_documents(repository_name, branch_name="main", directories=[], skip_existing=True):
    """Load documents from a GitHub repository."""
    github_client = Github(os.getenv("GITHUB_TOKEN"))
    repo = github_client.get_repo(repository_name)
    branch = repo.get_branch(branch_name)

    documents = []

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT source FROM documents")
    existing_documents = cursor.fetchall()
    existing_document_paths = [doc["source"] for doc in existing_documents]
    for directory in directories:
        response = repo.get_contents(directory, ref=branch_name)
        contents = response if isinstance(response, list) else [response]
        for content in contents:
            if content.path in existing_document_paths:
                if skip_existing:
                    print(f"Skipping {content.path}")
                    continue
                else:
                    # remove the existing document from the database
                    delete_document(content.path)
            if content.type == "file":
                documents.append({
                    "text": content.decoded_content.decode("utf-8"),
                    "source": content.path,
                    "metadata": json.dumps({
                        "repository": repository_name,
                        "branch": branch_name,
                        "name": content.name,
                        "path": content.path,
                        "sha": content.sha,
                        "size": content.size,
                        "type": content.type,
                        "download_url": content.download_url,
                        "git_url": content.git_url,
                        "html_url": content.html_url,
                    })
                })
    cursor.close()
    conn.close()
    return documents