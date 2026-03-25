import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from Backend.utils.cognito_client import (
    login_user, register_user,
    respond_new_password_challenge,
    is_admin, get_user_from_token,
    forgot_password, confirm_forgot_password, change_password
)
from Backend.utils.db_connection import get_connection

def lambda_handler(event, context):
    try:
        body   = json.loads(event.get("body", "{}"))
        action = body.get("action", "login")

        actions = {
            "login":            handle_login,
            "register":         handle_register,
            "challenge":        handle_challenge,
            "forgot_password":  handle_forgot_password,
            "reset_password":   handle_reset_password,
            "change_password":  handle_change_password,
        }

        handler = actions.get(action)
        if not handler:
            return _response(400, {"error": f"Acción '{action}' no válida"})

        return handler(body)

    except Exception as e:
        return _response(500, {"error": str(e)})


def handle_login(body):
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return _response(400, {"error": "Usuario y contraseña requeridos"})

    login = login_user(username, password)

    if login.get("challenge") == "NEW_PASSWORD_REQUIRED":
        return _response(202, {
            "challenge": "NEW_PASSWORD_REQUIRED",
            "session":   login.get("session"),
            "username":  login.get("username")
        })

    if not login.get("success"):
        return _response(401, {"error": login.get("error")})

    access_token = login.get("access_token")

    # ✅ user_info ya tiene name y email directamente
    user_info    = get_user_from_token(access_token)
    user_email   = user_info.get("email", "")
    user_is_admin = is_admin(user_email or username)  # Intenta primero con email, luego username

    return _response(200, {
        "access_token":  access_token,
        "id_token":      login.get("id_token"),
        "refresh_token": login.get("refresh_token"),
        "name":          user_info.get("name") or username, 
        "email":         user_email or username,
        "username":      username,
        "is_admin":      user_is_admin
    })


def handle_register(body):
    name     = body.get("name", "").strip()
    email    = body.get("email", "").strip()
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not all([name, email, username, password]):
        return _response(400, {"error": "Todos los campos son requeridos"})

    if len(password) < 8:
        return _response(400, {"error": "La contraseña debe tener mínimo 8 caracteres"})

    result = register_user(name, email, username, password)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(201, {
        "success":  True,
        "user_sub": result.get("user_sub"),
        "message":  "Cuenta creada exitosamente 🎉"
    })


def handle_challenge(body):
    username     = body.get("username")
    new_password = body.get("new_password")
    session      = body.get("session")
    old_password = body.get("old_password")

    if not all([username, new_password, session, old_password]):
        return _response(400, {"error": "Datos incompletos para el desafío"})

    result = respond_new_password_challenge(
        username, new_password, session,
        {"PASSWORD": old_password}
    )

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "access_token":  result.get("access_token"),
        "id_token":      result.get("id_token"),
        "refresh_token": result.get("refresh_token")
    })


def handle_forgot_password(body):
    username = body.get("username", "").strip()

    if not username:
        return _response(400, {"error": "Usuario requerido"})

    # Usar Cognito forgot_password en lugar de BD
    result = forgot_password(username)
    
    if not result.get("success"):
        return _response(400, {"error": result.get("error")})
    
    return _response(200, {
        "success": True,
        "message": "Codigo enviado a tu email"
    })


def handle_reset_password(body):
    username = body.get("username", "").strip()
    code = body.get("code", "").strip() or body.get("token", "").strip()
    new_password = body.get("new_password", "")

    if not all([username, code, new_password]):
        return _response(400, {"error": "Username, codigo y password requeridos"})

    # Usar Cognito confirm_forgot_password en lugar de BD
    result = confirm_forgot_password(username, code, new_password)
    
    if not result.get("success"):
        return _response(400, {"error": result.get("error")})
    
    return _response(200, {
        "success": True,
        "message": "Contrasena actualizada exitosamente"
    })



def handle_change_password(body):
    """Cambia la contraseña del usuario actual usando Cognito"""
    access_token = body.get("access_token", "").strip()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not all([access_token, old_password, new_password]):
        return _response(400, {"error": "Parametros incompletos"})

    # Usar Cognito change_password en lugar de BD
    result = change_password(access_token, old_password, new_password)
    
    if not result.get("success"):
        return _response(401, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": "Contrasena actualizada exitosamente"
    })


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