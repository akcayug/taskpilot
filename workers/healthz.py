"""
Healthz endpoint for Celery worker service.
Runs a simple HTTP server to respond to health checks.
"""
import http.server
import socketserver
import threading
from celery import current_app


class HealthzHandler(http.server.BaseHTTPRequestHandler):
    """Handler for health check requests."""

    def do_GET(self):
        """Handle GET request to /healthz."""
        if self.path == '/healthz':
            try:
                # Check Redis connectivity
                current_app.broker_connection().ensure_connection(max_retries=3)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "healthy", "service": "worker"}')
            except Exception as e:
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(f'{{"status": "unhealthy", "error": "{str(e)}"}}'.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def start_healthz_server(port=8002):
    """Start healthz HTTP server in a background thread."""
    handler = HealthzHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Worker healthz server running on port {port}")
        httpd.serve_forever()


def run_healthz_background(port=8002):
    """Run healthz server in background thread."""
    thread = threading.Thread(target=start_healthz_server, args=(port,), daemon=True)
    thread.start()
