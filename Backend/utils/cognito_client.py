import boto3
import os
import hmac
import hashlib
import base64
import re

USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
CLIENT_ID    = os.getenv("COGNITO_CLIENT_ID")
CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
REGION       = os.getenv("COGNITO_REGION")

client = boto3.client("cognito-idp", region_name=REGION)

# ─── VALIDACIÓN DE CONTRASEÑA ───────────────────────────────────
def validate_password_strength(password: str) -> tuple:
    """
    Valida fortaleza de contraseña
    Retorna: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Mínimo 8 caracteres"
    if len(password) > 128:
        return False, "Máximo 128 caracteres"
    if not re.search(r'[a-z]', password):
        return False, "Debe contener letras minúsculas"
    if not re.search(r'[A-Z]', password):
        return False, "Debe contener letras mayúsculas"
    if not re.search(r'[0-9]', password):
        return False, "Debe contener números"
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Debe contener caracteres especiales (!@#$ etc)"
    
    return True, ""

# ─── CALCULAR SECRET HASH ───────────────────────────────────
def get_secret_hash(username: str) -> str:
    """Calcula SECRET_HASH para Cognito
    
    Args:
        username: email o username del usuario
    
    Returns:
        str: hash en base64 o None
    """
    if not CLIENT_SECRET:
        return None
    message = bytes(username + CLIENT_ID, 'utf-8')
    key = bytes(CLIENT_SECRET, 'utf-8')
    return base64.b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()

# ─── VERIFICAR SI EMAIL YA EXISTE ──────────────────────────
def email_exists(email: str) -> bool:
    """
    Verifica si el email ya está registrado en Cognito
    
    Args:
        email: email a verificar
    
    Returns:
        bool: True si el email existe
    """
    # Validar formato de email
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False
    
    try:
        response = client.list_users(
            UserPoolId=USER_POOL_ID,
            Filter=f'email = "{email}"'
        )
        return len(response['Users']) > 0
    except Exception:
        return False

# ─── REGISTRO ───────────────────────────────────────────────
def register_user(name: str, email: str, username: str, password: str) -> dict:
    """
    Registra un nuevo usuario en Cognito
    
    Args:
        name: nombre completo
        email: email valido
        username: username único
        password: contraseña
    
    Returns:
        dict: {"success": bool, "user_sub": str, "error": str, "message": str}
    """
    # Validar entrada
    if not all([name, email, username, password]):
        return {"success": False, "error": "Todos los campos son requeridos", "message": None}
    
    # Validar contraseña
    is_strong, error_msg = validate_password_strength(password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña débil: {error_msg}", "message": None}
    
    try:
        # Validar que el email no esté registrado
        if email_exists(email):
            return {"success": False, "error": "Este correo ya está registrado", "message": None}
        
        params = {
            "ClientId": CLIENT_ID,
            "Username": username.strip(),
            "Password": password,
            "UserAttributes": [
                {"Name": "email", "Value": email.strip()},
                {"Name": "name",  "Value": name.strip()}
            ]
        }
        
        # Agregar SECRET_HASH si existe CLIENT_SECRET
        secret_hash = get_secret_hash(username)
        if secret_hash:
            params["SecretHash"] = secret_hash
        
        response = client.sign_up(**params)
        
        # Auto-confirmar el usuario (sin email de verificación)
        client.admin_confirm_sign_up(
            UserPoolId=USER_POOL_ID,
            Username=username.strip()
        )
        
        print(f"✅ Usuario registrado: {username}")
        return {
            "success": True, 
            "user_sub": response["UserSub"],
            "message": "Cuenta creada exitosamente 🎉",
            "error": None
        }
    except client.exceptions.UsernameExistsException:
        return {"success": False, "error": "El usuario ya está registrado", "message": None}
    except client.exceptions.InvalidPasswordException:
        return {"success": False, "error": "La contraseña no cumple requisitos de Cognito", "message": None}
    except Exception as e:
        print(f"❌ Error registrando usuario: {e}")
        return {"success": False, "error": str(e), "message": None}

# ─── LOGIN ───────────────────────────────────────────────────
def login_user(email: str, password: str) -> dict:
    """
    Autentica un usuario con email y contraseña
    
    Args:
        email: email del usuario
        password: contraseña
    
    Returns:
        dict: {"success": bool, "access_token": str, "id_token": str, 
               "refresh_token": str, "challenge": str, "session": str, "error": str}
    """
    if not email or not password:
        return {"success": False, "error": "Email y contraseña requeridos", "message": None}
    
    try:
        params = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "AuthParameters": {
                "USERNAME": email.strip(),
                "PASSWORD": password
            },
            "ClientId": CLIENT_ID
        }
        
        # Agregar SECRET_HASH si existe CLIENT_SECRET
        secret_hash = get_secret_hash(email)
        if secret_hash:
            params["AuthParameters"]["SECRET_HASH"] = secret_hash
        
        response = client.initiate_auth(**params)
        
        # Verificar si hay AuthenticationResult (login exitoso)
        if "AuthenticationResult" in response:
            tokens = response["AuthenticationResult"]
            print(f"✅ Login exitoso para {email}")
            return {
                "success":      True,
                "access_token": tokens["AccessToken"],
                "id_token":     tokens.get("IdToken"),
                "refresh_token":tokens.get("RefreshToken"),
                "error": None,
                "message": None
            }
        elif response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            # Retornar los datos del desafío para que el cliente lo maneje
            print(f"⚠️ Usuario {email} requiere cambio de contraseña")
            return {
                "success": False,
                "challenge": "NEW_PASSWORD_REQUIRED",
                "session": response.get("Session"),
                "username": email,
                "error": None,
                "message": None
            }
        else:
            # Otros desafíos
            return {
                "success": False, 
                "error": f"Desafío inesperado: {response.get('ChallengeName')}",
                "challenge": response.get('ChallengeName'),
                "message": None
            }
    except client.exceptions.NotAuthorizedException:
        return {
            "success": False, 
            "error": "Email o contraseña incorrectos",
            "message": None
        }
    except client.exceptions.UserNotFoundException:
        return {
            "success": False, 
            "error": "Usuario no encontrado",
            "message": None
        }
    except Exception as e:
        print(f"❌ Error en login: {e}")
        return {"success": False, "error": str(e), "message": None}

# ─── RESPONDER DESAFÍO NEW_PASSWORD_REQUIRED ─────────────────
def respond_new_password_challenge(username: str, new_password: str, session: str, response_data: dict) -> dict:
    """
    Responde al desafío NEW_PASSWORD_REQUIRED de Cognito
    
    Args:
        username: email o username
        new_password: nueva contraseña
        session: sesión del desafío
        response_data: datos de respuesta con PASSWORD anterior
    
    Returns:
        dict: {"success": bool, "access_token": str, "id_token": str, 
               "refresh_token": str, "error": str}
    """
    if not all([username, new_password, session, response_data]):
        return {"success": False, "error": "Parámetros incompletos"}
    
    # Validar nueva contraseña
    is_strong, error_msg = validate_password_strength(new_password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña débil: {error_msg}"}
    
    try:
        secret_hash = get_secret_hash(username)
        params = {
            "ClientId": CLIENT_ID,
            "ChallengeName": "NEW_PASSWORD_REQUIRED",
            "Session": session,
            "ChallengeResponses": {
                "USERNAME": username.strip(),
                "PASSWORD": response_data.get("PASSWORD"),
                "NEW_PASSWORD": new_password
            }
        }
        if secret_hash:
            params["ChallengeResponses"]["SECRET_HASH"] = secret_hash
        
        response = client.respond_to_auth_challenge(**params)
        
        if "AuthenticationResult" in response:
            tokens = response["AuthenticationResult"]
            print(f"✅ Desafío NEW_PASSWORD_REQUIRED respondido para {username}")
            return {
                "success": True,
                "access_token": tokens["AccessToken"],
                "id_token": tokens.get("IdToken"),
                "refresh_token": tokens.get("RefreshToken"),
                "error": None
            }
        else:
            return {"success": False, "error": "No se pudo completar el desafío"}
    except client.exceptions.InvalidPasswordException:
        return {"success": False, "error": "La nueva contraseña no cumple con los requisitos de Cognito"}
    except Exception as e:
        print(f"❌ Error en respond_new_password_challenge: {e}")
        return {"success": False, "error": str(e)}

# ─── VERIFICAR TOKEN ─────────────────────────────────────────
def get_user_from_token(access_token: str) -> dict:
    try:
        response = client.get_user(AccessToken=access_token)
        attrs = {a["Name"]: a["Value"] for a in response["UserAttributes"]}
        return {
            "success":  True,
            "sub":      attrs.get("sub"),
            "email":    attrs.get("email"),
            "name":     attrs.get("name")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ─── VERIFICAR SI ES ADMIN ───────────────────────────────────
def is_admin(identifier: str) -> bool:
    """Verifica si un usuario es admin (desde BD, busca por email o username)"""
    try:
        from utils.db_connection import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM users WHERE email = %s OR username = %s",
            (identifier, identifier)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            role = result['role'] if isinstance(result, dict) else result[0]
            return role == 'admin'
        
        return False
    except Exception as e:
        print(f"❌ Error verificando admin: {e}")
        return False

# ─── LISTAR TODOS LOS USUARIOS ───────────────────────────────
def list_all_users() -> list:
    """Obtiene la lista de todos los usuarios del Cognito User Pool"""
    try:
        users = []
        paginator = client.get_paginator('list_users')
        
        for page in paginator.paginate(UserPoolId=USER_POOL_ID):
            for user in page['Users']:
                attrs = {a["Name"]: a["Value"] for a in user["Attributes"]}
                user_data = {
                    "id": attrs.get("sub"),
                    "email": attrs.get("email", ""),
                    "username": user["Username"],
                    "role": "admin" if is_admin(attrs.get("email", "")) else "user",
                    "is_active": user["UserStatus"] == "CONFIRMED",
                    "created_at": str(user["UserCreateDate"])
                }
                users.append(user_data)
        
        return users
    except Exception as e:
        return []
    
def forgot_password(username: str) -> dict:
    """
    Inicia flujo de recuperación de contraseña
    Cognito enviará un código al email registrado
    
    Args:
        username: email o username
    
    Returns:
        dict: {"success": bool, "message": str, "error": str}
    """
    if not username or not username.strip():
        return {"success": False, "error": "Usuario requerido"}
    
    try:
        client.forgot_password(
            ClientId=CLIENT_ID,
            Username=username.strip(),
            SecretHash=get_secret_hash(username)
        )
        print(f"✅ Código de reset enviado a {username}")
        return {
            "success": True, 
            "message": "Código enviado a tu correo 📧",
            "error": None
        }
    except client.exceptions.UserNotFoundException:
        # No revelar si usuario existe
        return {
            "success": True, 
            "message": "Si el usuario existe, recibirá un código por email",
            "error": None
        }
    except client.exceptions.InvalidParameterException as e:
        return {"success": False, "error": "Parámetros inválidos", "message": None}
    except Exception as e:
        print(f"❌ Error en forgot_password: {e}")
        return {"success": False, "error": str(e), "message": None}

def confirm_forgot_password(username: str, code: str, new_password: str) -> dict:
    """
    Confirma reset de contraseña con código de verificación
    
    Args:
        username: email o username
        code: código recibido en email
        new_password: nueva contraseña
    
    Returns:
        dict: {"success": bool, "message": str, "error": str}
    """
    if not all([username, code, new_password]):
        return {"success": False, "error": "Todos los parámetros son requeridos", "message": None}
    
    # Validar contraseña
    is_strong, error_msg = validate_password_strength(new_password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña débil: {error_msg}", "message": None}
    
    try:
        client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=username.strip(),
            ConfirmationCode=code.strip(),
            Password=new_password,
            SecretHash=get_secret_hash(username)
        )
        print(f"✅ Contraseña actualizada para {username}")
        return {
            "success": True,
            "message": "Contraseña actualizada ✅",
            "error": None
        }
    except client.exceptions.CodeMismatchException:
        return {
            "success": False, 
            "error": "Código incorrecto (verifica y vuelve a intentar)",
            "message": None
        }
    except client.exceptions.ExpiredCodeException:
        return {
            "success": False, 
            "error": "El código expiró, solicita uno nuevo",
            "message": None
        }
    except client.exceptions.InvalidPasswordException:
        return {
            "success": False, 
            "error": "La contraseña no cumple con los requisitos de Cognito",
            "message": None
        }
    except Exception as e:
        print(f"❌ Error en confirm_forgot_password: {e}")
        return {"success": False, "error": str(e), "message": None}

# ─── CAMBIAR CONTRASEÑA (usuario autenticado) ────────────────
def change_password(access_token: str, previous_password: str, proposed_password: str) -> dict:
    """
    Permite al usuario cambiar su contraseña usando su access token
    (para usuarios ya autenticados)
    
    Args:
        access_token: token de acceso válido
        previous_password: contraseña actual
        proposed_password: nueva contraseña
    
    Returns:
        dict: {"success": bool, "message": str, "error": str}
    """
    if not all([access_token, previous_password, proposed_password]):
        return {"success": False, "error": "Todos los parámetros son requeridos", "message": None}
    
    # Validar nueva contraseña
    is_strong, error_msg = validate_password_strength(proposed_password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña débil: {error_msg}", "message": None}
    
    if proposed_password == previous_password:
        return {"success": False, "error": "La nueva contraseña debe ser diferente a la actual", "message": None}
    
    try:
        client.change_password(
            AccessToken=access_token,
            PreviousPassword=previous_password,
            ProposedPassword=proposed_password
        )
        print(f"✅ Contraseña cambiada exitosamente")
        return {
            "success": True, 
            "message": "Contraseña actualizada ✅",
            "error": None
        }
    except client.exceptions.NotAuthorizedException:
        return {
            "success": False, 
            "error": "Contraseña anterior incorrecta",
            "message": None
        }
    except client.exceptions.InvalidPasswordException:
        return {
            "success": False, 
            "error": "La nueva contraseña no cumple con los requisitos",
            "message": None
        }
    except client.exceptions.InvalidParameterException:
        return {
            "success": False, 
            "error": "Token de acceso inválido o expirado",
            "message": None
        }
    except Exception as e:
        print(f"Error en change_password: {e}")
        return {"success": False, "error": str(e), "message": None}

# ─── ADMIN FUNCTIONS - COGNITO ADMIN API ────────────────────
def admin_delete_user(username: str) -> dict:
    """
    Elimina un usuario del Cognito User Pool (admin only)
    
    Args:
        username: username o email del usuario a eliminar
    
    Returns:
        dict: {"success": bool, "message": str, "error": str}
    """
    if not username:
        return {"success": False, "error": "Username requerido"}
    
    try:
        client.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=username.strip()
        )
        print(f"Usuario {username} eliminado de Cognito")
        return {
            "success": True, 
            "message": f"Usuario {username} eliminado",
            "error": None
        }
    except client.exceptions.UserNotFoundException:
        return {"success": False, "error": "Usuario no encontrado en Cognito"}
    except Exception as e:
        print(f"Error eliminando usuario: {e}")
        return {"success": False, "error": str(e)}

def admin_set_user_password(username: str, password: str, permanent: bool = True) -> dict:
    """
    Cambia la contraseña de un usuario (admin only)
    
    Args:
        username: username o email del usuario
        password: nueva contraseña
        permanent: si True, contraseña es permanente; si False, requiere cambio en nuevo login
    
    Returns:
        dict: {"success": bool, "message": str, "error": str}
    """
    if not username or not password:
        return {"success": False, "error": "Username y password requeridos"}
    
    # Validar contraseña
    is_strong, error_msg = validate_password_strength(password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña debil: {error_msg}"}
    
    try:
        client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username.strip(),
            Password=password,
            Permanent=permanent
        )
        print(f"Contraseña actualizada para {username}")
        return {
            "success": True, 
            "message": "Contraseña actualizada para el usuario",
            "error": None
        }
    except client.exceptions.UserNotFoundException:
        return {"success": False, "error": "Usuario no encontrado en Cognito"}
    except client.exceptions.InvalidPasswordException:
        return {"success": False, "error": "Contraseña no cumple requisitos de Cognito"}
    except Exception as e:
        print(f"Error en admin_set_user_password: {e}")
        return {"success": False, "error": str(e)}

def admin_update_user_attributes(username: str, attributes: dict) -> dict:
    """
    Actualiza atributos de un usuario (admin only)
    
    Args:
        username: username o email del usuario
        attributes: dict con atributos a actualizar (email, name, etc)
    
    Returns:
        dict: {"success": bool, "message": str, "error": str}
    """
    if not username or not attributes:
        return {"success": False, "error": "Username y attributes requeridos"}
    
    try:
        # Convertir a formato de Cognito
        user_attributes = [
            {"Name": key, "Value": str(value)} 
            for key, value in attributes.items()
        ]
        
        client.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=username.strip(),
            UserAttributes=user_attributes
        )
        print(f"Atributos actualizados para {username}")
        return {
            "success": True, 
            "message": "Atributos actualizados",
            "error": None
        }
    except client.exceptions.UserNotFoundException:
        return {"success": False, "error": "Usuario no encontrado en Cognito"}
    except client.exceptions.AliasExistsException:
        return {"success": False, "error": "El email ya esta siendo usado por otro usuario"}
    except Exception as e:
        print(f"Error en admin_update_user_attributes: {e}")
        return {"success": False, "error": str(e)}

