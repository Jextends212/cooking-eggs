import boto3
import json
import os

REGION = os.getenv("BEDROCK_REGION", "us-east-2")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")

bedrock = boto3.client("bedrock-runtime", region_name=REGION)

SYSTEM_PROMPT = """Eres Chef Claude, un asistente culinario experto y apasionado.
Tu especialidad es:
- Sugerir recetas personalizadas según ingredientes disponibles
- Dar consejos y técnicas de cocina
- Proponer alternativas y sustituciones de ingredientes
- Calcular porciones y adaptar recetas
- Explicar el origen y cultura detrás de los platos

(máximo 150 palabras por respuesta).
Usa emojis de comida en cada respuesta 🥘🫕🥗🍜🥩🧄🥕🧅🍅


Responde siempre en el idioma en el que te hable el usuario,
con entusiasmo y de forma clara.
Usa emojis ocasionalmente para hacer la conversación más amena
Cuando des una receta usa este formato breve:
🍽️ Nombre del plato
⏱️ Tiempo: X minutos
🛒 Ingredientes: lista completa
👨‍🍳 Pasos: máximo 10 pasos cortos
✨ Tip rápido del chef"""

def ask_claude(messages: list) -> str:
    """
    messages: lista de dicts con formato:
    [{"role": "user", "content": "texto"}, {"role": "assistant", "content": "texto"}]
    """
    try:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 612,
            "system": SYSTEM_PROMPT,
            "messages": messages
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    except Exception as e:
        error_msg = str(e)
        # Si el modelo no está disponible, retornar una respuesta simulada para pruebas
        if "provided model identifier is invalid" in error_msg or "not valid" in error_msg:
            # Mock response para desarrollo/testing
            return """¡Hola! 🍗 Tengo justo la receta perfecta para ti:

🍽️ Arroz con Pollo al Estilo Casero
⏱️ Tiempo: 40 minutos
🛒 Ingredientes:
- Pollo (800g)
- Arroz (2 tazas)
- Tomates (3 medianos)
- Cebolla (1 grande)
- Ajo (3 dientes)
- Sal y pimienta al gusto
- Aceite (3 cucharadas)

👨‍🍳 Pasos:
1. Corta el pollo en trozos
2. Dora el pollo en aceite caliente
3. Agrega cebolla y ajo picados
4. Incorpora tomates en cubos
5. Añade arroz y mezcla bien
6. Vierte agua (4 tazas) y deja hervir
7. Cocina a fuego bajo 25 minutos
8. Sazona con sal y pimienta
9. Deja reposar 5 minutos
10. ¡Listo para servir!

✨ Tip: Si quieres más sabor, añade un poco de comino o pimentón
[NOTA: Esta es una respuesta de demostración - se requiere acceso a Bedrock para respuestas reales]"""
        return f"Error al contactar al chef: {error_msg}"