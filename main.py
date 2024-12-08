from fastapi import FastAPI, HTTPException, Path, Query,Body
from pydantic import BaseModel
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory  # Updated import
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import uvicorn
from langchain.schema import BaseMessage, HumanMessage, AIMessage, BaseChatMessageHistory
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict
# from langserve import add_routes
from prompts import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the LLM
llm = ChatGroq(
    model_name="llama3-8b-8192",
    api_key='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'
)

# Initialize FastAPI app
app = FastAPI(
    title="SRS app",
    version="1.0",
    description="SRS generation app"
)

# Storage
chat_store: Dict[str, ChatMessageHistory] = {}
long_term_memory: Dict[str, List[str]] = {}

memory_inheritance = {
    "introduction": ["introduction"],
    # "functional_requirements": ["introduction"],
    # "non_functional_requirements": ["functional_requirements"],
    "usecases": ["introduction"],
    "subusecases": ["usecases"],
    "user_type":['usecases','subusecases'],
    "database_design": ["usecases","introduction", "business_workflow"],
    "business_workflow": ["business_rules","usecases","subusecases"],
    "business_rules": ["subusecases","usecases","subusecases"],
    "user_interface": [ "usecases","subusecases"],
    # "reports_and_mis_catalogue": ["functional_requirements", "business_rules", "database_design"],
    # "er_diagram": ["database_design"],
    # "glossary_and_acronyms": ["introduction", "functional_requirements", "non_functional_requirements", "business_rules", "reports_and_mis_catalogue"],
    # "references": ["introduction", "functional_requirements", "non_functional_requirements", "business_rules", "reports_and_mis_catalogue"]
}

chat_inheritance = memory_inheritance.copy()

# ##For single chat
# def get_chat_history_for_prompt(session_id: str):
#     if session_id not in chat_store:
#         chat_store[session_id] = ChatMessageHistory()
#     return chat_store[session_id]

# def get_long_term_memory_for_section(session_id: str):
#     return ". ".join(get_long_term_memory_for_section.get(session_id, []))


# async def message_chat(input_text: str, session_id: str) -> str:
#     """Process a chat message using the appropriate chain."""
#     logger.info(f"Processing chat message for session: {session_id}")
#     if session_id not in chains:
#         raise HTTPException(status_code=400, detail=f"Invalid session ID: {session_id}")

#     chain = chains[session_id]
#     long_term_mem = get_long_term_memory_for_section(session_id)

#     try:
#         response = await chain.ainvoke(
#             {"input": input_text, "long_term_memory": long_term_mem},
#             config={"configurable": {"session_id": session_id}}
#         )

#         update_long_term_memory(session_id, input_text, response.content)
#         return response.content
#     except Exception as e:
#         logger.error(f"Chat processing error: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")



def get_chat_history(session_id: str) -> BaseChatMessageHistory:
    """Get chat history for a session, including inherited messages."""
    logger.info(f"Getting chat history for session: {session_id}")
    if session_id not in chat_store:
        chat_store[session_id] = ChatMessageHistory()

    session_history = chat_store[session_id]

    if session_id in chat_inheritance:
        for inherited_session in chat_inheritance[session_id]:
            if inherited_session in chat_store:
                last_message = get_last_conversation(inherited_session)
                if last_message:
                    session_history.add_message(
                        AIMessage(content=f"Inherited from {inherited_session}: {last_message.content}")
                    )

    return session_history

def get_last_conversation(session_id: str) -> BaseMessage:
    """Get the last message from a session's conversation history."""
    logger.info(f"Getting last conversation for session: {session_id}")
    history = chat_store.get(session_id)
    if history and history.messages:
        return history.messages[-1]
    return None

def create_chat_prompt_template(template_name: str) -> ChatPromptTemplate:
    """Create a chat prompt template with the given system message."""
    logger.info(f"Creating chat prompt template for: {template_name}")
    return ChatPromptTemplate.from_messages([
        ("system", template_name),
        ("system", "Long-term memory: {long_term_memory}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

# Create prompt templates
prompt_templates = {
    "introduction": create_chat_prompt_template(introduction),
    "usecases": create_chat_prompt_template(usecases),
    "subusecases":create_chat_prompt_template(subusecases_template),
    "user_type":create_chat_prompt_template(software_users),
    "business_rules":create_chat_prompt_template(business_rules_template),
    "business_workflow":create_chat_prompt_template(business_workflow),
    "database_design":create_chat_prompt_template(database),
    "user_interface":create_chat_prompt_template(user_interface)
}

# Create chains
chains = {
    "introduction": RunnableWithMessageHistory(
        prompt_templates["introduction"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "usecases": RunnableWithMessageHistory(
        prompt_templates["usecases"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "subusecases": RunnableWithMessageHistory(
        prompt_templates["subusecases"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "business_rules": RunnableWithMessageHistory(
        prompt_templates["business_rules"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "business_workflow": RunnableWithMessageHistory(
        prompt_templates["business_workflow"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "database_design": RunnableWithMessageHistory(
        prompt_templates["database_design"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "user_interface": RunnableWithMessageHistory(
        prompt_templates["user_interface"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    ),
    "user_type": RunnableWithMessageHistory(
        prompt_templates["user_type"] | llm,
        get_chat_history,
        input_messages_key="input",
        history_messages_key="history"
    )
    }

def get_long_term_memory(session_id: str) -> str:
    """Get long-term memory for a session, including inherited memories."""
    logger.info(f"Getting long-term memory for session: {session_id}")
    memories = []

    if session_id in long_term_memory:
        memories.append(f"Session {session_id} memory: {'. '.join(long_term_memory[session_id])}")

    if session_id in memory_inheritance:
        for inherited_session in memory_inheritance[session_id]:
            if inherited_session in long_term_memory:
                memories.append(f"Inherited from {inherited_session}: {'. '.join(long_term_memory[inherited_session])}")

    return "\n".join(memories)

def update_long_term_memory(session_id: str, input: str, output: str):
    """Update long-term memory for a session."""
    logger.info(f"Updating long-term memory for session: {session_id}")
    if session_id not in long_term_memory:
        long_term_memory[session_id] = []
    if len(input) > 20:
        long_term_memory[session_id].append(f"User said: {input}")
    if len(long_term_memory[session_id]) > 5:
        long_term_memory[session_id] = long_term_memory[session_id][-5:]

async def chat(input_text: str, session_id: str) -> str:
    """Process a chat message using the appropriate chain."""
    logger.info(f"Processing chat message for session: {session_id}")
    if session_id not in chains:
        raise HTTPException(status_code=400, detail=f"Invalid session ID: {session_id}")

    chain = chains[session_id]
    long_term_mem = get_long_term_memory(session_id)

    try:
        response = await chain.ainvoke(
            {"input": input_text, "long_term_memory": long_term_mem},
            config={"configurable": {"session_id": session_id}}
        )

        update_long_term_memory(session_id, input_text, response.content)
        return response.content
    except Exception as e:
        logger.error(f"Chat processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

# Function to edit the most recent AI message
def edit_most_recent_ai_message(chat_store, section_id: str, updated_message: str):
    """Fetches the most recent AI message from a specified section, allows editing, and updates it in the chat store."""
    logger.info(f"Editing most recent AI message for section: {section_id}")
    # Check if the provided section_id exists in the chat_store
    if section_id not in chat_store:
        return {"error": f"Section ID '{section_id}' not found in chat store."}

    # Get the list of messages from the specified section
    section_messages = chat_store[section_id].messages

    # Find the most recent AI message in the specified section
    for message in reversed(section_messages):
        if message.type == 'ai':
            # Update the message with the new content
            message.content = updated_message
            return {"message": f"Message updated to: {message.content}"}

    return {"error": "No AI message found to edit in the specified section."}

# Request model
class UserMessage(BaseModel):
    user_message: str

# Pydantic model for input data
class EditMessageRequest(BaseModel):
    section_id: str
    updated_message: str
class EditMessageWithPromptRequest(BaseModel):
    """Request model to edit a message with a user-specified prompt."""
    message: str
    user_prompt: str

# Supported session types
SUPPORTED_SESSION_TYPES = {
    "introduction",
    "usecases",
    "subusecases",
    "user_type",
    "business_rules",
    "business_workflow",
    "database_design",
    "user_interface",
   
}

@app.post("/chat/{session_type}")
async def handle_chat(
    session_type: str = Path(..., description="The type of chat session", examples=["introduction", "usecases"]),
    request: UserMessage = None,
):
    """Unified chat endpoint with session type passed as a URL parameter."""
    try:
        # Validate session type
        if session_type not in SUPPORTED_SESSION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid session type: {session_type}. Supported types are {', '.join(SUPPORTED_SESSION_TYPES)}.",
            )

        # Process the chat request
        message = await chat(request.user_message, session_type)
        return {"message": message}

    except HTTPException as he:
        logger.error(f"HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# FastAPI endpoint to edit the most recent AI message
@app.put("/edit-ai-message/")
async def edit_ai_message(request: EditMessageRequest):
    # Call the function to edit the message in the chat store
    result = edit_most_recent_ai_message(chat_store, request.section_id, request.updated_message)

    if 'error' in result:
        logger.error(f"Error editing AI message: {result['error']}")
        raise HTTPException(status_code=400, detail=result['error'])
    return result


# Run the FastAPI server
if __name__ == "__main__":
    logger.info("Starting FastAPI server")
    uvicorn.run(app, host="127.0.0.1", port=8000)
