from flask import Flask, Response, send_file, request, jsonify
from flask_cors import CORS
import requests
import re
import logging
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)

BASE_URLS = {
    'rtp1': "https://streaming-live.rtp.pt/liverepeater/smil:rtp1HD.smil/",
    'rtp2': "https://streaming-live.rtp.pt/liverepeater/smil:rtp2HD.smil/",
    'rtp3': "https://streaming-live.rtp.pt/liverepeater/smil:rtpnHD.smil/"
}

M3U_URL = "https://raw.githubusercontent.com/LITUATUI/M3UPT/main/M3U/M3UPT.m3u"

@app.route('/')
def index():
    app.logger.info("Acessando a página principal.")
    return send_file('naotensaceesoaquikikalabsarquivohtml.html')

@app.route('/<channel>/<path:path>')
def proxy(channel, path):
    if channel not in BASE_URLS:
        return Response("Canal não suportado", status=404)

    url = urljoin(BASE_URLS[channel], path)
    app.logger.info(f"Requisição recebida para: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': BASE_URLS[channel],
        'Origin': 'https://www.rtp.pt'
    }

    try:
        resp = requests.get(url, headers=headers, stream=True)
        resp.raise_for_status()

        app.logger.info(f"Resposta recebida do servidor RTP com status: {resp.status_code}")

        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                yield chunk

        content_type = resp.headers.get('Content-Type', 'application/octet-stream')
        
        if path.endswith('.m3u8'):
            content = resp.content.decode('utf-8')
            content = re.sub(r'^(https?://[^/]+)?(/.*)', f'http://localhost:5000/{channel}\2', content, flags=re.MULTILINE)
            app.logger.debug(f"Conteúdo modificado do .m3u8:\n{content}")
            return Response(content, content_type='application/vnd.apple.mpegurl')

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        return Response(generate(), content_type=content_type, headers=headers)

    except requests.RequestException as e:
        app.logger.error(f"Erro ao aceder ao stream: {str(e)}")
        return Response(f"Erro ao aceder ao stream: {str(e)}", status=500)

@app.route('/api/', methods=['POST'])
def get_channel_url():
    channel_id = request.json.get('channel')
    if not channel_id:
        return jsonify({"error": "Canal não especificado"}), 400

    try:
        m3u_content = requests.get(M3U_URL).text
        lines = m3u_content.split('\n')
        
        for i, line in enumerate(lines):
            if f'tvg-id="{channel_id}"' in line:
                for j in range(i+1, min(i+5, len(lines))):
                    if 'm3u8' in lines[j]:
                        url = re.search(r'(https?://\S+)', lines[j]).group(1)
                        return jsonify({"url": url})
        
        return jsonify({"error": "Canal não encontrado ou URL não disponível"}), 404
    
    except Exception as e:
        return jsonify({"error": f"Erro ao processar a solicitação: {str(e)}"}), 500

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Range'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
