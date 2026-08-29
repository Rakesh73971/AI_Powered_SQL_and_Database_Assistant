from langchain_core.prompts import ChatPromptTemplate
from app.ai.llm import get_llm
from app.ai.prompts.explain_prompt import EXPLAIN_HUMAN_PROMPT, EXPLAIN_SYSTEM_PROMPT


async def run_explain_chain(question: str, sql: str, results: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAIN_SYSTEM_PROMPT),
        ("human", EXPLAIN_HUMAN_PROMPT)
    ])

    chain = prompt | get_llm()

    response = await chain.ainvoke({
        "question": question,
        "sql": sql,
        "results": results
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
