import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.cognito_client import (
    login_user, register_user,
    respond_new_password_challenge,
    forgot_password, confirm_forgot_password,
    is_admin, get_user_from_token, change_password
)
from utils.password_reset import (
    send_reset_email, reset_password_with_token,
    change_password_authenticated
)

def lambda_handler(event, context):
    try:
        body   = json.loads(event.get("body", "{}"))
        action = body.get("action", "login")

        actions = {
            "login":                    handle_login,
            "register":                 handle_register,
            "challenge":                handle_challenge,
            "forgot_password":          handle_forgot_password,
            "reset_password":           handle_reset_password,
            "change_password":          handle_change_password,
            "change_password_alt":      handle_change_password_alt,
            "forgot_password_alt":      handle_forgot_password_alt,
            "reset_password_alt":       handle_reset_password_alt,
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
    
    # Verificar si hay un desafío
    if login.get("challenge") == "NEW_PASSWORD_REQUIRED":
        return _response(202, {
            "challenge": "NEW_PASSWORD_REQUIRED",
            "session":   login.get("session"),
            "username":  login.get("username")
        })

    # Verificar si el login fue exitoso
    if not login.get("success"):
        error_msg = login.get("error", "Credenciales incorrectas")
        print(f"❌ Login fallido: {error_msg}")
        return _response(401, {"error": error_msg})

    access_token = login.get("access_token")
    if not access_token:
        print("❌ No se obtuvo access_token")
        return _response(500, {"error": "Error al obtener token de acceso"})

    # Obtener información del usuario
    user_info = get_user_from_token(access_token)
    if not user_info.get("success"):
        print(f"❌ Error obteniendo info del usuario: {user_info.get('error')}")
        return _response(500, {"error": "Error al obtener información del usuario"})
    
    user_is_admin = is_admin(username)

    print(f"✅ Login exitoso para {username}")
    return _response(200, {
        "access_token":  access_token,
        "id_token":      login.get("id_token"),
        "refresh_token": login.get("refresh_token"),
        "name":          user_info.get("name") or username, 
        "email":         user_info.get("email", ""),
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

    result = forgot_password(username)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": "Código enviado a tu correo 📧"
    })


def handle_reset_password(body):
    username         = body.get("username", "").strip()
    confirmation_code = body.get("code", "").strip()
    new_password     = body.get("new_password", "")

    if not all([username, confirmation_code, new_password]):
        return _response(400, {"error": "Usuario, código y nueva contraseña requeridos"})

    if len(new_password) < 8:
        return _response(400, {"error": "La contraseña debe tener mínimo 8 caracteres"})

    result = confirm_forgot_password(username, confirmation_code, new_password)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": "Contraseña actualizada exitosamente ✅"
    })


def handle_change_password(body):
    """Cambiar contraseña con Cognito (usuario autenticado)"""
    access_token = body.get("access_token", "").strip()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not all([access_token, old_password, new_password]):
        return _response(400, {"error": "Access token, contraseña actual y nueva requeridos"})

    if len(new_password) < 8:
        return _response(400, {"error": "La contraseña debe tener mínimo 8 caracteres"})

    result = change_password(access_token, old_password, new_password)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": result.get("message", "Contraseña actualizada ✅")
    })


def handle_change_password_alt(body):
    """Cambiar contraseña sin Cognito (alternativa con BD)"""
    user_id = body.get("user_id", "").strip()
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")

    if not all([user_id, old_password, new_password]):
        return _response(400, {"error": "user_id, contraseña actual y nueva requeridos"})

    if len(new_password) < 8:
        return _response(400, {"error": "La contraseña debe tener mínimo 8 caracteres"})

    result = change_password_authenticated(user_id, old_password, new_password)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": result.get("message", "Contraseña actualizada ✅")
    })


def handle_forgot_password_alt(body):
    """Solicitar reset de contraseña sin Cognito (alternativa con BD)"""
    email = body.get("email", "").strip()
    user_id = body.get("user_id", "").strip()
    username = body.get("username", "").strip()

    if not all([email, user_id, username]):
        return _response(400, {"error": "Email, user_id y username requeridos"})

    result = send_reset_email(email, user_id, username)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": result.get("message", "Email de reset enviado 📧")
    })


def handle_reset_password_alt(body):
    """Confirmar reset de contraseña sin Cognito (alternativa con BD)"""
    user_id = body.get("user_id", "").strip()
    token = body.get("token", "").strip()
    new_password = body.get("new_password", "")

    if not all([user_id, token, new_password]):
        return _response(400, {"error": "user_id, token y nueva contraseña requeridos"})

    if len(new_password) < 8:
        return _response(400, {"error": "La contraseña debe tener mínimo 8 caracteres"})

    result = reset_password_with_token(user_id, token, new_password)

    if not result.get("success"):
        return _response(400, {"error": result.get("error")})

    return _response(200, {
        "success": True,
        "message": result.get("message", "Contraseña actualizada ✅")
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