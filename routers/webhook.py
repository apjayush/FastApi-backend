import os
import json
from base64 import b64decode, b64encode
from fastapi import APIRouter, Request, Response
from cryptography.hazmat.primitives.asymmetric.padding import OAEP, MGF1
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from app.utils.logger import log_message
from app.services.whatsapp_service import send_whatsapp_text, send_whatsapp_buttons
from app.services.rasa_service import send_to_rasa

router = APIRouter()

def decrypt_request(encrypted_flow_data_b64, encrypted_aes_key_b64, initial_vector_b64, private_key):
    flow_data = b64decode(encrypted_flow_data_b64)
    iv = b64decode(initial_vector_b64)

    # Decrypt the AES encryption key
    encrypted_aes_key = b64decode(encrypted_aes_key_b64)
    aes_key = private_key.decrypt(
        encrypted_aes_key,
        OAEP(
            mgf=MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Decrypt the Flow data
    encrypted_flow_data_body = flow_data[:-16]
    encrypted_flow_data_tag = flow_data[-16:]
    decryptor = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(iv, encrypted_flow_data_tag)
    ).decryptor()
    decrypted_data_bytes = decryptor.update(encrypted_flow_data_body) + decryptor.finalize()
    decrypted_data = json.loads(decrypted_data_bytes.decode("utf-8"))
    return decrypted_data, aes_key, iv

def encrypt_response(response, aes_key, iv):
    # Flip the initialization vector
    flipped_iv = bytearray([b ^ 0xFF for b in iv])

    # Encrypt the response data
    encryptor = Cipher(
        algorithms.AES(aes_key),
        modes.GCM(flipped_iv)
    ).encryptor()
    ciphertext = encryptor.update(json.dumps(response).encode("utf-8")) + encryptor.finalize()
    encrypted = ciphertext + encryptor.tag
    return b64encode(encrypted).decode("utf-8")

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    # log_message(str(data))  # log full raw webhook content

    # Health check or encrypted flow request
    if "encrypted_flow_data" in data:
        # Load private key with password
        private_key_path = os.getenv("PRIVATE_KEY_PATH", "/home/ayush/private.pem")
        private_key_password = os.getenv("PRIVATE_KEY_PASSWORD")
        password_bytes = private_key_password.encode('utf-8') if private_key_password else None
        with open(private_key_path, "rb") as key_file:
            private_key = load_pem_private_key(key_file.read(), password=password_bytes)

        try:
            decrypted_data, aes_key, iv = decrypt_request(
                data["encrypted_flow_data"],
                data["encrypted_aes_key"],
                data["initial_vector"],
                private_key
            )
            print("Decrypted payload:", decrypted_data)
        except Exception as e:
            print("Decryption error:", e)
            return Response(content="", status_code=500)

        # Health check: respond with required payload
        if decrypted_data.get("action") == "ping":
            response_payload = {
                "data": {
                    "status": "active"
                }
            }
            encrypted_response = encrypt_response(response_payload, aes_key, iv)
            return Response(content=encrypted_response, media_type="text/plain")

        # You can handle other decrypted actions here...

        # Default: return error if not handled
        return Response(content="", status_code=400)

    try:
        if "entry" not in data or not data["entry"]:
            log_message("Webhook received payload without 'entry' key.")
            return {"status": "ignored"}
        
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # ---------------------------------------
        # IGNORE STATUS NOTIFICATIONS
        # (sent, delivered, read)
        # ---------------------------------------
        if "statuses" in value:
            return {"status": "ok"}

        # ---------------------------------------
        # GET USER MESSAGE
        # ---------------------------------------
        messages = value.get("messages", [])
        if not messages:
            return {"status": "no_messages"}

        msg = messages[0]
        user_phone = msg["from"]

        print(f"User Message: {msg}")  # for debugging
        print(f"User Phone: {user_phone}")

        # ---------------------------------------
        # CASE 1: USER SENT NORMAL TEXT
        # ---------------------------------------
        if msg["type"] == "text":
            user_msg = msg["text"]["body"]

        # ---------------------------------------
        # CASE 2: USER CLICKED A BUTTON
        # ---------------------------------------
        elif msg["type"] == "interactive":
            interactive = msg["interactive"]

            # Button reply
            if interactive["type"] == "button_reply":
                user_msg = interactive["button_reply"]["id"]

            # List reply (future)
            elif interactive["type"] == "list_reply":
                user_msg = interactive["list_reply"]["id"]

        else:
            user_msg = None

        # No valid message
        if not user_msg:
            return {"status": "ignored"}

        log_message(f"From: {user_phone} | Message: {user_msg}")

        # ---------------------------------------
        # SEND TO RASA
        # ---------------------------------------
        rasa_response = await send_to_rasa(user_phone, user_msg)
        log_message(f"Rasa replied: {rasa_response}")

        # ---------------------------------------
        # SEND RASA RESPONSES TO WHATSAPP
        # ---------------------------------------
        for r in rasa_response:

            # Buttons
            if r.get("buttons"):
                await send_whatsapp_buttons(
                    user_phone,
                    r.get("text", ""),
                    r["buttons"]
                )

            # Text only
            elif r.get("text"):
                await send_whatsapp_text(user_phone, r["text"])

        return {"status": "ok"}

    except Exception as e:
        log_message(f"Webhook Error: {e}")
        return {"status": "error"}
    


VERIFY_TOKEN = "mytoken"   
@router.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)

    return {"error": "Invalid verify token"}

