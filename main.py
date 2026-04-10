from fastapi import FastAPI, Request
from query import rag_query
from parsing import parse_metadata
import os
import json
from ingest import ingest
from ingest_from_github import delete_document, filter_files

app = FastAPI()

GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH")
GITHUB_DIRECTORIES = os.getenv("GITHUB_DIRECTORIES").split(",")

@app.get("/")
async def root(request: Request):
    # Extract all query params into a dict except for one
    query = request.query_params.get("q")
    relevance_limit = float(request.query_params.get("relevance_limit", 0.5))
    metadata_filters = {k: parse_metadata(v) for k, v in request.query_params.items() if k not in ["q", "relevance_limit"]}
    if not query:
        return {"error": "Query parameter 'q' is required"}
    response = rag_query(query, metadata_filters=metadata_filters, relevance_limit=relevance_limit, with_logging=True)
    return {"query": query, "relevance_limit": relevance_limit, "metadata_filters": metadata_filters, "response": response}

@app.post("/github_webhooks")
async def github_webhooks(request: Request):
    # body = await request.json()
    # print(body)
    body = await request.json()
    print('the body is:')
    print(body)

    commits = body.get("commits")

    added_or_modified_files = []
    removed_files = []
    
    for commit in commits: 
        added_or_modified_files.extend(commit.get("added"))
        added_or_modified_files.extend(commit.get("modified"))
        removed_files.extend(commit.get("removed"))
        
    # filter added, modified and removed files based on github directories list
    filtered_added_or_modified_files = list(set(filter_files(added_or_modified_files, GITHUB_DIRECTORIES)))
    filtered_removed_files = list(set(filter_files(removed_files, GITHUB_DIRECTORIES)))

    for file in filtered_removed_files:
        delete_document(file)
    
    ingest(GITHUB_REPOSITORY, GITHUB_BRANCH, filtered_added_or_modified_files, skip_existing=False)
        

    return {"message": "Webhook received"}