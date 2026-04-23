#!/usr/bin/env python3
"""
Script para habilitar solo CloudFront con el ETag correcto
"""

import boto3

cloudfront = boto3.client('cloudfront', region_name='us-east-2')

CLOUDFRONT_ID = 'E2CF1UGAOEY54R'

print("🌐 Habilitando CloudFront Distribution...\n")

try:
    # Obtener distribución
    print("[1] Obteniendo configuración actual...")
    dist = cloudfront.get_distribution(Id=CLOUDFRONT_ID)
    config = dist['Distribution']['DistributionConfig']
    etag = dist['ETag']
    
    print(f"    ✓ ETag obtenido: {etag[:20]}...")
    print(f"    ✓ Estado actual: {'Habilitado' if config.get('Enabled') else 'Deshabilitado'}")
    
    # Cambiar Enabled a True
    if not config.get('Enabled'):
        config['Enabled'] = True
        print("\n[2] Habilitando distribución...")
        
        response = cloudfront.update_distribution(
            Id=CLOUDFRONT_ID,
            DistributionConfig=config,
            IfMatch=etag
        )
        
        print(f"    ✅ CloudFront habilitado")
        print(f"\n🌐 URL: https://d19zwm3cutizk7.cloudfront.net")
        print(f"⏳ Propagación global: 5-15 minutos\n")
        
    else:
        print(f"\n✓ CloudFront ya está habilitado\n")
        
    print("✅ Completado")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    exit(1)
