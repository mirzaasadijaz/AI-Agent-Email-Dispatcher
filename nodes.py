import smtplib
import email.utils
import re
import markdown
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from google import genai
from google.genai import types
from state import EmailState

# --- Placeholder patterns -----------------------------------------------
# Broad enough to catch real-world AI variations like "[Your Company Name]"
# or "[Sender's Full Name]", but RECIPIENT_NAME_PATTERN is always checked
# first / excluded from the sender patterns so "[Recipient Name]" is never
# swallowed by the sender-cleanup step.
RECIPIENT_NAME_PATTERN = re.compile(
    r'\[[^\[\]]*?\b(?:recipient|client|customer)\s*name\b[^\[\]]*?\]', re.IGNORECASE
)
SENDER_NAME_PATTERN = re.compile(
    r'\[(?!\s*(?:recipient|client|customer))[^\[\]]*?\bname\b[^\[\]]*?\]', re.IGNORECASE
)
SENDER_TITLE_PATTERN = re.compile(
    r'\[[^\[\]]*?\b(?:title|company|role)\b[^\[\]]*?\]', re.IGNORECASE
)
# Catches anything the AI invents that isn't a real placeholder we handle,
# e.g. "[Link: Shop the Sale Now]" or "[Insert CTA here]" — stripped to
# plain text instead of being left as a broken bracket in the sent email.
STRAY_BRACKET_PATTERN = re.compile(r'\[([^\[\]]{1,80})\]')


def generate_email_content(state: EmailState) -> dict:
    raw_content = state.get("content")
    sender_name = (state.get("sender_name") or "").strip()
    sender_title = (state.get("sender_title") or "").strip()

    # Fallback signature so we never sign emails as blank
    signature_name = sender_name if sender_name else "The Team"

    if not raw_content:
        client = genai.Client(api_key=state["gemini_api_key"])
        sys_instruct = (
            "You are an elite, executive-level email copywriter. Write the email body based on the prompt.\n\n"
            "STRICT RULES:\n"
            "1. Use Markdown for formatting (**bolding**, bullet points).\n"
            "2. NEVER use placeholder brackets for the sender (e.g., no [Name], no [Company]).\n"
            "3. Leave the greeting placeholder as '[Recipient Name]' exactly — do not invent a "
            "different bracket for it, since that gets personalized later.\n"
            "4. Do NOT invent any other bracketed placeholders — no [Link], no [CTA], no [Insert X], "
            "no [Button]. If you want a call-to-action, write it as plain text (e.g., "
            "'Shop the sale now.'), never as a bracket.\n"
            f"5. You MUST end the email exactly with this signature:\n\nBest regards,\n{signature_name}"
            + (f"\n{sender_title}" if sender_title else "")
        )
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=f"Write an email about: {state['prompt']}",
            config=types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.4
            )
        )
        raw_content = response.text

    # Replace ONLY sender-side placeholders. Recipient placeholders are
    # left untouched here — they get filled in per-recipient in dispatch_emails.
    cleaned = SENDER_NAME_PATTERN.sub(signature_name, raw_content)
    cleaned = SENDER_TITLE_PATTERN.sub(sender_title, cleaned)

    # Clean up accidental duplicate signature lines
    if sender_title:
        dup = f"{signature_name}\n{sender_title}\n{signature_name}"
        cleaned = cleaned.replace(dup, f"{signature_name}\n{sender_title}")
    else:
        dup = f"{signature_name}\n{signature_name}"
        cleaned = cleaned.replace(dup, signature_name)

    # Safety net: if the AI invented any other bracketed placeholder
    # (e.g. "[Link: Shop the Sale Now]"), strip the brackets and keep the
    # text inside rather than sending a broken-looking "[Link: ...]" — but
    # never touch the still-pending "[Recipient Name]" placeholder.
    def _strip_stray(match: re.Match) -> str:
        inner = match.group(1)
        if RECIPIENT_NAME_PATTERN.match(f"[{inner}]"):
            return match.group(0)
        return inner

    cleaned = STRAY_BRACKET_PATTERN.sub(_strip_stray, cleaned)

    return {"content": cleaned.strip()}


def create_image_prompt(state: EmailState) -> dict:
    if not state.get("auto_generate_image_prompt") or state.get("image_prompt") or state.get("attachment_data"):
        return {}

    client = genai.Client(api_key=state["gemini_api_key"])
    email_text = f"Subject: {state.get('subject')}\nBody: {state.get('content')}"

    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=f"Create an image prompt for this email:\n{email_text}",
        config=types.GenerateContentConfig(
            system_instruction="You are an expert AI image prompt engineer. Write a concise, visually striking, and descriptive prompt for an AI image generator based on the email context. Output ONLY the prompt text."
        )
    )
    return {"image_prompt": response.text}


def generate_or_fetch_image(state: EmailState) -> dict:
    if state.get("attachment_data"):
        return {}

    if state.get("image_prompt") and state.get("gemini_api_key"):
        try:
            client = genai.Client(api_key=state["gemini_api_key"])
            result = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=state["image_prompt"],
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="4:3"
                )
            )
            return {
                "attachment_data": result.generated_images[0].image.image_bytes,
                "attachment_name": "ai_generated_image.jpg"
            }
        except Exception as e:
            print(f"Gemini API Error: {e}")

    return {}


def dispatch_emails(state: EmailState) -> dict:
    results = []
    try:
        server = smtplib.SMTP(state["smtp_server"], state["smtp_port"])
        server.starttls()
        server.login(state["smtp_email"], state["smtp_password"])

        sender_name = (state.get("sender_name") or "").strip() or "The Team"
        theme_mode = state.get("theme_mode", "Simple")
        custom_template = state.get("custom_html_template", "")

        for recipient_str in state["emails"]:
            try:
                recip_name, recip_email = email.utils.parseaddr(recipient_str.strip())
                if not recip_email:
                    recip_email = recipient_str.strip()

                display_name = recip_name if recip_name else "there"

                # Replace [Recipient Name] / [Client Name] / [Customer Name]
                # for this specific recipient
                personalized_text = RECIPIENT_NAME_PATTERN.sub(display_name, state["content"])

                # Convert Markdown to HTML
                raw_html = markdown.markdown(personalized_text)

                # --- APPLY THEME LOGIC ---
                if theme_mode == "Custom HTML Theme" and custom_template and "{{content}}" in custom_template:
                    final_html = custom_template.replace("{{content}}", raw_html)
                else:
                    final_html = (
                        f"<html><head></head><body style='font-family: sans-serif; "
                        f"font-size: 14px; color: #333;'>{raw_html}</body></html>"
                    )

                personalized_subject = RECIPIENT_NAME_PATTERN.sub(display_name, state["subject"])

                msg = MIMEMultipart('mixed')
                msg['From'] = f"{sender_name} <{state['smtp_email']}>" if sender_name else state["smtp_email"]
                msg['To'] = recipient_str.strip()
                msg['Subject'] = personalized_subject

                alt = MIMEMultipart('alternative')
                msg.attach(alt)
                alt.attach(MIMEText(personalized_text, 'plain'))
                alt.attach(MIMEText(final_html, 'html'))

                if state.get("attachment_data") and state.get("attachment_name"):
                    image_part = MIMEImage(state["attachment_data"], name=state["attachment_name"])
                    msg.attach(image_part)

                server.send_message(msg)
                results.append({"email": recip_email, "status": "Success", "error": ""})
            except Exception as e:
                results.append({"email": recipient_str, "status": "Failed", "error": str(e)})

        server.quit()
    except Exception as e:
        for recipient in state["emails"]:
            results.append({"email": recipient, "status": "Failed", "error": f"SMTP Error: {str(e)}"})

    return {"results": results}