import json
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.db_connection  import get_connection
from utils.cognito_client import get_user_from_token

def lambda_handler(event, context):
    try:
        http_method  = event.get("requestContext", {}).get("http", {}).get("method")
        headers      = event.get("headers") or {}
        access_token = headers.get("access-token") or headers.get("access_token")
        path         = event.get("rawPath", "")
        recipe_id    = (event.get("pathParameters") or {}).get("recipe_id")

        if not access_token:
            return _response(401, {"error": "Token requerido"})

        user = get_user_from_token(access_token)
        if not user["success"]:
            return _response(401, {"error": "Token inválido"})

        user_id = user["sub"]
        conn    = get_connection()

        with conn:
            with conn.cursor() as cursor:

                # ── GET /profile ─────────────────────────────
                if http_method == "GET" and "/favorites" not in path:
                    cursor.execute(
                        """SELECT up.avatar_emoji, up.bio, up.favorite_cuisine,
                                  u.email, u.username
                           FROM user_profiles up
                           LEFT JOIN users u ON up.user_id = u.id
                           WHERE up.user_id = %s""",
                        (user_id,)
                    )
                    profile = cursor.fetchone()

                    if not profile:
                        cursor.execute(
                            "INSERT IGNORE INTO user_profiles (user_id) VALUES (%s)",
                            (user_id,)
                        )
                        conn.commit()
                        return _response(200, {
                            "avatar_emoji":     "👨‍🍳",
                            "bio":              "",
                            "favorite_cuisine": "",
                            "email":            user.get("email", ""),
                            "username":         user.get("name", "")
                        })

                    # ✅ DictCursor → acceso por nombre de columna
                    return _response(200, {
                        "avatar_emoji":     profile.get("avatar_emoji") or "👨‍🍳",
                        "bio":              profile.get("bio") or "",
                        "favorite_cuisine": profile.get("favorite_cuisine") or "",
                        "email":            profile.get("email") or "",
                        "username":         profile.get("username") or ""
                    })

                # ── PUT /profile ─────────────────────────────
                elif http_method == "PUT" and "/favorites" not in path:
                    body             = json.loads(event.get("body", "{}"))
                    avatar_emoji     = body.get("avatar_emoji", "👨‍🍳")
                    bio              = body.get("bio", "")
                    favorite_cuisine = body.get("favorite_cuisine", "")

                    cursor.execute(
                        """INSERT INTO user_profiles (user_id, avatar_emoji, bio, favorite_cuisine)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                           avatar_emoji     = VALUES(avatar_emoji),
                           bio              = VALUES(bio),
                           favorite_cuisine = VALUES(favorite_cuisine)""",
                        (user_id, avatar_emoji, bio, favorite_cuisine)
                    )
                    conn.commit()
                    return _response(200, {"success": True, "message": "Perfil actualizado ✅"})

                # ── GET /profile/favorites ────────────────────
                elif http_method == "GET" and "/favorites" in path:
                    cursor.execute(
                        """SELECT id, title, ingredients, steps, tip, prep_time, created_at
                           FROM favorite_recipes
                           WHERE user_id = %s
                           ORDER BY created_at DESC""",
                        (user_id,)
                    )
                    favorites = [
                        {
                            "id":          f["id"],
                            "title":       f["title"],
                            "ingredients": f.get("ingredients") or "",
                            "steps":       f.get("steps") or "",
                            "tip":         f.get("tip") or "",
                            "prep_time":   f.get("prep_time") or "",
                            "created_at":  str(f["created_at"])
                        }
                        for f in cursor.fetchall()
                    ]
                    return _response(200, {"favorites": favorites})

                # ── POST /profile/favorites ───────────────────
                elif http_method == "POST" and "/favorites" in path:
                    body        = json.loads(event.get("body", "{}"))
                    title       = body.get("title", "").strip()
                    ingredients = body.get("ingredients", "")
                    steps       = body.get("steps", "")
                    tip         = body.get("tip", "")
                    prep_time   = body.get("prep_time", "")

                    if not title:
                        return _response(400, {"error": "Título de receta requerido"})

                    cursor.execute(
                        """INSERT INTO favorite_recipes
                           (user_id, title, ingredients, steps, tip, prep_time)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (user_id, title, ingredients, steps, tip, prep_time)
                    )
                    conn.commit()
                    return _response(201, {
                        "success":   True,
                        "recipe_id": cursor.lastrowid,
                        "message":   "Receta guardada en favoritos 💚"
                    })

                # ── DELETE /profile/favorites/{recipe_id} ─────
                elif http_method == "DELETE" and "/favorites" in path and recipe_id:
                    cursor.execute(
                        "SELECT id FROM favorite_recipes WHERE id = %s AND user_id = %s",
                        (recipe_id, user_id)
                    )
                    if not cursor.fetchone():
                        return _response(403, {"error": "Acceso denegado"})

                    cursor.execute(
                        "DELETE FROM favorite_recipes WHERE id = %s AND user_id = %s",
                        (recipe_id, user_id)
                    )
                    conn.commit()
                    return _response(200, {"success": True, "message": "Receta eliminada 🗑️"})

                else:
                    return _response(400, {"error": "Ruta no válida"})

    except Exception as e:
        return _response(500, {"error": str(e)})


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