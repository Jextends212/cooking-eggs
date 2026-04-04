# ⏸️ Pausar/Reanudar AWS - Guía Rápida

## 🎯 El Problema

Tu app está corriendo en AWS y consume:
- **RDS Database**: ~$15/mes (el mayor costo)
- **Lambda + API**: ~$3/mes
- **CloudFront**: ~$3/mes
- **Total**: ~$21/mes

Con $180 USD en créditos, tienes para 9 meses. Pero puedes ahorrar pausando cuando no la uses.

---

## 🚀 OPCIÓN 1: Pausa Rápida (Recomendada)

Solo pausa RDS (donde está la mayoría del costo):

### Pausar:
```bash
python quick_pause.py --pause
```

✅ Resultado:
- RDS se detiene (1-2 min)
- Ahorras ~$15/mes
- Los datos se preservan
- Acceso a frontend sigue disponible

### Reanudar:
```bash
python quick_pause.py --resume
```

✅ Resultado:
- RDS se reinicia (2-5 min)
- Vuelve a costar ~$15/mes
- Todo funciona igual qu antes

### Ver estado:
```bash
python quick_pause.py --status
```

---

## 🛑 OPCIÓN 2: Pausa Completa (Full Shutdown)

Pausa RDS, CloudFront y Lambda completamente:

### Pausar TODO:
```bash
python pause_resources.py
```

Luego cuando pregunte:
```
Delete SAM stack? (type 'yes' to confirm): yes
```

✅ Resultado:
- RDS: ⏸️ Paused (~$15 saving)
- Lambda/API: 🗑️ Deleted (~$3 saving)
- CloudFront: 🔴 Disabled (~$3 saving)
- **Total Ahorro**: ~$21/mes
- S3 sigue disponible pero sin CDN

### Reanudar TODO:
```bash
python resume_resources.py
```

Cuando pregunte:
```
Redeploy SAM stack now? (type 'yes' to confirm): yes
```

✅ Resultado:
- RDS: ▶️ Starting (2-5 min)
- Lambda/API: 📦 Redeployed (3-5 min)
- CloudFront: 🟢 Enabled (5-15 min)
- Espera ~10-15 min total

---

## 🧊 OPCIÓN 3: Cold Storage (Máximo Ahorro)

Si no la vas a usar por MUCHO tiempo:

```bash
# 1. Pausa todo primero
python pause_resources.py
# Select: Yes para delete stack

# 2. Luego elimina snapshots viejos (opcional)
aws rds delete-db-snapshot --db-snapshot-identifier eggs-db-snapshot-XXXXXX --region us-east-2

# 3. Cuando quieras reactivar:
python resume_resources.py
```

✅ Resultado:
- Costo casi zero (~$0.50 solo S3)
- Todos los datos preservados
- 10-15 min para reactivar

---

## 💰 Comparativa de Costos

| Escenario | RDS | Lambda | CloudFront | **Total** | **Ahorro** |
|-----------|-----|--------|------------|-----------|-----------|
| **Completo** | $15 | $3 | $3 | **$21** | — |
| **RDS Pausado** | $0 | $3 | $3 | **$6** | $15 💚 |
| **Completo Pausado** | $0 | $0 | $0 | **$0.50** | $20.50 💚💚 |
| **Cold Storage** | $0 | $0 | $0 | **$0.50** | $20.50 💚💚 |

---

## ⚡ Comandos Rápidos

### Pausa rápida solamente RDS:
```bash
aws rds stop-db-instance --db-instance-identifier eggs-db --region us-east-2
```

### Reanudar RDS:
```bash
aws rds start-db-instance --db-instance-identifier eggs-db --region us-east-2
```

### Ver si RDS está corriendo:
```bash
aws rds describe-db-instances --db-instance-identifier eggs-db --region us-east-2 --query 'DBInstances[0].DBInstanceStatus'
```

### Eliminar stack SAM (full delete):
```bash
sam delete --stack-name coking-eggs --no-prompts
```

### Redeploy SAM (si lo eliminaste):
```bash
sam build
sam deploy --no-confirm-changeset
```

---

## 📱 Checklist de Pausa

- [ ] Ejecutar `python quick_pause.py --pause` (o opción full)
- [ ] Esperar a que RDS se pare (1-2 min)
- [ ] Verificar con `python quick_pause.py --status`
- [ ] ✅ Notarás que no hay cambios en frontend
- [ ] 💰 Empiezas a ahorrar dinero inmediatamente

---

## 📱 Checklist de Reactivación

- [ ] Ejecutar `python resume_resources.py`
- [ ] Esperar a que RDS inicie (2-5 min)
- [ ] Copiar la URL de CloudFront
- [ ] Acceder a `https://d19zwm3cutizk7.cloudfront.net`
- [ ] ✅ Verificar que todo funciona
- [ ] 💳 Costos vuelven a ~$21/mes

---

## ⚠️ Cosas Importantes

### ✅ Se Preserve:
- Base de datos (RDS)
- Usuarios (Cognito)
- Archivos frontend (S3)
- Stack configuration

### ❌ Se Pierde (si eliminas stack):
- API Gateway URL cambia (necesitas actualizar frontend)
- Lambda functions se recrean (igual configuración)
- SSM parameters se preservan

### 📝 Datos SIEMPRE seguros:
- Snapshots automáticos de RDS
- Backups de 7 días
- S3 versioning habilitado
- Cognito es inmutable

---

## 🆘 Si Algo Sale Mal

**"RDS no inicia"**
```bash
# Ver logs
aws rds describe-db-instances --db-instance-identifier eggs-db --region us-east-2
```

**"CloudFront sigue deshabilitado"**
```bash
# Habilitar manualmente
aws cloudfront update-distribution --id E2CF1UGAOEY54R # (necesita config completa)
```

**"Lambda functions no funcionan"**
```bash
# Redeploy
sam build && sam deploy --no-confirm-changeset
```

**"Datos perdidos"**
- No puede pasar si usas nuestros scripts
- Los datos SIEMPRE se preservan
- Snapshots disponibles por 7 días

---

## 📊 Monitoreo

Después de pausar, verifica costos:

```bash
# Ver costos actuales
python quick_pause.py --status

# En 1 mes, deberías ver:
# $21 → $0.50 (si todo está pausado)
```

En **AWS Console → Billing → Cost Explorer**, deberías ver la reducción.

---

## 🎓 Ejemplo Real

**Escenario:**
```
- Hoy: Pauso la app
- Costo mes actual: -$10 (pausé a mitad)
- Total créditos: $180 - $10 = $170

- En 2 meses: Reanudar
- Nuevos costos: $21/mes
- Créditos después de 4 más meses: $170 - (21×4) = $86

- Total: Con pausa estratégica, los $180 USD duran ~10-12 meses
```

---

## 📞 Preguntas Frecuentes

**P: ¿Se pierden los datos si pauso?**
A: NO. Los datos se preservan en RDS. Snapshots automáticos cada día.

**P: ¿Cuánto tardo en reanudar?**
A: Unos 5-10 minutos total (RDS 2-5min + CloudFront 5-15min)

**P: ¿Puedo pausar solo RDS?**
A: SÍ, es lo que recomendamos (ahorra $15 sin afectar frontend)

**P: ¿Qué pasa si se me olvida reanudar?**
A: Nada malo. Está pausado, punto. Solo que la app no funciona hasta que lo reactive.

**P: ¿Hay límite de pausas/reanudas?**
A: NO. Puedes pausar/reanudar ilimitadamente.

---

**¿Listo? Ejecuta:**
```bash
python quick_pause.py --pause
```

**¡Felicidades! Estás ahorrando dinero! 💚**
