from typing import TypedDict, List, Optional, Dict

class EmailState(TypedDict):
    emails: List[str]
    subject: str
    prompt: Optional[str]
    content: Optional[str]
    
    # Personalization Fields
    sender_name: str
    sender_title: str
    
    # Theme Fields (NEW)
    theme_mode: str
    custom_html_template: Optional[str]
    
    # Image Generation Fields
    auto_generate_image_prompt: bool 
    image_prompt: Optional[str]      
    attachment_name: Optional[str]   
    attachment_data: Optional[bytes] 
    
    # Credentials
    smtp_server: str
    smtp_port: int
    smtp_email: str
    smtp_password: str
    gemini_api_key: str  
    results: List[Dict[str, str]]