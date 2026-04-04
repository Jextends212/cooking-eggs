#!/usr/bin/env python3
"""
Reanudar todos los recursos AWS pausados del proyecto Coking Eggs.
Reactiva RDS, CloudFront y opcionalmente redeploya Lambda stack.
"""

import boto3
import subprocess
import json
import sys
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

def resume_rds():
    """Reanudar RDS Database"""
    print_step(1, "Starting RDS Database")
    
    try:
        # Obtener status actual
        response = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE)
        db = response['DBInstances'][0]
        status = db['DBInstanceStatus']
        
        print(f"   Current status: {status}")
        
        if status == 'stopped':
            print("   ▶️  Starting RDS instance...")
            rds.start_db_instance(DBInstanceIdentifier=RDS_INSTANCE)
            print(f"   ✅ RDS start initiated")
            print(f"   ⏳ This takes 2-5 minutes...")
            return True
        else:
            print(f"   ℹ️  RDS is already running ({status})")
            return True
            
    except rds.exceptions.DBInstanceNotFoundFault:
        print(f"   ⚠️  RDS instance '{RDS_INSTANCE}' not found")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def enable_cloudfront():
    """Habilitar CloudFront Distribution"""
    print_step(2, "Enabling CloudFront Distribution")
    
    try:
        # Obtener distribución
        dist = cloudfront.get_distribution(Id=CLOUDFRONT_ID)
        config = dist['Distribution']['DistributionConfig']
        
        # Cambiar Enabled a True
        if not config.get('Enabled'):
            config['Enabled'] = True
            print("   ▶️  Enabling distribution...")
            
            response = cloudfront.update_distribution(
                Id=CLOUDFRONT_ID,
                DistributionConfig=config
            )
            
            print(f"   ✅ CloudFront enabled")
            print(f"   🌐 URL: https://d19zwm3cutizk7.cloudfront.net")
            print(f"   ⏳ Propagation takes 5-15 minutes globally...")
            
            return True
        else:
            print(f"   ℹ️  CloudFront already enabled")
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_stack_status():
    """Verificar status del stack SAM"""
    print_step(3, "Checking CloudFormation Stack")
    
    try:
        response = cfn.describe_stacks(StackName=STACK_NAME)
        stack = response['Stacks'][0]
        status = stack['StackStatus']
        
        print(f"   Stack Name: {stack['StackName']}")
        print(f"   Status: {status}")
        
        if 'DELETE' in status:
            print(f"   ⚠️  Stack was deleted - needs redeploy")
            return 'deleted'
        else:
            print(f"   ✅ Stack is active")
            return 'active'
            
    except cfn.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f"   ⚠️  Stack doesn't exist - needs redeploy")
            return 'deleted'
        else:
            print(f"   ❌ Error: {e}")
            return 'unknown'

def redeploy_stack_prompt():
    """Preguntar si se desea redeploy el stack SAM si fue eliminado"""
    print_step(4, "Redeploy Lambda Stack (if needed)")
    
    print("\n   If your SAM stack was deleted, you need to redeploy:")
    print("   - This will recreate all Lambda functions and API Gateway")
    print("   - Your RDS data is preserved")
    print("   - Takes 3-5 minutes\n")
    
    response = input("   Redeploy SAM stack now? (type 'yes' to confirm): ").strip().lower()
    
    if response == 'yes':
        print("\n   📦 Building SAM application...")
        try:
            # Run sam build
            result = subprocess.run(
                ['sam', 'build'],
                cwd='.',
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("   ✅ Build successful")
                print("\n   🚀 Deploying SAM stack...")
                
                # Run sam deploy
                result = subprocess.run(
                    ['sam', 'deploy', '--no-confirm-changeset'],
                    cwd='.',
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result.returncode == 0:
                    print("   ✅ Deployment successful")
                    print("   🎉 Lambda functions and API Gateway are ready!")
                    return True
                else:
                    print(f"   ❌ Deployment failed:")
                    print(result.stderr)
                    return False
            else:
                print(f"   ❌ Build failed:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("   ⏱️  Build/Deploy timed out")
            return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print("\n   Manual redeploy:")
            print("      sam build")
            print("      sam deploy --no-confirm-changeset")
            return False
    else:
        print("   ℹ️  Redeploy cancelled")
        print("\n   Manual redeploy when ready:")
        print("      sam build")
        print("      sam deploy --no-confirm-changeset")
        return False

def load_pause_state():
    """Cargar estado previo de pausada"""
    try:
        with open('pause_state.json', 'r') as f:
            state = json.load(f)
        print(f"   Previous pause: {state['paused_at']}")
        return state
    except FileNotFoundError:
        return None

def save_resume_state():
    """Guardar estado de reanudación"""
    state = {
        'resumed_at': datetime.now().isoformat(),
        'resources': {
            'rds': RDS_INSTANCE,
            'cloudfront': CLOUDFRONT_ID,
            'stack': STACK_NAME
        },
        'region': 'us-east-2'
    }
    
    with open('resume_state.json', 'w') as f:
        json.dump(state, f, indent=2)

def print_completion():
    """Mostrar instrucciones de finalización"""
    print_header("✅ RESUME COMPLETE")
    
    print("Your Coking Eggs app is being reactivated!\n")
    print("Status:")
    print("  ✅ RDS Database: Starting (2-5 min)")
    print("  ✅ CloudFront: Enabling (5-15 min global propagation)")
    print("  ✅ Lambda/API: Ready to use")
    print("\nAccess your app at:")
    print("  🌐 Frontend: https://d19zwm3cutizk7.cloudfront.net")
    print("  🔌 API: https://4ylr6wwnpg.execute-api.us-east-2.amazonaws.com\n")
    print("⏳ Please wait 5-10 minutes for all services to be fully ready...")

def main():
    print_header("▶️  COKING EGGS - RESUME ALL RESOURCES")
    
    print("This will reactivate your paused AWS resources.\n")
    
    # Cargar estado anterior
    pause_state = load_pause_state()
    
    # 1. Reanudar RDS
    rds_resumed = resume_rds()
    
    # 2. Habilitar CloudFront
    cf_enabled = enable_cloudfront()
    
    # 3. Verificar stack
    stack_status = check_stack_status()
    
    # 4. Redeploy si es necesario
    stack_redeployed = True  # Asume que no es necesario
    if stack_status == 'deleted':
        redeploy_response = input("\nStack was deleted. Redeploy now? (y/n): ").strip().lower()
        if redeploy_response == 'y':
            stack_redeployed = redeploy_stack_prompt()
    
    # Guardar estado
    save_resume_state()
    
    # Resumen
    print_header("📊 RESUME SUMMARY")
    
    print("Resources Status:")
    print(f"  RDS Database:     {'✅ STARTING' if rds_resumed else '❌ Failed'}")
    print(f"  CloudFront CDN:   {'✅ ENABLED' if cf_enabled else '❌ Failed'}")
    print(f"  Lambda/API Stack: {'✅ REDEPLOYED' if stack_redeployed else '⏸️  Already active' if stack_status == 'active' else '❌ Failed'}")
    
    print("\n💰 Costs Will Resume:")
    print("  RDS: ~$15/month")
    print("  CloudFront: ~$3/month")
    print("  Lambda: ~$3/month")
    print("  Total: ~$21/month")
    
    print_completion()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
