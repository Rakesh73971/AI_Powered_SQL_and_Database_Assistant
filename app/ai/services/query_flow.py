import time
import re
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.query_history import QueryHistory, QueryStatus, Feedback
from app.models.database_connection import DatabaseConnection
from app.services.connection_service import get_connection_or_404
from app.services.query_service import create_query_history
from app.ai.rag import retrieve_relevant_schemas
from app.ai.chains.sql_chain import run_sql_chain
from app.ai.chains.explain_chain import run_explain_chain
from app.services.schema_service import serialize_value

def is_sql_safe(sql: str) -> bool:
    """
    Strict validation to ensure only read-only SELECT and WITH statements are executed.
    Blocks queries containing destructive operations (DROP, DELETE, UPDATE, ALTER, etc.)
    and handles comment cleaning to block injection attempts.
    """
    forbidden_keywords = ["drop", "delete", "update", "insert", "alter", "truncate", "create", "grant", "revoke"]
    
    # Strip comments to prevent safety filter bypass
    clean_sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    clean_sql = re.sub(r'/\*.*?\*/', '', clean_sql, flags=re.DOTALL)
    
    clean_sql = clean_sql.strip().lower()
    
    # Check tokens to prevent matching word prefixes (e.g. "update" vs "updated_at")
    tokens = re.findall(r'\b\w+\b', clean_sql)
    for kw in forbidden_keywords:
        if kw in tokens:
            return False
            
    # Verify the query starts with safe query keywords
    if not (clean_sql.startswith("select") or clean_sql.startswith("with")):
        return False
        
    return True

def _execute_dynamic_sql(connection_url: str, generated_sql: str) -> tuple[list, list]:
    temp_engine = create_engine(connection_url)
    with temp_engine.connect() as temp_conn:
        res = temp_conn.execute(text(generated_sql))
        # Fetch up to 100 rows for counting and previewing
        rows = res.fetchmany(100)
        columns = list(res.keys()) if res.keys() else []
        return rows, columns

async def run_ai_query_flow(
    db: AsyncSession,
    connection_id: int,
    nl_query: str,
    user_id: int
) -> QueryHistory:
    """
    Ties together the entire AI flow:
    1. Fetches connection & retrieves schemas via ChromaDB schema RAG.
    2. Runs the Text-to-SQL LLM chain.
    3. Runs safety guardrails check.
    4. Runs query on the connection's engine & captures results preview and performance.
    5. Runs the LLM explanation chain on query results.
    6. Persists the historical record in the PostgreSQL metadata db.
    """
    # 1. Fetch connection
    connection = await get_connection_or_404(db, connection_id, user_id)
    
    # 2. Retrieve schemas using RAG
    relevant_schemas = await asyncio.to_thread(retrieve_relevant_schemas, connection_id, nl_query, limit=3)
    schema_context = "\n\n".join(relevant_schemas) if relevant_schemas else "No schemas indexed. Please index your database."
    
    # 3. Generate SQL using the SQL generation chain
    try:
        generated_sql = await run_sql_chain(
            dialect=connection.db_type.value,
            schema_context=schema_context,
            question=nl_query
        )
    except Exception as exc:
        return await create_query_history(
            db=db,
            connection_id=connection_id,
            nl_query=nl_query,
            generated_sql=None,
            status_val=QueryStatus.FAILED,
            user_id=user_id,
            error_message=f"SQL Generation Error: {exc}"
        )
        
    # 4. Safety validation
    if not is_sql_safe(generated_sql):
        return await create_query_history(
            db=db,
            connection_id=connection_id,
            nl_query=nl_query,
            generated_sql=generated_sql,
            status_val=QueryStatus.BLOCKED,
            user_id=user_id,
            error_message="Query blocked: Unsafe or non-SELECT SQL statement detected."
        )
        
    # 5. Execute SQL
    start_time = time.time()
    result_preview = []
    row_count = 0
    status_val = QueryStatus.SUCCESS
    error_message = None
    
    try:
        rows, columns = await asyncio.to_thread(_execute_dynamic_sql, connection.sqlalchemy_url, generated_sql)
        row_count = len(rows)
        
        # Format rows as serialized dicts
        for row in rows[:5]:
            row_dict = {}
            for col, val in zip(columns, row):
                row_dict[col] = serialize_value(val)
            result_preview.append(row_dict)
    except Exception as exc:
        status_val = QueryStatus.FAILED
        error_message = str(exc)
        
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    # 6. Generate plain English explanation of the results
    ai_explanation = None
    if status_val == QueryStatus.SUCCESS:
        try:
            preview_str = str(result_preview)
            ai_explanation = await run_explain_chain(
                question=nl_query,
                sql=generated_sql,
                results=preview_str
            )
        except Exception as exc:
            ai_explanation = f"Explanation generation failed: {exc}"
            
    # 7. Create history record in DB with schema context
    db_history = QueryHistory(
        user_id=user_id,
        connection_id=connection_id,
        nl_query=nl_query,
        generated_sql=generated_sql,
        execution_time_ms=execution_time_ms if status_val == QueryStatus.SUCCESS else None,
        row_count=row_count if status_val == QueryStatus.SUCCESS else None,
        result_preview=result_preview if status_val == QueryStatus.SUCCESS else None,
        ai_explanation=ai_explanation,
        status=status_val,
        error_message=error_message,
        schema_context_used=relevant_schemas,
        feedback=Feedback.NONE
    )
    db.add(db_history)
    await db.commit()
    await db.refresh(db_history)
    return db_history
