from flask import Flask, Response, send_file
import requests
import re
import logging

app = Flask(__name__)

# Configuração de logs
logging.basicConfig(level=logging.DEBUG)

# URL base do stream da RTP2
BASE_URL = "https://streaming-live.rtp.pt/liverepeater/smil:rtp2HD.smil/"

@app.route('/')
def index():
    app.logger.info("Acessando a página principal.")
    return send_file('player.html')

@app.route('/<path:path>')
def proxy(path):
    url = BASE_URL + path
    app.logger.info(f"Requisição recebida para: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Faz a requisição ao servidor RTP com User-Agent
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()  # Levanta um erro se a resposta não for 200

        app.logger.info(f"Resposta recebida do servidor RTP com status: {resp.status_code}")

        content = resp.content
        
        # Se for um arquivo .m3u8, modificar as URLs dos chunks
        if path.endswith('.m3u8'):
            content = content.decode('utf-8')
            # Modificar as URLs relativas para usar o nosso proxy
            content = re.sub(r'^(https?://[^/]+)?(/.*)', r'http://localhost:5000\2', content)
            app.logger.debug(f"Conteúdo modificado do .m3u8:\n{content}")
            content = content.encode('utf-8')

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(content, resp.status_code, headers)

    except requests.RequestException as e:
        app.logger.error(f"Erro ao aceder ao stream: {str(e)}")
        return Response(f"Erro ao aceder ao stream: {str(e)}", status=500)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
