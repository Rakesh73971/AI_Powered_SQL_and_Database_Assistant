from langchain_core.prompts import ChatPromptTemplate
from app.ai.llm import get_llm
from app.ai.prompts.optimize_prompt import OPTIMIZE_HUMAN_PROMPT, OPTIMIZE_SYSTEM_PROMPT


async def run_optimize_chain(
    dialect: str,
    schema_context: str,
    nl_query: str,
    generated_sql: str,
    execution_time_ms: int,
    error_message: str = None
) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", OPTIMIZE_SYSTEM_PROMPT),
        ("human", OPTIMIZE_HUMAN_PROMPT)
    ])

    chain = prompt | get_llm()

    response = await chain.ainvoke({
        "dialect": dialect,
        "schema_context": schema_context,
        "nl_query": nl_query,
        "generated_sql": generated_sql or "None",
        "execution_time_ms": execution_time_ms if execution_time_ms is not None else 0,
        "error_message": error_message or "None"
    })

    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    texts.append(part["text"])
            return "".join(texts)
        else:
            return str(content)
    else:
        return str(response)
