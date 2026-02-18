import requests
import base64
import re
import os
import pandas as pd  # Opcional, para leer el resultado fácilmente
import io


def ejecuta_rep(v_reporte, v_nom_reporte):
    # Endpoint de PublicReportService (más compatible para formatos directos)
    url = "https://ekck.fa.us6.oraclecloud.com/xmlpserver/services/PublicReportService"
    user = "rolmedo"
    pas = "Mexico.2022"

    if not os.path.exists("archivos_csv"):
        os.makedirs("archivos_csv")

    # Cambiamos la extensión a .csv
    v_nom_reporte = v_nom_reporte.replace(".xml", ".csv")
    nom_reporte = os.path.join("archivos_csv", v_nom_reporte)

    userpass = f"{user}:{pas}"
    basicAuth = "Basic " + base64.b64encode(userpass.encode("ascii")).decode("ascii")

    headers = {
        'Content-Type': 'text/xml; charset=UTF-8',
        'Authorization': basicAuth
    }

    # CAMBIO IMPORTANTE: attributeFormat ahora es 'csv'
    soap_request = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:pub="http://xmlns.oracle.com/oxp/service/PublicReportService">
    <soapenv:Header/>
    <soapenv:Body>
        <pub:runReport>
            <pub:reportRequest>
                <pub:attributeFormat>csv</pub:attributeFormat>
                <pub:parameterNameValues/>
                <pub:reportAbsolutePath>{v_reporte}</pub:reportAbsolutePath>
                <pub:sizeOfDataChunkDownload>-1</pub:sizeOfDataChunkDownload>
            </pub:reportRequest>
            <pub:userID>{user}</pub:userID>
            <pub:password>{pas}</pub:password>
        </pub:runReport>
    </soapenv:Body>
</soapenv:Envelope>"""

    try:
        print(f"Solicitando CSV para: {v_reporte}")
        response = requests.post(url, data=soap_request, headers=headers, timeout=120)

        if response.status_code != 200:
            print(f"❌ Error {response.status_code}")
            fault_match = re.search(r"<faultstring>(.*?)</faultstring>", response.text)
            if fault_match:
                print(f"Detalle Oracle: {fault_match.group(1)}")
            return

        if 'reportBytes' in response.text:
            start = response.text.find('<reportBytes>') + len('<reportBytes>')
            end = response.text.find('</reportBytes>')
            b64_str = response.text[start:end].strip()

            # Decodificar el contenido CSV
            csv_content = base64.b64decode(b64_str)

            with open(nom_reporte, "wb") as f:
                f.write(csv_content)

            print(f"✅ ¡Éxito! CSV guardado en: {nom_reporte}")

        else:
            print("⚠️ El servidor no devolvió datos en la etiqueta reportBytes.")

    except Exception as e:
        print(f"❌ Error crítico: {e}")


if __name__ == "__main__":
    try:
        with open("parametros.txt", "r") as f:
            for line in f:
                ruta_rep = line.strip()
                if ruta_rep:
                    # Limpiamos la ruta por si viene con comas
                    ruta_rep = ruta_rep.split(",")[-1].strip()
                    nombre_base = ruta_rep.split("/")[-1].replace(".xdo", "")
                    ejecuta_rep(ruta_rep, nombre_base + ".csv")
    except Exception as e:
        print(f"Error al leer parámetros: {e}")