from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper import scrape_site, auto_detect_common_fields, fetch_html
import threading
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# In-memory storage for jobs (in a real app, use a database)
jobs = {}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Scraper API is running"})

@app.route('/detect', methods=['POST'])
def detect_fields():
    data = request.json
    url = data.get('url')
    use_selenium = data.get('use_selenium', False)
    use_tor = data.get('use_tor', False)

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        html = fetch_html(url, use_selenium=use_selenium, use_tor=use_tor)
        detected = auto_detect_common_fields(html)
        return jsonify({"success": True, "detected": detected})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/scrape', methods=['POST'])
def start_scrape():
    data = request.json
    job_id = str(uuid.uuid4())
    
    # Extract parameters
    config = {
        'base_url': data.get('url'),
        'fields': data.get('fields'),
        'next_selector': data.get('next_selector'),
        'use_selenium': data.get('use_selenium', False),
        'scrape_all': data.get('scrape_all', False),
        'max_pages': int(data.get('max_pages', 1)),
        'auto_mode': data.get('auto_mode', False),
        'infinite_scroll': data.get('infinite_scroll', False),
        'load_more_selector': data.get('load_more_selector'),
        'use_tor': data.get('use_tor', False),
        'delay_range': tuple(data.get('delay_range', [1.0, 2.0])),
        'normalize_urls': data.get('normalize_urls', True),
        'request_timeout': int(data.get('timeout', 20)),
        'request_retries': int(data.get('retries', 2)),
    }

    # Initialize job status
    jobs[job_id] = {
        "status": "running",
        "progress": {"page": 0, "total": 0 if config['scrape_all'] else config['max_pages']},
        "results": [],
        "error": None
    }

    def run_scraper(jid, cfg):
        try:
            def progress_callback(page, total):
                if jid in jobs:
                    jobs[jid]["progress"] = {"page": page, "total": total}

            results = scrape_site(
                base_url=cfg['base_url'],
                fields=cfg['fields'],
                next_selector=cfg['next_selector'],
                use_selenium=cfg['use_selenium'],
                scrape_all=cfg['scrape_all'],
                max_pages=cfg['max_pages'],
                auto_mode=cfg['auto_mode'],
                infinite_scroll=cfg['infinite_scroll'],
                load_more_selector=cfg['load_more_selector'],
                use_tor=cfg['use_tor'],
                delay_range=cfg['delay_range'],
                progress_callback=progress_callback,
                normalize_urls=cfg['normalize_urls'],
                request_timeout=cfg['request_timeout'],
                request_retries=cfg['request_retries']
            )
            jobs[jid]["results"] = results
            jobs[jid]["status"] = "completed"
        except Exception as e:
            jobs[jid]["error"] = str(e)
            jobs[jid]["status"] = "failed"

    # Run in background thread
    thread = threading.Thread(target=run_scraper, args=(job_id, config))
    thread.start()

    return jsonify({"job_id": job_id})

@app.route('/status/<job_id>', methods=['GET'])
def check_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route('/download/<job_id>/<format>', methods=['GET'])
def download_results(job_id, format):
    # In a real API, we would generate the file and serve it.
    # For now, the extension will handle the JSON response from /status and convert it to CSV/Excel if needed,
    # or we can return the raw data here.
    job = jobs.get(job_id)
    if not job or job['status'] != 'completed':
        return jsonify({"error": "Job not ready"}), 400
    
    return jsonify(job['results'])

if __name__ == '__main__':
    print("Starting Scraper API on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
