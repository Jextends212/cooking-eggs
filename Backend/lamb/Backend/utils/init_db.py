import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def init_db_connection():
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            ssl_disabled=False,
            autocommit=True,
            ssl_ca='./global-bundle.pem'
        )

        cur = conn.cursor()

        #Test
        cur.execute("SELECT VERSION();")
        print("✅ MySQL version:", cur.fetchone()[0])

        #Crear BD si no existe
        db_name = os.getenv("DB_NAME", "cooking_eggs")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"✅ Base de datos '{db_name}' lista")

        #Cambiar a la BD
        cur.execute(f"USE {db_name}")

        #Ejecutar schema
        schema_path = "Backend/lamb/db/schema.sql"
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()

            errores = 0
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    try:
                        cur.execute(statement)
                    except mysql.connector.errors.ProgrammingError as e:
                        if "already exists" in str(e):
                            print(f"⚠️  Tabla ya existe, continuando...")
                        else:
                            print(f"❌ Error en statement: {e}")
                            errores += 1

            if errores == 0:
                print("✅ Schema ejecutado correctamente")
            else:
                print(f"⚠️  Schema ejecutado con {errores} errores")
        else:
            print("⚠️ No se encontró schema.sql")

        #Mostrar tablas actuales
        cur.execute("SHOW TABLES")
        tablas = [t[0] for t in cur.fetchall()]
        print(f"\n📋 Tablas en BD ({len(tablas)}):")
        for t in tablas:
            print(f"   ✅ {t}")

        print("\n✅ Base de datos inicializada correctamente")

    except Exception as e:
        print(f"❌ Database error: {e}")
        raise

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_db_connection()