from langchain_core.prompts import ChatPromptTemplate
from app.ai.llm import get_llm
from app.ai.prompts.sql_prompt import SQL_HUMAN_PROMPT, SQL_SYSTEM_PROMPT


async def run_sql_chain(dialect: str, schema_context: str, question: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SQL_SYSTEM_PROMPT),
        ("human", SQL_HUMAN_PROMPT)
    ])

    chain = prompt | get_llm()

    response = await chain.ainvoke({
        "dialect": dialect,
        "schema_context": schema_context,
        "question": question
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
            sql = "".join(texts)
        else:
            sql = str(content)
    else:
        sql = str(response)

    sql = sql.strip()

    # strip markdown code blocks if the LLM added them
    if sql.startswith("```"):
        lines = sql.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        sql = "\n".join(lines).strip()
        
    return sql