"""
Healthz endpoint for bot service

Run this alongside the bot to provide health checking capability
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import logging

logger = logging.getLogger(__name__)


class HealthzHandler(BaseHTTPRequestHandler):
    """HTTP handler for healthz endpoint"""

    def do_GET(self):
        if self.path == '/healthz':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {
                'status': 'healthy',
                'service': 'telegram-bot'
            }

            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Override to use logging instead of print"""
        logger.info(f"{self.address_string()} - {format % args}")


def start_healthz_server(port=8001):
    """Start healthz HTTP server in a separate thread"""
    server = HTTPServer(('0.0.0.0', port), HealthzHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Healthz server started on port {port}")
    return server
