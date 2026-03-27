def log_query(query, metadata_filters, relevance_limit):
    print("-"*30)
    print("Performing vector search with:")
    print(f"Query: {query}")
    print(f"Metadata filters: {metadata_filters}")
    print(f"Relevance limit: {relevance_limit}")
    print("-"*30)

def log_results(results):
    print(f"Found {len(results)} results")
    for result in results:
        print("-"*30)
        print(f"Similarity: {result['similarity']}")
        print(f"Source: {result['source']}")
        # print(f"Title: {result['metadata']['title']}")
        # print(f"Authors: {result['metadata']['authors']}")
        # print(f"Published: {result['metadata']['published']}")
        print(f"Text: {result['text']}")
        print("-"*30)

def log_response(response):
    print(f"Response: {response}")
    print("-"*30)