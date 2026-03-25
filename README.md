# 🍳 Coking Eggs - Chatbot Admin Platform

Una plataforma de chatbot completa con panel de administración, integrada con AWS Lambda, Cognito, RDS y Anthropic Claude.

## 🎯 Características Principales

### Backend (AWS Lambda)
- **Autenticación**: Integración con AWS Cognito
- **Chat**: Conversaciones con IA (Anthropic Claude)
- **Gestión de Usuarios**: CRUD de usuarios, roles (admin/user)
- **Historial**: Persistencia de conversaciones
- **Perfiles**: Gestión de datos de usuario

### Frontend
- **Chat Interface**: Interfaz moderna y responsiva
- **Panel Admin**: Gestión completa de usuarios
- **Autenticación**: Login/Register/Password Reset
- **Avatares**: Selección personalizada
- **CloudFront CDN**: Distribución global

### Infraestructura
- **AWS Lambda**: Funciones serverless (Python 3.12)
- **API Gateway**: REST API
- **RDS MySQL**: Base de datos
- **S3 + CloudFront**: Hosting estático del frontend
- **SSM Parameter Store**: Gestión segura de credenciales
- **AWS SAM**: Infrastructure as Code

## 📁 Estructura del Proyecto

```
coking-eggs/
├── Backend/
│   ├── lamb/                    # Lambda handlers
│   │   ├── admin_handler.py     # Endpoints admin
│   │   ├── auth_handler.py      # Autenticación
│   │   ├── chat_handler.py      # Chat con IA
│   │   ├── history_handler.py   # Historial
│   │   ├── profile_handler.py   # Perfiles
│   │   └── Backend/utils/       # Módulos compartidos
│   └── utils/                   # Utilidades reutilizables
├── Frontend/                    # Aplicación web
│   ├── index.html              # Home
│   ├── chat.html               # Chat principal
│   ├── admin.html              # Panel admin
│   ├── reset-password.html     # Recuperar contraseña
│   ├── CSS/styles.css          # Estilos
│   └── JS/
│       ├── auth.js             # Autenticación
│       ├── chat.js             # Chat logic
│       └── admin.js            # Admin logic
├── events/                      # Eventos SAM para testing
├── template.yaml               # SAM template
├── requirements.txt            # Dependencias Python
└── deploy_frontend.py          # Script deploy CloudFront
```

## 🚀 Deployment

### Backend (Lambda + API)
```bash
# Compilar y desplegar
sam build
sam deploy --no-confirm-changeset
```

### Frontend (CloudFront)
```bash
# Deploy automático a S3 + CloudFront
python deploy_frontend.py
```

## 🔐 Seguridad

- ✅ Credenciales en **AWS SSM Parameter Store** (no en código)
- ✅ **S3 privado** con acceso solo desde CloudFront (OAI)
- ✅ **HTTPS** enforced
- ✅ **CORS** configurado para API Gateway
- ✅ **IAM roles** mínimos por función Lambda
- ⚠️ `.gitignore` excluye archivos sensibles

## 📊 Variantes de Autenticación

### Cognito (Actual - Recomendado)
- Gestión de usuarios completamente en AWS
- MFA disponible
- Integración simple

### Alternativa: Custom con JWT
- Stored en RDS
- SES para email verification
- Más control personalizado

Ver: `Backend/utils/password_reset.py`

## 💰 Costos

| Servicio | Estimado |
|----------|----------|
| Lambda | ~$1-3/mes |
| RDS (t2.micro) | ~$15/mes |
| S3 + CloudFront | ~$0.50-3/mes |
| **Total** | **~$17/mes** |

Con $180 USD en créditos: **~12-18 meses**

## 📝 Notas de Desarrollo

- Backend usa **Python 3.12**
- Frontend es **vanilla JavaScript** (sin frameworks)
- Base de datos: **MySQL** en AWS RDS
- IA: **Anthropic Claude 3.5 Haiku**

## 🔄 Flujo de Actualización

1. Cambiar código en `Backend/` o `Frontend/`
2. Para Backend: `sam build && sam deploy`
3. Para Frontend: `python deploy_frontend.py`
4. Invalidar CloudFront si es necesario

## 📧 Contacto & Créditos

Proyecto: Coking Eggs Chatbot
Desarrollador: Jextends212

---

**⚠️ IMPORTANTE**: Las credenciales (DB_PASSWORD, COGNITO_CLIENT_SECRET) se almacenan en **AWS SSM Parameter Store**, NO en el código fuente.
