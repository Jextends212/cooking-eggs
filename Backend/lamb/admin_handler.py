import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from Backend.utils.db_connection  import get_connection
from Backend.utils.cognito_client import (
    get_user_from_token, is_admin, list_all_users,
    admin_delete_user, admin_set_user_password, admin_update_user_attributes
)

def lambda_handler(event, context):
    """
    GET    /admin/users                      - lista de todos los usuarios (desde Cognito)
    PUT    /admin/users/{user_id}            - editar usuario en Cognito (email, etc)
    DELETE /admin/users/{user_id}            - eliminar usuario de Cognito
    POST   /admin/users/{user_id}/pwd        - cambiar password en Cognito (admin solo)
    GET    /admin/conversations              - todas las conversaciones
    GET    /admin/conversations/{user_id}    - conversaciones de un usuario
    DELETE /admin/conversations/{conv_id}    - eliminar conversacion
    """
    try:
        headers = event.get("headers") or {}
        access_token = headers.get("access-token") or headers.get("access_token")
        http_method  = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path         = event.get("rawPath", "")
        body_str     = event.get("body") or "{}"
        params       = event.get("pathParameters") or {}
        
        body = {}
        try:
            body = json.loads(body_str) if body_str else {}
        except:
            pass

        # Verificar token
        user = get_user_from_token(access_token)
        if not user["success"]:
            return _response(401, {"error": "Token invalido"})

        # Verificar que es admin
        if not is_admin(user["email"]):
            return _response(403, {"error": "Acceso solo para administradores"})

        # ======== GET /admin/users - lista de usuarios desde Cognito
        if "/admin/users" in path and http_method == "GET" and not params.get("user_id"):
            try:
                users_data = list_all_users()
                return _response(200, {"users": users_data})
            except Exception as e:
                return _response(500, {"error": str(e)})
        
        # ======== PUT /admin/users/{user_id} - editar usuario en Cognito
        if "/admin/users/" in path and http_method == "PUT":
            username = params.get("user_id")  # Es el username del usuario
            if not username:
                return _response(400, {"error": "user_id (username) requerido"})
            
            new_email = body.get("email", "").strip()
            
            if not new_email:
                return _response(400, {"error": "Email requerido para actualizar"})
            
            # Actualizar email en Cognito
            result = admin_update_user_attributes(username, {"email": new_email})
            
            if not result.get("success"):
                return _response(400, {"error": result.get("error")})
            
            return _response(200, {"message": "Usuario actualizado en Cognito", "username": username})
        
        # ======== DELETE /admin/users/{user_id} - eliminar usuario de Cognito
        if "/admin/users/" in path and http_method == "DELETE":
            username = params.get("user_id")  # Es el username del usuario
            if not username:
                return _response(400, {"error": "user_id (username) requerido"})
            
            try:
                conn = get_connection()
                cursor = conn.cursor()
                
                # Primero eliminar datos del usuario en BD (conversaciones, etc)
                cursor.execute("DELETE FROM conversations WHERE user_id = (SELECT id FROM users WHERE username = %s)", (username,))
                cursor.execute("DELETE FROM favorite_recipes WHERE user_id = (SELECT id FROM users WHERE username = %s)", (username,))
                cursor.execute("DELETE FROM user_profiles WHERE user_id = (SELECT id FROM users WHERE username = %s)", (username,))
                cursor.execute("DELETE FROM users WHERE username = %s", (username,))
                
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error limpiando BD: {e}")
                pass  # Continuar aunque la BD falle
            
            # Eliminar de Cognito
            result = admin_delete_user(username)
            
            if not result.get("success"):
                return _response(400, {"error": result.get("error")})
            
            return _response(200, {"message": "Usuario eliminado de Cognito y BD"})
        
        # ======== POST /admin/users/{user_id}/pwd - cambiar password en Cognito
        if "/admin/users/" in path and "/pwd" in path and http_method == "POST":
            username = params.get("user_id")  # Es el username del usuario
            new_password = body.get("new_password", "").strip()
            
            if not username or not new_password:
                return _response(400, {"error": "user_id (username) y new_password requeridos"})
            
            result = admin_set_user_password(username, new_password)
            
            if not result.get("success"):
                return _response(400, {"error": result.get("error")})
            
            return _response(200, {"message": "Contraseña actualizada en Cognito"})

        conn = get_connection()
        cursor = conn.cursor()

        # DELETE — eliminar conversacion
        if http_method == "DELETE" and "/conversations/" in path:
            conv_id = params.get("conv_id")
            cursor.execute(
                "DELETE FROM conversations WHERE id = %s",
                (conv_id,)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return _response(200, {"message": "Conversacion eliminada"})

        # GET — conversaciones de un usuario especifico
        if params.get("user_id") and "/conversations/" in path:
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
                {"id": row[0] if isinstance(row, tuple) else row["id"], 
                 "title": row[1] if isinstance(row, tuple) else row["title"], 
                 "created_at": str(row[2] if isinstance(row, tuple) else row["created_at"]), 
                 "email": row[3] if isinstance(row, tuple) else row["email"], 
                 "username": row[4] if isinstance(row, tuple) else row["username"]}
                for row in cursor.fetchall()
            ]
            cursor.close()
            conn.close()
            return _response(200, {"conversations": conversations})

        # GET — todas las conversaciones de todos los usuarios
        cursor.execute(
            """SELECT c.id, c.title, c.created_at, u.email, u.username
               FROM conversations c
               JOIN users u ON c.user_id = u.id
               ORDER BY c.created_at DESC"""
        )
        conversations = [
            {"id": row[0] if isinstance(row, tuple) else row["id"], 
             "title": row[1] if isinstance(row, tuple) else row["title"], 
             "created_at": str(row[2] if isinstance(row, tuple) else row["created_at"]), 
             "email": row[3] if isinstance(row, tuple) else row["email"], 
             "username": row[4] if isinstance(row, tuple) else row["username"]}
            for row in cursor.fetchall()
        ]
        cursor.close()
        conn.close()
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