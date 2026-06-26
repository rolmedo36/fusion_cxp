import pandas as pd
import os

carpeta = "archivos_csv"
archivos = [
    "core_invoices_rep.csv",
    "distributions_rep.csv",
    "payments_applied_rep.csv",
    "payments_ers_rep.csv",
    "taxes_rep.csv"
]

for arch in archivos:
    ruta = os.path.join(carpeta, arch)
    if os.path.exists(ruta):
        print(f"\n{'='*60}")
        print(f"📄 ARCHIVO: {arch}")
        print(f"{'='*60}")
        try:
            # Intentar leer con header automático
            df = pd.read_csv(ruta, nrows=3, low_memory=False)
            print(f"✅ Columnas detectadas ({len(df.columns)}):")
            for i, col in enumerate(df.columns):
                print(f"   [{i}] {col}")
            print(f"\n📊 Primera fila de muestra:")
            print(df.iloc[0].to_dict())
        except Exception as e:
            print(f"❌ Error: {e}")
            # Intentar sin header
            try:
                df = pd.read_csv(ruta, nrows=3, header=None, low_memory=False)
                print(f"⚠️ Sin headers. Primeras columnas:")
                print(df.iloc[0].tolist()[:10])
            except Exception as e2:
                print(f"❌ Error secundario: {e2}")
    else:
        print(f"\n⚠️ No encontrado: {ruta}")