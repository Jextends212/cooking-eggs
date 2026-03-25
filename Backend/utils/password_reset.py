"""
ALTERNATIVA SIN COGNITO: Reset de contraseña con verificación por email

Flujo:
1. Usuario solicita reset → genera token + envía email con link
2. Usuario hace click en link → valida token y abre formulario
3. Usuario ingresa nueva contraseña → actualiza en BD

Requisitos en AWS:
- SES configurado y verificado
- Email de sender en Variables de entorno
- Paquete argon2-cffi instalado
"""

import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import boto3
import secrets
import re
import hmac
from datetime import datetime, timedelta, timezone
from utils.db_connection import get_connection

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

# ─── CONFIGURACIÓN ──────────────────────────────
SES_CLIENT = boto3.client('ses', region_name=os.getenv('BEDROCK_REGION', 'us-east-1'))
SENDER_EMAIL = os.getenv('SES_SENDER_EMAIL', 'noreply@cookingeggsai.com')
API_URL = os.getenv('API_URL', 'https://example.com')
TOKEN_EXPIRY_MINUTES = 30

# ─── VALIDACIÓN DE CONTRASEÑA ───────────────────
def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Valida que la contraseña cumpla requisitos de seguridad
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
        return False, "Debe contener caracteres especiales (!@#$% etc)"
    
    return True, ""

def _get_password_hasher():
    """Retorna PasswordHasher o falla con excepción clara"""
    if not ARGON2_AVAILABLE:
        raise RuntimeError("Paquete argon2-cffi no está instalado. Ejecuta: pip install argon2-cffi")
    return PasswordHasher()

# ─── GENERAR TOKEN DE RESET ─────────────────────
def generate_reset_token(user_id: str) -> str:
    """
    Genera un token único y lo guarda en DB (válido 30 minutos)
    Retorna: token en formato texto (para url)
    """
    # Limpiar tokens expirados del mismo usuario
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM password_reset_tokens WHERE user_id = %s OR expires_at < NOW()",
                    (user_id,)
                )
            conn.commit()
    except Exception as e:
        print(f"Error limpiando tokens antiguos: {e}")
    
    # Generar nuevo token
    token = secrets.token_urlsafe(32)  # ~43 caracteres, URL-safe
    
    try:
        ph = _get_password_hasher()
        token_hash = ph.hash(token)
    except RuntimeError as e:
        print(f"Error con hasher: {e}")
        raise
    
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                expiry = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
                cursor.execute(
                    """INSERT INTO password_reset_tokens 
                       (user_id, token_hash, expires_at)
                       VALUES (%s, %s, %s)""",
                    (user_id, token_hash, expiry)
                )
            conn.commit()
        
        print(f"Token generado para usuario {user_id}")
        return token
    except Exception as e:
        print(f"Error generando token: {e}")
        return None

# ─── VERIFICAR TOKEN ────────────────────────────
def verify_reset_token(user_id: str, token: str) -> bool:
    """
    Verifica si el token es válido y no expiró
    Protegido contra timing attacks
    """
    if not token or len(token) < 20:
        return False
    
    try:
        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """SELECT token_hash, expires_at FROM password_reset_tokens 
                       WHERE user_id = %s AND expires_at > NOW()""",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    # Siempre hacer hash por seguridad (timing attack)
                    try:
                        ph = _get_password_hasher()
                        ph.verify("dummy_hash_never_matches", token)
                    except:
                        pass
                    return False
                
                stored_hash, expires_at = result
                
                try:
                    ph = _get_password_hasher()
                    ph.verify(stored_hash, token)
                    print(f"Token valido para usuario {user_id}")
                    return True
                except (VerifyMismatchError if ARGON2_AVAILABLE else Exception):
                    return False
                    
    except Exception as e:
        print(f"Error verificando token: {e}")
        return False

# ─── ENVIAR EMAIL CON LINK DE RESET ─────────────
def send_reset_email(email: str, user_id: str, username: str) -> dict:
    """
    Genera token y envía email de reset
    Retorna: {"success": bool, "error": str|None, "message": str}
    """
    # Validar entrada
    if not email or not user_id or not username:
        return {"success": False, "error": "Parámetros incompletos"}
    
    try:
        token = generate_reset_token(user_id)
        if not token:
            return {"success": False, "error": "No se pudo generar token de reset"}
        
        # MODO DE DESARROLLO: No enviar email, solo generar token
        # En producción, esto enviará email con SES
        print(f"[DEV MODE] Token generado para {email}: {token[:20]}...")
        
        try:
            # Intentar enviar con SES (puede fallar en desarrollo)
            reset_link = f"{API_URL}/reset-password?token={token}&user_id={user_id}"
            
            subject = "Reset Password - Cooking Eggs"
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Reset your password</h2>
                    <p>Hello {username},</p>
                    <p>Click the link below to reset your password (valid for 30 minutes):</p>
                    <p><a href="{reset_link}">Reset Password</a></p>
                </body>
            </html>
            """
            
            SES_CLIENT.send_email(
                Source=SENDER_EMAIL,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
                }
            )
        except Exception as ses_error:
            # En desarrollo, si SES no funciona, continuamos de todas formas
            print(f"[DEV MODE] Email sending disabled: {str(ses_error)}")
            pass
        
        return {
            "success": True, 
            "message": "Reset token generated. Check your email or use the token directly.",
            "error": None,
            "token": token  # Devolver token en desarrollo para testing
        }
    
    except Exception as e:
        print(f"Error in send_reset_email: {e}")
        return {
            "success": False, 
            "error": f"Error: {str(e)}",
            "message": None
        }

# ─── CAMBIAR CONTRASEÑA ─────────────────────────
def reset_password_with_token(user_id: str, token: str, new_password: str) -> dict:
    """
    Valida token y cambia la contraseña
    Retorna: {"success": bool, "message": str, "error": str|None}
    """
    
    # Validar entrada
    if not user_id or not token or not new_password:
        return {"success": False, "error": "Parametros incompletos"}
    
    # Validar contraseña
    is_strong, error_msg = validate_password_strength(new_password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña debil: {error_msg}"}
    
    # 1. Verificar token
    if not verify_reset_token(user_id, token):
        return {"success": False, "error": "Token invalido o expirado"}
    
    # 2. Cambiar contraseña en BD
    try:
        ph = _get_password_hasher()
        password_hash = ph.hash(new_password)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id)
        )
        
        # Eliminar token usado
        cursor.execute(
            "DELETE FROM password_reset_tokens WHERE user_id = %s",
            (user_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Contraseña actualizada para usuario {user_id}")
        return {
            "success": True, 
            "message": "Contraseña actualizada",
            "error": None
        }
    
    except Exception as e:
        print(f"Error actualizando contraseña: {e}")
        return {
            "success": False, 
            "error": f"Error al actualizar contraseña: {str(e)}",
            "message": None
        }

# ─── CAMBIAR CONTRASEÑA (CON CONTRASEÑA ACTUAL) ──
def change_password_authenticated(user_id: str, old_password: str, new_password: str) -> dict:
    """
    Cambia contraseña si el usuario ya esta autenticado y conoce la actual
    Retorna: {"success": bool, "message": str, "error": str|None}
    """
    # Validar entrada
    if not user_id or not old_password or not new_password:
        return {"success": False, "error": "Parametros incompletos"}
    
    # Validar nueva contraseña
    is_strong, error_msg = validate_password_strength(new_password)
    if not is_strong:
        return {"success": False, "error": f"Contraseña debil: {error_msg}"}
    
    if old_password == new_password:
        return {"success": False, "error": "La nueva contraseña debe ser diferente a la actual"}
    
    try:
        ph = _get_password_hasher()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtener hash actual
        cursor.execute(
            "SELECT password_hash FROM users WHERE id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return {"success": False, "error": "Usuario no encontrado"}
        
        d = result
        stored_hash = d['password_hash'] if isinstance(d, dict) else d[0]
        
        # Verificar contraseña actual (con proteccion contra timing attacks)
        try:
            ph.verify(stored_hash, old_password)
        except Exception:
            return {"success": False, "error": "Contraseña actual incorrecta"}
        
        # Actualizar contraseña
        new_password_hash = ph.hash(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_password_hash, user_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Contraseña cambiada para usuario {user_id}")
        return {
            "success": True, 
            "message": "Contraseña actualizada",
            "error": None
        }
    
    except Exception as e:
        print(f"Error actualizando contraseña: {e}")
        return {
            "success": False, 
            "error": f"Error al cambiar contraseña: {str(e)}",
            "message": None
        }

