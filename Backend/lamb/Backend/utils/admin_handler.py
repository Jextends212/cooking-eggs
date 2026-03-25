#Admin_handler
import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from Backend.utils.db_connection  import get_connection
from Backend.utils.cognito_client import get_user_from_token, is_admin, list_all_users, admin_delete_user

def lambda_handler(event, context):
    """
    GET    /admin/users                   → lista de todos los usuarios
    GET    /admin/conversations           → todas las conversaciones
    GET    /admin/conversations/{user_id} → conversaciones de un usuario
    DELETE /admin/conversations/{conv_id} → eliminar conversación
    """
    try:
        headers = event.get("headers") or {}
        access_token = headers.get("access-token") or headers.get("access_token")
        http_method  = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path         = event.get("rawPath", "")
        params       = event.get("pathParameters") or {}

        # Verificar token
        user = get_user_from_token(access_token)
        if not user["success"]:
            return _response(401, {"error": "Token inválido"})

        # Verificar que es admin
        if not is_admin(user["email"]):
            return _response(403, {"error": "Acceso solo para administradores"})

        # GET /admin/users — lista de usuarios
        if "/admin/users" in path and http_method == "GET":
            try:
                users_data = list_all_users()
                return _response(200, {"users": users_data})
            except Exception as e:
                return _response(500, {"error": str(e)})

        conn = get_connection()

        with conn:
            with conn.cursor() as cursor:

                # DELETE — eliminar conversación
                if http_method == "DELETE" and "/conversations/" in path:
                    conv_id = params.get("conv_id")
                    cursor.execute(
                        "DELETE FROM conversations WHERE id = %s",
                        (conv_id,)
                    )
                    conn.commit()
                    return _response(200, {"message": "Conversación eliminada ✅"})

                # GET — conversaciones de un usuario específico
                elif params.get("user_id"):
                    user_id = params.get("user_id")
                    cursor.execute(
                        """SELECT c.id, c.title, c.created_at,
                                  u.email, u.username
                           FROM conversations c
                           JOIN users u ON c.user_id = u.id
                           WHERE c.user_id = %s
                           ORDER BY c.created_at DESC""",
                        (user_id,)
                    )
                    conversations = [
                        {"id": row["id"], "title": row["title"], "created_at": str(row["created_at"]), 
                         "email": row["email"], "username": row["username"]}
                        for row in cursor.fetchall()
                    ]
                    return _response(200, {"conversations": conversations})

                # GET — todas las conversaciones de todos los usuarios
                else:
                    cursor.execute(
                        """SELECT c.id, c.title, c.created_at,
                                  u.email, u.username
                           FROM conversations c
                           JOIN users u ON c.user_id = u.id
                           ORDER BY c.created_at DESC"""
                    )
                    conversations = [
                        {"id": row["id"], "title": row["title"], "created_at": str(row["created_at"]), 
                         "email": row["email"], "username": row["username"]}
                        for row in cursor.fetchall()
                    ]
                    return _response(200, {"conversations": conversations})

    except Exception as e:
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type":                "application/json",
            "Access-Control-Allow-Origin": "*",
            "Strict-Transport-Security":   "max-age=31536000; includeSubDomains"
        },
        "body": json.dumps(body, default=str, ensure_ascii=False)
    }