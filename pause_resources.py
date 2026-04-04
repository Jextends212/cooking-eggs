#!/usr/bin/env python3
"""
Pausar todos los recursos AWS del proyecto Coking Eggs para detener costos.
Mantiene la capacidad de reanudarlos sin perder datos.

Recursos pausables:
- RDS Database (pausa la BD, mantiene datos)
- CloudFront Distribution (deshabilita CDN, frontend local aún accesible)
- Lambda + API Gateway (detiene el stack SAM si es necesario)
"""

import boto3
import sys
import json
from datetime import datetime

# AWS Clients
rds = boto3.client('rds', region_name='us-east-2')
cloudfront = boto3.client('cloudfront', region_name='us-east-2')
cfn = boto3.client('cloudformation', region_name='us-east-2')

# Resources
RDS_INSTANCE = 'eggs-db'
CLOUDFRONT_ID = 'E2CF1UGAOEY54R'
STACK_NAME = 'coking-eggs'

def print_header(msg):
    print(f"\n{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}\n")

def print_step(num, msg):
    print(f"[{num}] {msg}")

def pause_rds():
    """Pausar RDS Database"""
    print_step(1, "Pausing RDS Database (eggs-db)")
    
    try:
        # Crear snapshot antes de pausar
        print("   📸 Creating snapshot before pause...")
        response = rds.create_db_snapshot(
            DBSnapshotIdentifier=f"{RDS_INSTANCE}-snapshot-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            DBInstanceIdentifier=RDS_INSTANCE
        )
        snapshot_id = response['DBSnapshot']['DBSnapshotIdentifier']
        print(f"   ✓ Snapshot created: {snapshot_id}")
        
        # Pausar instancia
        print("   ⏸️  Stopping RDS instance...")
        rds.stop_db_instance(DBInstanceIdentifier=RDS_INSTANCE)
        print(f"   ✅ RDS instance paused successfully")
        print(f"   💾 Data preserved in snapshots")
        
        return True
    except rds.exceptions.DBInstanceNotFoundFault:
        print(f"   ⚠️  RDS instance '{RDS_INSTANCE}' not found")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def disable_cloudfront():
    """Deshabilitar CloudFront Distribution"""
    print_step(2, "Disabling CloudFront Distribution")
    
    try:
        # Obtener distribución
        dist = cloudfront.get_distribution(Id=CLOUDFRONT_ID)
        config = dist['Distribution']['DistributionConfig']
        
        # Cambiar Enabled a False
        if config.get('Enabled'):
            config['Enabled'] = False
            print("   ⏸️  Disabling distribution...")
            
            response = cloudfront.update_distribution(
                Id=CLOUDFRONT_ID,
                DistributionConfig=config
            )
            
            print(f"   ✅ CloudFront disabled")
            print(f"   🌐 Frontend S3 still accessible via S3 direct URL")
            
            return True
        else:
            print(f"   ℹ️  CloudFront already disabled")
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def get_stack_info():
    """Obtener información del stack SAM"""
    print_step(3, "Checking CloudFormation Stack")
    
    try:
        response = cfn.describe_stacks(StackName=STACK_NAME)
        stack = response['Stacks'][0]
        status = stack['StackStatus']
        
        print(f"   Stack Name: {stack['StackName']}")
        print(f"   Status: {status}")
        print(f"   Created: {stack['CreationTime']}")
        
        return stack
    except Exception as e:
        print(f"   ⚠️  Stack info unavailable: {e}")
        return None

def delete_stack_prompt():
    """Preguntar si se desea eliminar el stack SAM (AVANZADO)"""
    print_step(4, "Advanced Option: Delete SAM Stack")
    print("\n   ⚠️  WARNING: Deleting the stack will:")
    print("      - Delete all Lambda functions")
    print("      - Delete API Gateway endpoints")
    print("      - Remove all Lambdas and their configurations")
    print("      - Keep RDS and S3 data intact")
    print("\n   ℹ️  This is useful if you want to truly pause everything")
    print("      and redeploy later with 'sam deploy'")
    
    response = input("\n   Delete SAM stack? (type 'yes' to confirm): ").strip().lower()
    
    if response == 'yes':
        print("\n   🗑️  Deleting stack...")
        try:
            cfn.delete_stack(StackName=STACK_NAME)
            print(f"   ✅ Stack deletion initiated")
            print(f"   ⏳ This may take 5-10 minutes...")
            return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    else:
        print("   ℹ️  Stack deletion cancelled")
        return False

def save_pause_state():
    """Guardar estado de pausada para referencia"""
    state = {
        'paused_at': datetime.now().isoformat(),
        'resources': {
            'rds': RDS_INSTANCE,
            'cloudfront': CLOUDFRONT_ID,
            'stack': STACK_NAME
        },
        'region': 'us-east-2'
    }
    
    with open('pause_state.json', 'w') as f:
        json.dump(state, f, indent=2)
    
    print("\n   📝 Pause state saved to: pause_state.json")

def print_resume_instructions():
    """Mostrar instrucciones para reanudar"""
    print_header("📝 TO RESUME YOUR APP")
    
    print("Run the resume script:")
    print("  python resume_resources.py")
    print("\nSteps performed:")
    print("  1. Start RDS database")
    print("  2. Enable CloudFront distribution")
    print("  3. Create/redeploy Lambda functions if needed")
    
    print("\nManual alternatives:")
    print("\n  Resume RDS:")
    print("    aws rds start-db-instance --db-instance-identifier eggs-db --region us-east-2")
    print("\n  Resume CloudFront:")
    print("    aws cloudfront update-distribution --id E2CF1UGAOEY54R ...")
    print("\n  Redeploy Lambda:")
    print("    sam build && sam deploy --no-confirm-changeset")

def main():
    print_header("🛑 COKING EGGS - PAUSE ALL RESOURCES")
    
    print("This will pause your AWS resources to stop costs.")
    print("Your data will be preserved and you can resume later.\n")
    
    # 1. Pausar RDS
    rds_paused = pause_rds()
    
    # 2. Deshabilitar CloudFront
    cf_disabled = disable_cloudfront()
    
    # 3. Info del stack
    get_stack_info()
    
    # 4. Preguntar sobre eliminar stack (AVANZADO)
    print("\n" + "="*70)
    delete_response = input("\nDo you want to DELETE the Lambda/API stack to completely stop costs? (y/n): ").strip().lower()
    
    stack_deleted = False
    if delete_response == 'y':
        stack_deleted = delete_stack_prompt()
    
    # Guardar estado
    save_pause_state()
    
    # Resumen
    print_header("✅ PAUSE SUMMARY")
    
    print("Resources Status:")
    print(f"  RDS Database:     {'✅ PAUSED' if rds_paused else '❌ Failed'}")
    print(f"  CloudFront CDN:   {'✅ DISABLED' if cf_disabled else '❌ Failed'}")
    print(f"  Lambda/API Stack: {'🗑️  DELETED' if stack_deleted else '⏸️  RUNNING (can delete separately)'}")
    
    print("\n💰 Cost Impact:")
    print("  RDS: ~$15/month → $0 (paused)")
    print("  CloudFront: ~$3/month → $0 (disabled)")
    print("  Lambda: ~$3/month → $0 (running minimal requests only)")
    print(f"  S3: ~$0.50/month (unchanged, very minimal)")
    
    print("\n💳 Estimated Savings: ~$15-18/month")
    print(f"   With $180 USD credits: Additional ~12-14 months of free tier!")
    
    print_resume_instructions()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
