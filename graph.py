from langgraph.graph import StateGraph, START, END
from state import EmailState
from nodes import generate_email_content, create_image_prompt, generate_or_fetch_image, dispatch_emails

def build_graph():
    workflow = StateGraph(EmailState)
    
    workflow.add_node("generate_content", generate_email_content)
    workflow.add_node("create_image_prompt", create_image_prompt)     # NEW NODE
    workflow.add_node("generate_image", generate_or_fetch_image)
    workflow.add_node("dispatch_emails", dispatch_emails)
    
    workflow.add_edge(START, "generate_content")
    workflow.add_edge("generate_content", "create_image_prompt")      # Inserted into flow
    workflow.add_edge("create_image_prompt", "generate_image")        # Inserted into flow
    workflow.add_edge("generate_image", "dispatch_emails")
    workflow.add_edge("dispatch_emails", END)
    
    return workflow.compile()