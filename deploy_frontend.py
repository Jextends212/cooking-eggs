#!/usr/bin/env python3
"""
Deploy Frontend a S3 + CloudFront
Automatiza la creación de bucket, subida de archivos y distribución CloudFront
"""

import os
import sys
import json
import boto3
import uuid
from pathlib import Path
from datetime import datetime

# Configuración
FRONTEND_DIR = Path(__file__).parent / "Frontend"
REGION = "us-east-2"  # Misma región que el backend
ENVIRONMENT = "prod"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# AWS Clients
s3_client = boto3.client('s3', region_name=REGION)
cloudfront_client = boto3.client('cloudfront', region_name=REGION)
sts_client = boto3.client('sts')

def print_header(msg):
    print(f"\n{'=' * 70}")
    print(f"  {msg}")
    print(f"{'=' * 70}\n")

def print_step(step_num, msg):
    print(f"[{step_num}] {msg}")

def get_account_id():
    """Obtener ID de la cuenta AWS"""
    return sts_client.get_caller_identity()['Account']

def create_bucket_name():
    """Crear nombre único para el bucket"""
    account_id = get_account_id()
    suffix = str(uuid.uuid4())[:8]
    bucket_name = f"coking-eggs-front-{account_id}-{suffix}".lower()
    return bucket_name

def create_s3_bucket(bucket_name):
    """Crear bucket S3"""
    print_step(1, f"Creating S3 bucket: {bucket_name}")
    try:
        response = s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': REGION}
        )
        print(f"   ✅ Bucket created successfully")
        return bucket_name
    except s3_client.exceptions.BucketAlreadyExists:
        print(f"   ⚠️  Bucket already exists, using it...")
        return bucket_name
    except Exception as e:
        print(f"   ❌ Error creating bucket: {e}")
        raise

def enable_website_hosting(bucket_name):
    """Habilitar hosting estático en S3 (privado, accesible solo vía CloudFront)"""
    print_step(2, "Configuring S3 bucket (private, CloudFront only)")
    try:
        # Bloquear acceso público (mejor práctica de seguridad)
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        print(f"   ✓ Block Public Access enabled (secure)")
        
        # Configurar versionado (opcional pero recomendado)
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print(f"   ✓ Versioning enabled")
        
        print(f"   ✅ S3 bucket configured (CloudFront will handle access)")
        
    except Exception as e:
        print(f"   ❌ Error configuring bucket: {e}")
        raise

def upload_files(bucket_name):
    """Subir archivos del Frontend al S3"""
    print_step(3, "Uploading frontend files to S3")
    
    if not FRONTEND_DIR.exists():
        print(f"   ❌ Frontend directory not found: {FRONTEND_DIR}")
        raise FileNotFoundError(f"Frontend directory not found")
    
    files_uploaded = 0
    total_size = 0
    
    for root, dirs, files in os.walk(FRONTEND_DIR):
        for file in files:
            file_path = Path(root) / file
            # Calcular la ruta relativa para S3
            relative_path = file_path.relative_to(FRONTEND_DIR)
            s3_key = str(relative_path).replace('\\', '/')
            
            # Determinar Content-Type
            content_type = get_content_type(file_path)
            
            try:
                file_size = file_path.stat().st_size
                total_size += file_size
                
                s3_client.upload_file(
                    str(file_path),
                    bucket_name,
                    s3_key,
                    ExtraArgs={'ContentType': content_type, 'CacheControl': 'max-age=3600'}
                )
                print(f"   ✓ {s3_key} ({file_size} bytes)")
                files_uploaded += 1
            except Exception as e:
                print(f"   ❌ Error uploading {s3_key}: {e}")
                raise
    
    print(f"\n   ✅ Uploaded {files_uploaded} files ({total_size / 1024:.2f} KB)")

def get_content_type(file_path):
    """Determinar Content-Type basado en extensión"""
    ext_map = {
        '.html': 'text/html; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.eot': 'application/vnd.ms-fontobject',
    }
    
    ext = file_path.suffix.lower()
    return ext_map.get(ext, 'application/octet-stream')

def create_cloudfront_distribution(bucket_name):
    """Crear distribución CloudFront con OAI"""
    print_step(4, "Creating CloudFront distribution with Origin Access Identity")
    
    s3_domain = f"{bucket_name}.s3.{REGION}.amazonaws.com"
    
    try:
        # Crear OAI (Origin Access Identity) para acceso seguro
        oai_response = cloudfront_client.create_cloud_front_origin_access_identity(
            CloudFrontOriginAccessIdentityConfig={
                'CallerReference': str(uuid.uuid4()),
                'Comment': f'OAI for {bucket_name}'
            }
        )
        oai_id = oai_response['CloudFrontOriginAccessIdentity']['Id']
        canonical_user_id = oai_response['CloudFrontOriginAccessIdentity']['S3CanonicalUserId']
        print(f"   ✓ Origin Access Identity created: {oai_id}")
        
        # Actualizar política del bucket para permitir acceso desde OAI
        # NOTA: Usar S3CanonicalUserId, no ARN, para OAI
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CloudFrontOAIAccess",
                    "Effect": "Allow",
                    "Principal": {
                        "CanonicalUser": canonical_user_id
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print(f"   ✓ Bucket policy updated for OAI access")
        
        # Crear distribución
        distribution_config = {
            'CallerReference': str(uuid.uuid4()),
            'Comment': f'Frontend distribution for Coking Eggs ({TIMESTAMP})',
            'Enabled': True,
            'Origins': {
                'Quantity': 1,
                'Items': [
                    {
                        'Id': 'S3Origin',
                        'DomainName': s3_domain,
                        'S3OriginConfig': {
                            'OriginAccessIdentity': f'origin-access-identity/cloudfront/{oai_id}'
                        }
                    }
                ]
            },
            'DefaultRootObject': 'index.html',
            'DefaultCacheBehavior': {
                'TargetOriginId': 'S3Origin',
                'ViewerProtocolPolicy': 'redirect-to-https',
                'AllowedMethods': {
                    'Quantity': 2,
                    'Items': ['GET', 'HEAD']
                },
                'Compress': True,
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'},
                    'Headers': {
                        'Quantity': 0
                    }
                },
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                },
                'MinTTL': 0,
                'DefaultTTL': 3600,
                'MaxTTL': 86400
            },
            'CacheBehaviors': {
                'Quantity': 2,
                'Items': [
                    {
                        'PathPattern': '*.html',
                        'TargetOriginId': 'S3Origin',
                        'ViewerProtocolPolicy': 'redirect-to-https',
                        'AllowedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD']
                        },
                        'Compress': True,
                        'ForwardedValues': {
                            'QueryString': False,
                            'Cookies': {'Forward': 'none'}
                        },
                        'TrustedSigners': {
                            'Enabled': False,
                            'Quantity': 0
                        },
                        'MinTTL': 0,
                        'DefaultTTL': 300,
                        'MaxTTL': 3600
                    },
                    {
                        'PathPattern': '*.js',
                        'TargetOriginId': 'S3Origin',
                        'ViewerProtocolPolicy': 'redirect-to-https',
                        'AllowedMethods': {
                            'Quantity': 2,
                            'Items': ['GET', 'HEAD']
                        },
                        'Compress': True,
                        'ForwardedValues': {
                            'QueryString': False,
                            'Cookies': {'Forward': 'none'}
                        },
                        'TrustedSigners': {
                            'Enabled': False,
                            'Quantity': 0
                        },
                        'MinTTL': 0,
                        'DefaultTTL': 3600,
                        'MaxTTL': 86400
                    }
                ]
            }
        }
        
        response = cloudfront_client.create_distribution(
            DistributionConfig=distribution_config
        )
        
        distribution_id = response['Distribution']['Id']
        cloudfront_domain = response['Distribution']['DomainName']
        
        print(f"   ✅ CloudFront distribution created successfully")
        print(f"   📦 Distribution ID: {distribution_id}")
        print(f"   🌐 Domain: {cloudfront_domain}")
        
        return distribution_id, cloudfront_domain
        
    except Exception as e:
        print(f"   ❌ Error creating CloudFront distribution: {e}")
        raise

def save_deployment_info(bucket_name, distribution_id, cloudfront_domain):
    """Guardar información de deployment"""
    print_step(5, "Saving deployment information")
    
    deployment_info = {
        'timestamp': TIMESTAMP,
        'environment': ENVIRONMENT,
        'region': REGION,
        'bucket_name': bucket_name,
        'cloudfront_distribution_id': distribution_id,
        'cloudfront_domain': cloudfront_domain,
        'frontend_url': f'https://{cloudfront_domain}',
        'status': 'deploying',  # CloudFront toma 5-15 min para propagar
    }
    
    output_file = Path(__file__).parent / 'deployment_info_frontend.json'
    with open(output_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"   ✅ Deployment info saved to: {output_file}")
    return deployment_info

def print_summary(deployment_info):
    """Mostrar resumen del deployment"""
    print_header("🎉 DEPLOYMENT SUCCESSFUL")
    
    print("📋 Deployment Information:")
    print(f"   Environment: {deployment_info['environment']}")
    print(f"   Region: {deployment_info['region']}")
    print(f"   Timestamp: {deployment_info['timestamp']}")
    
    print("\n💾 AWS Resources:")
    print(f"   S3 Bucket (Private): {deployment_info['bucket_name']}")
    print(f"   CloudFront Distribution: {deployment_info['cloudfront_distribution_id']}")
    
    print("\n🌐 ACCESS YOUR APP:")
    print(f"   🚀 {deployment_info['cloudfront_domain']}")
    print(f"   🔗 https://{deployment_info['cloudfront_domain']}")
    
    print("\n⏱️  CloudFront Propagation Status:")
    print("   ⏳ Deploying... (takes 5-15 minutes globally)")
    print("   ✅ Check CloudFront distribution in AWS Console to monitor progress")
    
    print("\n📝 Configuration File:")
    print(f"   {Path(__file__).parent / 'deployment_info_frontend.json'}\n")
    
    print("🔒 Security:")
    print("   ✓ S3 bucket is PRIVATE (only CloudFront can access)")
    print("   ✓ Uses Origin Access Identity (OAI) for secure access")
    print("   ✓ HTTPS enforced\n")

def main():
    print_header("🚀 COKING EGGS - FRONTEND DEPLOYMENT")
    
    try:
        # 1. Crear bucket
        bucket_name = create_bucket_name()
        create_s3_bucket(bucket_name)
        
        # 2. Habilitar website hosting
        enable_website_hosting(bucket_name)
        
        # 3. Subir archivos
        upload_files(bucket_name)
        
        # 4. Crear CloudFront
        distribution_id, cloudfront_domain = create_cloudfront_distribution(bucket_name)
        
        # 5. Guardar información
        deployment_info = save_deployment_info(bucket_name, distribution_id, cloudfront_domain)
        
        # 6. Mostrar resumen
        print_summary(deployment_info)
        
        return 0
        
    except Exception as e:
        print_header("❌ DEPLOYMENT FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
