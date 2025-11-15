import httpx
from app.config import WHATSAPP_TOKEN, PHONE_NUMBER_ID


async def send_whatsapp_text(to: str, message: str):
    """
    Send a plain text message to a WhatsApp user.
    """

    print("Reaching WhatsApp API to send message")
    
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

    print("WhatsApp URL:", url)

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()


async def send_whatsapp_buttons(to: str, text: str, buttons: list):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

    print("Reacheding WhatsApp API to send buttons")

    # Convert Rasa buttons → WhatsApp buttons
    wa_buttons = []
    for b in buttons:
        wa_buttons.append({
            "type": "reply",
            "reply": {
                "id": b["payload"],   # WhatsApp returns this when user clicks
                "title": b["title"]   # Button text (max 20 chars)
            }
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": text.strip()
            },
            "action": {
                "buttons": wa_buttons
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    print("payload", payload)
    print("headers", headers)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        return response.json()
