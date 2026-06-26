import pandas as pd

df = pd.read_csv('./archivos_csv/taxes.csv')

print("=" * 80)
print("ANÁLISIS DE CÓDIGOS DE RETENCIÓN ISR:")
print("=" * 80)

# Filtrar solo retenciones ISR
isr = df[df['TIPO_IMPUESTO'] == 'RETENCION_ISR']

print(f"\n📋 Total retenciones ISR: {len(isr)}")

if len(isr) > 0:
    print("\n📊 Valores únicos en TAX_RATE_CODE para RETENCION_ISR:")
    print(isr['TAX_RATE_CODE'].value_counts().head(20))

    print("\n📋 Muestra de registros ISR:")
    print(isr[['INVOICE_ID', 'TAX_RATE_CODE', 'IMPUESTO_USD', 'IMPUESTO_MXN']].head(10))

    # Buscar específicamente cualquier código con '4'
    print("\n" + "=" * 80)
    print("BUSCANDO CÓDIGOS CON '4' EN TODO EL CSV:")
    print("=" * 80)
    con_4 = df[df['TAX_TYPE_CODE'].astype(str).str.contains('4', na=False)]
    print(f"Total registros con '4' en TAX_TYPE_CODE: {len(con_4)}")

    if len(con_4) > 0:
        print("\nMuestra:")
        print(con_4[['TAX_TYPE_CODE', 'TIPO_IMPUESTO', 'IMPUESTO_MXN']].head(10))