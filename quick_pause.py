#!/usr/bin/env python3
"""
Herramienta simple de una línea para pausar/reanudar recursos AWS
Uso: python quick_pause.py --pause  o  python quick_pause.py --resume
"""

import boto3
import sys
import argparse
from datetime import datetime

rds = boto3.client('rds', region_name='us-east-2')
cloudfront = boto3.client('cloudfront', region_name='us-east-2')

RDS_INSTANCE = 'eggs-db'
CLOUDFRONT_ID = 'E2CF1UGAOEY54R'

def pause_all():
    """Pausar RDS rápidamente"""
    print("⏸️  Pausing RDS Database...")
    try:
        rds.stop_db_instance(DBInstanceIdentifier=RDS_INSTANCE)
        print("✅ RDS paused successfully")
        print(f"⏳ Takes 1-2 minutes to fully stop")
        print(f"💰 Saving ~$15/month")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def resume_all():
    """Reanudar RDS rápidamente"""
    print("▶️  Starting RDS Database...")
    try:
        rds.start_db_instance(DBInstanceIdentifier=RDS_INSTANCE)
        print("✅ RDS start initiated")
        print(f"⏳ Takes 2-5 minutes to fully start")
        print(f"Ready to use soon!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def status():
    """Ver estado actual de recursos"""
    print("\n📊 Current Resource Status:\n")
    
    # RDS Status
    try:
        response = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE)
        db = response['DBInstances'][0]
        print(f"RDS Database ({RDS_INSTANCE}):")
        print(f"  Status: {db['DBInstanceStatus']}")
        print(f"  Endpoint: {db['Endpoint']['Address']}")
        print(f"  Type: {db['DBInstanceClass']}")
    except Exception as e:
        print(f"RDS Status: ❌ Error - {e}")
    
    # CloudFront Status
    try:
        response = cloudfront.get_distribution(Id=CLOUDFRONT_ID)
        config = response['Distribution']['DistributionConfig']
        status = "🟢 ENABLED" if config['Enabled'] else "🔴 DISABLED"
        print(f"\nCloudFront Distribution ({CLOUDFRONT_ID}):")
        print(f"  Status: {status}")
        print(f"  Domain: d19zwm3cutizk7.cloudfront.net")
    except Exception as e:
        print(f"CloudFront Status: ❌ Error - {e}")
    
    print()

def main():
    parser = argparse.ArgumentParser(
        description='Quick pause/resume for AWS resources',
        usage='%(prog)s [--pause|--resume|--status]'
    )
    parser.add_argument('--pause', action='store_true', help='Pause RDS database')
    parser.add_argument('--resume', action='store_true', help='Resume RDS database')
    parser.add_argument('--status', action='store_true', help='Check resource status')
    
    args = parser.parse_args()
    
    # Si no hay argumentos, mostrar ayuda
    if not args.pause and not args.resume and not args.status:
        parser.print_help()
        print("\nExamples:")
        print("  python quick_pause.py --pause    # Pause RDS")
        print("  python quick_pause.py --resume   # Resume RDS")
        print("  python quick_pause.py --status   # Check status")
        return 1
    
    if args.pause:
        return 0 if pause_all() else 1
    elif args.resume:
        return 0 if resume_all() else 1
    elif args.status:
        status()
        return 0

if __name__ == '__main__':
    sys.exit(main())
