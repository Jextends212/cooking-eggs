import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from Backend.utils.db_connection  import get_connection
from Backend.utils.cognito_client import get_user_from_token

def lambda_handler(event, context):
    """
    GET    /history              → lista de conversaciones del usuario
    GET    /history/{conv_id}    → mensajes de una conversación
    DELETE /history/{conv_id}    → eliminar una conversación
    """
    try:
        # Debug: ver estructura del evento
        print(f"DEBUG EVENT: {json.dumps(event, indent=2, default=str)[:500]}")
        
        http_method  = event.get("requestContext", {}).get("http", {}).get("method")
        
        # API Gateway HTTP API convierte headers a minúsculas
        headers = event.get("headers") or {}
        access_token = headers.get("access_token") or headers.get("access-token") or headers.get("accesstoken")
        conv_id      = (event.get("pathParameters") or {}).get("conv_id")

        print(f"DEBUG: method={http_method}, has_token={bool(access_token)}, conv_id={conv_id}")
        print(f"DEBUG: ALL HEADERS: {list(headers.keys())}")

        if not access_token:
            return _response(401, {"error": "Token requerido", "headers": list(headers.keys())})

        user = get_user_from_token(access_token)
        if not user["success"]:
            return _response(401, {"error": "Token inválido"})
        
        # Debug: verificar que user tiene 'sub'
        if "sub" not in user:
            return _response(500, {"error": "User object missing 'sub' key", "user_keys": list(user.keys())})

        conn = get_connection()

        with conn:
            with conn.cursor() as cursor:

                # DELETE /history/{conv_id}
                if http_method == "DELETE" and conv_id:
                    cursor.execute(
                        "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                        (conv_id, user["sub"])
                    )
                    if not cursor.fetchone():
                        return _response(403, {"error": "Acceso denegado"})

                    # Marcar como eliminada o eliminar directamente
                    cursor.execute(
                        "DELETE FROM conversations WHERE id = %s AND user_id = %s",
                        (conv_id, user["sub"])
                    )
                    conn.commit()
                    return _response(200, {"success": True, "message": "Conversación eliminada"})

                # GET /history/{conv_id}
                elif conv_id:
                    cursor.execute(
                        "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                        (conv_id, user["sub"])
                    )
                    if not cursor.fetchone():
                        return _response(403, {"error": "Acceso denegado"})

                    # Traer mensajes
                    cursor.execute(
                        """SELECT role, content, created_at
                           FROM messages
                           WHERE conversation_id = %s
                           ORDER BY created_at ASC""",
                        (conv_id,)
                    )
                    rows = cursor.fetchall()
                    # ✅ DictCursor retorna dicts, no tuplas
                    messages = [
                        {
                            "role":       row["role"],
                            "content":    row["content"],
                            "created_at": str(row["created_at"])
                        }
                        for row in rows
                    ]
                    return _response(200, {"messages": messages})

                # GET /history
                else:
                    cursor.execute(
                        """SELECT id, title, created_at
                           FROM conversations
                           WHERE user_id = %s
                           ORDER BY created_at DESC""",
                        (user["sub"],)
                    )
                    rows = cursor.fetchall()
                    
                    # ✅ DictCursor retorna dicts, no tuplas
                    conversations = [
                        {
                            "id":         row["id"],
                            "title":      row["title"],
                            "updated_at": str(row["created_at"])
                        }
                        for row in rows
                    ]
                    return _response(200, {"conversations": conversations})

    except KeyError as e:
        import traceback
        error_detail = f"KeyError: {e} - Traceback: {traceback.format_exc()}"
        print(f"ERROR KeyError en history_handler: {error_detail}")
        return _response(500, {"error": f"KeyError: {e}", "detail": str(e)})
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR en history_handler: {error_detail}")
        return _response(500, {"error": str(e), "type": type(e).__name__})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
            "Strict-Transport-Security":   "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options":      "nosniff",
            "X-Frame-Options":             "DENY"
        },
        "body": json.dumps(body, default=str, ensure_ascii=False)
    }