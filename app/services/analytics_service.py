from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.query_history import QueryHistory, QueryStatus, Feedback
from app.models.database_connection import DatabaseConnection
from app.ai.chains.optimize_chain import run_optimize_chain


def get_admin_analytics(db: Session, slow_threshold_ms: int = 1000) -> dict:
    """
    Calculates query performance KPIs, feedback summary, frequent queries,
    and identifies slow/failed queries for admin review.
    """
    # 1. Base counts
    total_queries = db.query(QueryHistory).count()
    
    # 2. Query Status metrics
    status_stats = db.query(
        QueryHistory.status,
        func.count(QueryHistory.id)
    ).group_by(QueryHistory.status).all()
    status_counts = {s.value: count for s, count in status_stats}
    for q_status in QueryStatus:
        if q_status.value not in status_counts:
            status_counts[q_status.value] = 0
            
    # 3. User Feedback metrics
    feedback_stats = db.query(
        QueryHistory.feedback,
        func.count(QueryHistory.id)
    ).group_by(QueryHistory.feedback).all()
    feedback_counts = {f.value: count for f, count in feedback_stats}
    for q_feedback in Feedback:
        if q_feedback.value not in feedback_counts:
            feedback_counts[q_feedback.value] = 0

    # 4. Query execution speeds (only for successful queries)
    speed_stats = db.query(
        func.avg(QueryHistory.execution_time_ms),
        func.min(QueryHistory.execution_time_ms),
        func.max(QueryHistory.execution_time_ms)
    ).filter(
        QueryHistory.status == QueryStatus.SUCCESS,
        QueryHistory.execution_time_ms.isnot(None)
    ).first()
    
    avg_speed = round(speed_stats[0], 2) if speed_stats and speed_stats[0] is not None else 0.0
    min_speed = speed_stats[1] if speed_stats and speed_stats[1] is not None else 0
    max_speed = speed_stats[2] if speed_stats and speed_stats[2] is not None else 0

    # 5. Most frequent queries
    freq_queries = db.query(
        QueryHistory.nl_query,
        func.count(QueryHistory.id).label("freq")
    ).group_by(
        QueryHistory.nl_query
    ).order_by(
        func.count(QueryHistory.id).desc()
    ).limit(10).all()
    
    frequent_list = [
        {"nl_query": q[0], "count": q[1]} for q in freq_queries
    ]

    # 6. Slow queries (succeeded, but execution time > threshold)
    slow_queries = db.query(QueryHistory).filter(
        QueryHistory.status == QueryStatus.SUCCESS,
        QueryHistory.execution_time_ms > slow_threshold_ms
    ).order_by(
        QueryHistory.execution_time_ms.desc()
    ).limit(20).all()

    # 7. Failed queries
    failed_queries = db.query(QueryHistory).filter(
        QueryHistory.status == QueryStatus.FAILED
    ).order_by(
        QueryHistory.created_at.desc()
    ).limit(20).all()

    return {
        "summary": {
            "total_queries": total_queries,
            "status_counts": status_counts,
            "feedback_counts": feedback_counts,
        },
        "performance": {
            "avg_execution_time_ms": avg_speed,
            "min_execution_time_ms": min_speed,
            "max_execution_time_ms": max_speed,
            "slow_threshold_ms": slow_threshold_ms,
        },
        "most_frequent_queries": frequent_list,
        "slow_queries": [
            {
                "id": q.id,
                "user_id": q.user_id,
                "connection_id": q.connection_id,
                "nl_query": q.nl_query,
                "generated_sql": q.generated_sql,
                "execution_time_ms": q.execution_time_ms,
                "row_count": q.row_count,
                "created_at": q.created_at
            } for q in slow_queries
        ],
        "failed_queries": [
            {
                "id": q.id,
                "user_id": q.user_id,
                "connection_id": q.connection_id,
                "nl_query": q.nl_query,
                "generated_sql": q.generated_sql,
                "error_message": q.error_message,
                "created_at": q.created_at
            } for q in failed_queries
        ]
    }


def optimize_query_by_id(db: Session, query_id: int) -> dict:
    """
    Fetches the query history record, formats the schema context,
    runs the optimization LangChain model, and returns optimization tips.
    """
    record = db.query(QueryHistory).filter(QueryHistory.id == query_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query history record not found."
        )
    
    connection = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == record.connection_id
    ).first()
    
    dialect = connection.db_type.value if connection else "postgresql"
    
    # Extract schema context used during query generation
    schema_ctx = "No schemas were cached or used during this query run."
    if record.schema_context_used:
        if isinstance(record.schema_context_used, list):
            schema_ctx = "\n\n".join(record.schema_context_used)
        else:
            schema_ctx = str(record.schema_context_used)

    # Run LangChain optimization
    try:
        optimization_insights = run_optimize_chain(
            dialect=dialect,
            schema_context=schema_ctx,
            nl_query=record.nl_query,
            generated_sql=record.generated_sql,
            execution_time_ms=record.execution_time_ms,
            error_message=record.error_message
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query optimization recommendations: {exc}"
        )

    return {
        "query_id": record.id,
        "nl_query": record.nl_query,
        "executed_sql": record.generated_sql,
        "execution_time_ms": record.execution_time_ms,
        "status": record.status.value,
        "error_message": record.error_message,
        "dialect": dialect,
        "optimization_suggestions": optimization_insights
    }
