import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.db.config import settings
from app.ai.llm import get_embeddings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        """
        Embeds a list of schema documents using the configured Google Generative AI Embeddings.
        """
        embeddings_model = get_embeddings()
        return embeddings_model.embed_documents(input)

# Resolve persistent directory path for ChromaDB
persist_dir = settings.chroma_persist_dir
if not os.path.isabs(persist_dir):
    # Make it absolute relative to the workspace root directory of the application
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    persist_dir = os.path.join(parent_dir, persist_dir)

os.makedirs(persist_dir, exist_ok=True)

# Initialize persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path=persist_dir)

def get_schema_collection():
    """
    Creates or retrieves the ChromaDB collection for database schemas.
    """
    return chroma_client.get_or_create_collection(
        name="database_schemas",
        embedding_function=GeminiEmbeddingFunction()
    )

def index_table_schema(connection_id: int, table_name: str, column_definitions: list, sample_values: list) -> str:
    """
    Vectorizes a table's column definitions and sample values, and stores them in ChromaDB.
    """
    collection = get_schema_collection()
    
    # Format column descriptions
    col_lines = []
    for col in column_definitions:
        pk_indicator = " (Primary Key)" if col.get("pk") else ""
        col_lines.append(f"  - {col['name']} ({col['type']}){pk_indicator}")
    col_str = "\n".join(col_lines)
    
    # Format sample values representation
    sample_str = str(sample_values) if sample_values else "None"
    
    # Formulate complete schema document
    document_text = (
        f"Table: {table_name}\n"
        f"Columns:\n{col_str}\n"
        f"Sample Data Preview:\n{sample_str}"
    )
    
    doc_id = f"conn_{connection_id}_{table_name}"
    
    # Upsert the document and metadata into the collection
    collection.upsert(
        ids=[doc_id],
        documents=[document_text],
        metadatas=[{
            "connection_id": connection_id,
            "table_name": table_name
        }]
    )
    return doc_id

def delete_connection_schemas(connection_id: int):
    """
    Deletes all vector schema documents associated with a database connection.
    """
    collection = get_schema_collection()
    
    # Fetch existing IDs for this connection
    results = collection.get(
        where={"connection_id": connection_id}
    )
    
    if results and results.get("ids"):
        collection.delete(ids=results["ids"])

def retrieve_relevant_schemas(connection_id: int, question: str, limit: int = 3) -> list[str]:
    """
    Performs similarity search on database schemas in ChromaDB to retrieve relevant context.
    """
    collection = get_schema_collection()
    
    results = collection.query(
        query_texts=[question],
        where={"connection_id": connection_id},
        n_results=limit
    )
    
    schemas = []
    if results and results.get("documents") and len(results["documents"]) > 0:
        schemas = results["documents"][0]
    return schemas
