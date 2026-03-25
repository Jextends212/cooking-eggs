import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.db_connection import get_connection
from utils.bedrock_client import ask_claude
from utils.cognito_client import get_user_from_token

def lambda_handler(event, context):
    """
    Recibe: { access_token, conversation_id (opcional), message }
    Devuelve: { conversation_id, response }
    """
    try:
        body         = json.loads(event.get("body", "{}"))
        access_token = body.get("access_token")
        message      = body.get("message", "").strip()
        conv_id      = body.get("conversation_id")  # None si es nueva conversación

        if not access_token or not message:
            return _response(400, {"error": "Faltan parámetros"})

        # 1. Verificar token y obtener usuario
        user = get_user_from_token(access_token)
        if not user["success"]:
            return _response(401, {"error": "Token inválido"})

        user_sub = user["sub"]
        conn     = get_connection()

        with conn:
            with conn.cursor() as cursor:

                # 2. Asegurar que el usuario existe en MySQL
                cursor.execute(
                    "INSERT IGNORE INTO users (id, email, username) VALUES (%s, %s, %s)",
                    (user_sub, user["email"], user["name"])
                )

                # 3. Crear conversación si es nueva
                if not conv_id:
                    # Título automático con las primeras palabras del mensaje
                    title = message[:50] + "..." if len(message) > 50 else message
                    cursor.execute(
                        "INSERT INTO conversations (user_id, title) VALUES (%s, %s)",
                        (user_sub, title)
                    )
                    conv_id = cursor.lastrowid

                # 4. Cargar historial de la conversación
                cursor.execute(
                    """SELECT role, content FROM messages
                       WHERE conversation_id = %s
                       ORDER BY created_at ASC""",
                    (conv_id,)
                )
                history = [
                    {"role": row["role"], "content": row["content"]}
                    for row in cursor.fetchall()
                ]

                # 5. Agregar el nuevo mensaje del usuario al historial
                history.append({"role": "user", "content": message})

                # 6. Llamar a Claude con todo el historial
                claude_response = ask_claude(history)

                # 7. Guardar mensaje del usuario en DB
                cursor.execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                    (conv_id, "user", message)
                )

                # 8. Guardar respuesta de Claude en DB
                cursor.execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
                    (conv_id, "assistant", claude_response)
                )

            conn.commit()

        return _response(200, {
            "conversation_id": conv_id,
            "response":        claude_response
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
            "Strict-Transport-Security":   "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options":      "nosniff",
            "X-Frame-Options":             "DENY"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
