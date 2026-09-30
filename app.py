import os
import re
import email.utils
import streamlit as st
from dotenv import load_dotenv
from graph import build_graph

load_dotenv()

def main():
    st.set_page_config(page_title="AI Email Dispatcher", page_icon="✉️", layout="wide")
    st.title("✉️ AI Agent Email Dispatcher")
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.subheader("API Keys")
        gemini_key = st.text_input("Google API Key (Text & Image)", value=os.getenv("GOOGLE_API_KEY", ""), type="password")
        
        st.subheader("SMTP Credentials")
        smtp_email = st.text_input("Sender Email", value=os.getenv("SMTP_EMAIL", ""))
        smtp_password = st.text_input("App Password", value=os.getenv("SMTP_PASSWORD", ""), type="password")
        smtp_server = st.text_input("SMTP Server", value=os.getenv("SMTP_SERVER", "smtp.gmail.com"))
        default_port = int(os.getenv("SMTP_PORT", 587))
        smtp_port = st.number_input("SMTP Port", value=default_port, step=1)
        
    tab1, tab2, tab3, tab4 = st.tabs(["📨 Setup & Recipients", "📝 Text Content", "🎨 Theme & Styling", "🖼️ Image Attachment"])
    
    with tab1:
        st.subheader("Sender Personalization")
        colA, colB = st.columns(2)
        with colA:
            sender_name = st.text_input("Your Name", placeholder="e.g., Hafiz Muhammad Asad Ijaz")
        with colB:
            sender_title = st.text_input("Your Title / Company", placeholder="e.g., Data Scientist | The Aura Accessories")
        if not sender_name.strip():
            st.caption("⚠️ No name set — emails will be signed as 'The Team' until you add one.")
            
        st.divider()
        st.subheader("Recipients & Subject")
        subject = st.text_input("Email Subject", placeholder="Enter the subject line here (Use [Recipient Name] for dynamic insertion)")
        
        col_recip1, col_recip2 = st.columns([1, 1])
        with col_recip1:
            email_input = st.text_area(
                "Type Recipients Manually", 
                placeholder="Format: Name <email@domain.com>\nExample:\nAbdullah <abdullah@example.com>\njane@example.com", 
                height=150
            )
        with col_recip2:
            st.markdown("**Or Upload a .txt file:**")
            st.caption("The file should contain emails separated by commas or newlines.")
            uploaded_email_file = st.file_uploader("Upload Mailing List", type=['txt'])
        
    with tab2:
        input_mode = st.radio("How would you like to create the email body?", ["Generate from Prompt", "Provide Exact Content"])
        prompt, exact_content = None, None
        
        if input_mode == "Generate from Prompt":
            prompt = st.text_area("AI Prompt", placeholder="e.g., Write a follow-up email thanking them...", height=250)
            st.info("💡 The AI will automatically use your Name and Title from the first tab and avoid using raw placeholders.")
        else:
            exact_content = st.text_area("Email Content", placeholder="Type the exact email body here...\nYou can use [Recipient Name], [Your Name], and [Your Title/Company]", height=250)

    with tab3:
        st.subheader("Email Design")
        theme_mode = st.radio("Choose your Email Theme:", ["Simple (Default)", "Custom HTML Theme"])
        
        custom_html_template = None
        if theme_mode == "Custom HTML Theme":
            st.info("Provide your custom HTML wrapper by pasting it or uploading a file. **You MUST include `{{content}}`** exactly where you want the main email text to appear.")
            
            theme_source = st.radio("Theme source", ["Paste HTML", "Upload .html file"], horizontal=True)
            
            default_html = (
                "<html>\n"
                "<body style='background-color: #f4f7f6; padding: 30px; font-family: Arial, sans-serif;'>\n"
                "  <div style='max-width: 600px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.05);'>\n"
                "    <div style='text-align: center; margin-bottom: 20px;'>\n"
                "       <h2 style='color: #2c3e50;'>Company Newsletter</h2>\n"
                "       <hr style='border: 1px solid #eee;'/>\n"
                "    </div>\n"
                "    <div style='color: #444; line-height: 1.6;'>\n"
                "      {{content}}\n"
                "    </div>\n"
                "    <div style='text-align: center; margin-top: 30px; font-size: 12px; color: #888;'>\n"
                "       <hr style='border: 1px solid #eee;'/>\n"
                "       © 2026 Your Company Name. All rights reserved.\n"
                "    </div>\n"
                "  </div>\n"
                "</body>\n"
                "</html>"
            )
            
            if theme_source == "Upload .html file":
                uploaded_theme_file = st.file_uploader("Upload your theme", type=['html', 'htm'])
                if uploaded_theme_file:
                    custom_html_template = uploaded_theme_file.getvalue().decode("utf-8", errors="replace")
                    with st.expander("Preview uploaded HTML source"):
                        st.code(custom_html_template, language="html")
                    if "{{content}}" not in custom_html_template:
                        st.warning("This file doesn't contain `{{content}}` — add it wherever the email body should go.")
                else:
                    st.caption("No file uploaded yet — pick an .html file, or switch to 'Paste HTML'.")
            else:
                custom_html_template = st.text_area("Custom HTML Code", value=default_html, height=350)

    with tab4:
        attach_mode = st.radio("Image Attachment Mode", [
            "None", 
            "Upload an Image", 
            "Auto-Generate Image (Agent analyzes email content)", 
            "Generate Image (Manual Prompt)"
        ])
        
        attachment_data, attachment_name, image_prompt = None, None, None
        
        if attach_mode == "Upload an Image":
            uploaded_file = st.file_uploader("Select an image (JPG/PNG)", type=['png', 'jpg', 'jpeg'])
            if uploaded_file:
                attachment_data = uploaded_file.getvalue()
                attachment_name = uploaded_file.name
                st.image(attachment_data, caption="Upload Preview", use_container_width=True)
                
        elif attach_mode == "Generate Image (Manual Prompt)":
            image_prompt = st.text_input("AI Image Prompt", placeholder="e.g., A cinematic shot of a modern office, soft lighting...")
            
        elif attach_mode == "Auto-Generate Image (Agent analyzes email content)":
            st.info("🤖 Gemini will read your email text and automatically craft an image prompt.")

    st.divider()
    
    if st.button("🚀 Execute Email Campaign", type="primary", use_container_width=True):
        raw_emails = email_input.replace('\n', ',').split(',')
        if uploaded_email_file:
            file_content = uploaded_email_file.getvalue().decode("utf-8")
            file_emails = file_content.replace('\n', ',').split(',')
            raw_emails.extend(file_emails)
            
        emails = [e.strip() for e in raw_emails if e.strip()]
        
        if not emails:
            st.error("Please provide at least one recipient email address (manually or via file upload).")
            return
        if not smtp_email or not smtp_password:
            st.error("Please configure your SMTP credentials in the sidebar.")
            return
            
        needs_ai = (input_mode == "Generate from Prompt") or ("Generate Image" in attach_mode)
        if needs_ai and not gemini_key:
            st.error("Please provide your Google API Key to use AI features.")
            return
        
        if theme_mode == "Custom HTML Theme":
            if not custom_html_template or not custom_html_template.strip():
                st.error("Select 'Paste HTML' or upload a file with your custom theme, or switch back to 'Simple (Default)'.")
                return
            if "{{content}}" not in custom_html_template:
                st.error("Your custom HTML theme must include `{{content}}` so the email body has somewhere to go.")
                return
            
        with st.spinner(f"Agent workflow executing for {len(emails)} recipient(s)..."):
            app_graph = build_graph()
            auto_gen_prompt = (attach_mode == "Auto-Generate Image (Agent analyzes email content)")
            
            initial_state = {
                "emails": emails,
                "subject": subject,
                "prompt": prompt if input_mode == "Generate from Prompt" else None,
                "content": exact_content if input_mode == "Provide Exact Content" else None,
                "sender_name": sender_name,
                "sender_title": sender_title,
                "theme_mode": theme_mode,
                "custom_html_template": custom_html_template,
                "auto_generate_image_prompt": auto_gen_prompt,
                "image_prompt": image_prompt if attach_mode == "Generate Image (Manual Prompt)" else None,
                "attachment_name": attachment_name,
                "attachment_data": attachment_data,
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "smtp_email": smtp_email,
                "smtp_password": smtp_password,
                "gemini_api_key": gemini_key,
                "results": []
            }
            
            final_state = app_graph.invoke(initial_state)
            
        st.success("Workflow Complete!")
        
        col_res1, col_res2 = st.columns([1, 1])
        with col_res1:
            st.subheader("📝 Message Preview")
            st.caption("Shown with a sample name — each recipient gets their own.")
            sample_name = "there"
            if emails:
                first_name, _ = email.utils.parseaddr(emails[0])
                if first_name:
                    sample_name = first_name
            preview_text = re.sub(
                r'\[[^\[\]]*?\b(?:recipient|client|customer)\s*name\b[^\[\]]*?\]',
                sample_name, final_state["content"], flags=re.IGNORECASE,
            )
            with st.container(border=True):
                st.markdown(preview_text)
            
        with col_res2:
            if final_state.get("attachment_data"):
                st.subheader("🖼️ Attached Image")
                st.image(final_state["attachment_data"], caption=final_state.get("attachment_name"))
                if auto_gen_prompt:
                    st.caption(f"**Gemini 1.5 Pro generated this prompt:** {final_state.get('image_prompt')}")
                
        st.divider()
        st.subheader("📊 Dispatch Report")
        for res in final_state["results"]:
            if res["status"] == "Success":
                st.success(f"✅ Sent to: {res['email']}")
            else:
                st.error(f"❌ Failed to send to {res['email']}: {res['error']}")

if __name__ == "__main__":
    main()