# 💰 AWS Cost Management Guide - Coking Eggs

## 🎯 Overview

Tu proyecto tiene costos mensuales de aproximadamente **$17-21/mes**. Con **$180 USD** en créditos, tienes para **9-10 meses** de operación normal.

Puedes **pausar los recursos** para evitar costos y reactivarlos cuando lo necesites.

---

## 📊 Current Monthly Costs

| Service | Tier | Cost |
|---------|------|------|
| **RDS MySQL** (t4g.micro) | 730 hours/month | ~$15 |
| **Lambda** | 1M requests/month | ~$1-2 |
| **CloudFront** | ~1GB/month transfer | ~$0.085 |
| **S3** | 165KB storage | ~$0.004 |
| **Cognito** | $0.5 per 50k requests | ~$0.50 |
| **Bedrock** | Pay per use | Variable |
| **API Gateway** | $3.50 per 1M requests | ~$0.50 |
| **SSM Parameter Store** | Free tier | $0 |
| **CloudFormation** | No charge | $0 |
| **Total** | | **~$17-20/month** |

---

## 🛑 How to Pause Everything

### Option 1: Pause RDS Only (Recommended)
**Saves:** ~$15/month  
**Impact:** App will show "Database offline" message  
**Data:** Preserved in snapshots  
**Resumable:** Yes, 2-5 minutes to start

```bash
python pause_resources.py
# Select: No for Lambda/API stack deletion
```

**Manual pause (CLI):**
```bash
aws rds stop-db-instance \
  --db-instance-identifier eggs-db \
  --region us-east-2
```

### Option 2: Pause RDS + Disable CloudFront
**Saves:** ~$18/month  
**Impact:** Frontend unavailable via CDN, but S3 still accessible  
**Data:** Preserved  
**Resumable:** Yes

```bash
python pause_resources.py
# Select: No for Lambda/API stack deletion
```

### Option 3: Complete Shutdown (All except S3)
**Saves:** ~$19/month  
**Impact:** Complete app offline  
**Data:** Preserved  
**Resumable:** Yes, requires redeploy (3-5 min)

```bash
python pause_resources.py
# Select: Yes for Lambda/API stack deletion
```

**Manual delete:**
```bash
sam delete --stack-name coking-eggs --no-prompts
```

---

## ▶️ How to Resume

### Quick Resume (RDS + CloudFront)
```bash
python resume_resources.py
# Automatic resume in 5-10 minutes
```

### Full Resume (if stack was deleted)
```bash
python resume_resources.py
# Will prompt to redeploy SAM stack
# Full redeploy: 3-5 minutes
```

**Manual resume steps:**

1. **Start RDS:**
```bash
aws rds start-db-instance \
  --db-instance-identifier eggs-db \
  --region us-east-2
```

2. **Enable CloudFront:**
```bash
aws cloudfront get-distribution --id E2CF1UGAOEY54R # Get config
aws cloudfront update-distribution \
  --id E2CF1UGAOEY54R \
  --distribution-config file://distribution-config.json
```

3. **Redeploy Lambda (if deleted):**
```bash
sam build
sam deploy --no-confirm-changeset
```

---

## 🔍 Monitoring Costs

### In AWS Console:
1. Go to **Billing Dashboard**
2. Check **Cost Explorer** for breakdown
3. Set **Budget Alerts** (recommended $200/month)

### CLI:
```bash
# Get current month costs
aws ce get-cost-and-usage \
  --time-period Start=2026-04-01,End=2026-04-30 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --region us-east-2
```

---

## 💡 Cost Optimization Tips

### 1. **Auto-Pause on Schedule** ⏰
```bash
# Pause during night (cron job on your local machine)
# Saves: $15 × (8 hours / 24 hours) = $5/month additional reduction
```

### 2. **Reserved Instances** (if keeping it long-term)
- RDS t4g.micro 1-year reserved: ~$8/month (vs $15 on-demand)
- **Saves:** $7/month = $84/year

### 3. **Reduce Bedrock Usage**
- Current: Claude 3.5 Haiku (~$0.80 per 1M input tokens)
- Alternative: Use Claude 3.5 Opus when really needed
- Savings depend on usage

### 4. **Enable S3 Lifecycle**
- Move old chat logs to Glacier: $4 per TB/month → $0.004 per TB/month
- Saves storage costs long-term

---

## 📋 Resource Status Verification

### Check RDS Status
```bash
aws rds describe-db-instances \
  --db-instance-identifier eggs-db \
  --region us-east-2 \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Engine:Engine,InstanceClass:DBInstanceClass}'
```

### Check CloudFront Status
```bash
aws cloudfront get-distribution-config \
  --id E2CF1UGAOEY54R \
  --query 'DistributionConfig.Enabled'
```

### Check Lambda Stack
```bash
aws cloudformation describe-stacks \
  --stack-name coking-eggs \
  --region us-east-2 \
  --query 'Stacks[0].{Status:StackStatus,Created:CreationTime}'
```

---

## 🔐 Data Preservation

### RDS Database
- **Paused:** Manual snapshot created before pause
- **Stops:** Automatic daily backups
- **Deleted Stack:** RDS data remains (stack deletion ≠ data deletion)
- **Check snapshots:**
```bash
aws rds describe-db-snapshots \
  --db-instance-identifier eggs-db \
  --region us-east-2
```

### S3 Frontend
- **Always preserved** - Uploading new files required to update
- **Versioning enabled** - Can rollback to previous versions

### Cognito Users
- **Always preserved** in user pool
- Only deleted if you manually remove users

---

## ❌ What Gets Lost

⚠️ **These are permanent if deleted:**
- Lambda functions (code, but not data)
- API Gateway (URLs change if recreated)
- SSM Parameters (if manually deleted)
- Cognito users (if manually deleted)

### Safe to delete/pause:
- RDS data: ✅ Safe (snapshots + backups)
- Lambda code: ✅ Safe (redeploy from repo)
- S3 files: ✅ Safe (versioning enabled)
- Cognito: ✅ Safe (user pool preserved)

---

## 🎲 Quick Decision Tree

**For 1-2 weeks off?**
→ Just pause RDS (cheapest: ~$15 savings)

**For 1-2 months?**
→ Pause RDS + disable CloudFront (~$18 savings)

**For 3+ months?**
→ Delete entire SAM stack (~$19 savings)
→ Keep RDS snapshots for backup

**Forgot about it?**
→ Set billing alert to $200 USD to prevent surprises

---

## 📞 Emergency Stop

If you accidentally leave something running and want **immediate halt:**

```bash
# Nuclear option - stop everything
python pause_resources.py  # All-in-one

# Or individually:
aws rds stop-db-instance --db-instance-identifier eggs-db --region us-east-2
aws cloudfront update-distribution --id E2CF1UGAOEY54R # (disable)
sam delete --stack-name coking-eggs --no-prompts
```

---

## 📈 Cost Tracking

Keep these files updated:
- `pause_state.json` - When you paused
- `resume_state.json` - When you resumed

This helps track how much you've actually saved!

---

**💬 Need help?** Check AWS documentation or edit this file with your custom notes.
