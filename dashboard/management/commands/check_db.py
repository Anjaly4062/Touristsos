import os
import socket
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = 'Safely diagnoses database connection, network reachability, and SSL configuration.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Tourist SOS Database Connectivity Diagnostic ==="))

        db_conf = settings.DATABASES['default']
        host = db_conf.get('HOST', 'localhost')
        port = db_conf.get('PORT', '3306')
        name = db_conf.get('NAME', '')
        user = db_conf.get('USER', '')
        password = db_conf.get('PASSWORD', '')
        ssl_options = db_conf.get('OPTIONS', {}).get('ssl', {})
        ca_path = ssl_options.get('ca') if isinstance(ssl_options, dict) else None

        is_remote = bool(os.environ.get('DB_HOST'))
        self.stdout.write(f"Environment Mode: {'PRODUCTION / REMOTE (Aiven)' if is_remote else 'LOCAL DEVELOPMENT'}")

        # 1. Environment Variables Check
        self.stdout.write("\n[1/5] Checking Database Environment Variables...")
        env_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_SSL_CA']
        for var in env_vars:
            val = os.environ.get(var)
            if val is not None:
                if 'PASSWORD' in var:
                    status = f"SET (length: {len(val)} chars)"
                elif 'USER' in var or 'NAME' in var:
                    status = f"SET ({val})"
                elif 'HOST' in var:
                    # Show partial host for safety
                    masked = val[:8] + '...' + val[-12:] if len(val) > 20 else val
                    status = f"SET ({masked})"
                else:
                    status = f"SET ({val})"
                self.stdout.write(f"  - {var}: {self.style.SUCCESS(status)}")
            else:
                self.stdout.write(f"  - {var}: {self.style.WARNING('NOT SET (using default/fallback)')}")

        if is_remote and port == '3306':
            self.stdout.write(self.style.WARNING(
                "  [!] WARNING: DB_PORT is set to 3306. Aiven MySQL services use high ports (e.g. 10000-30000), not 3306. "
                "Verify DB_PORT in your Aiven Console!"
            ))

        # 2. SSL CA Certificate Check
        self.stdout.write("\n[2/5] Checking SSL CA Certificate...")
        if ca_path:
            ca_exists = os.path.exists(ca_path)
            if ca_exists:
                file_size = os.path.getsize(ca_path)
                self.stdout.write(self.style.SUCCESS(f"  - CA Certificate found at: {ca_path} (Size: {file_size} bytes)"))
            else:
                self.stdout.write(self.style.ERROR(f"  - CA Certificate NOT FOUND at: {ca_path}"))
                self.stdout.write(
                    "    Tip: On Render, add a Secret File named 'ca.pem' in Dashboard -> Secret Files. "
                    "It will mount at /etc/secrets/ca.pem."
                )
        else:
            self.stdout.write("  - SSL CA path is not configured (Local mode).")

        # 3. DNS Resolution
        self.stdout.write(f"\n[3/5] Testing DNS Resolution for '{host}'...")
        try:
            addr_info = socket.getaddrinfo(host, int(port) if str(port).isdigit() else 3306, socket.AF_INET, socket.SOCK_STREAM)
            resolved_ip = addr_info[0][4][0]
            self.stdout.write(self.style.SUCCESS(f"  - DNS resolution successful. IP: {resolved_ip}"))
        except socket.gaierror as e:
            self.stdout.write(self.style.ERROR(f"  - DNS resolution FAILED: {e}"))
            self.stdout.write("    Check your DB_HOST setting for typos or extra whitespace/schemes.")
            return

        # 4. TCP Network Reachability
        self.stdout.write(f"\n[4/5] Testing TCP Port Reachability to '{host}:{port}' (5s timeout)...")
        try:
            sock = socket.create_connection((host, int(port)), timeout=5)
            sock.close()
            self.stdout.write(self.style.SUCCESS(f"  - TCP connection to {host}:{port} SUCCEEDED!"))
        except socket.timeout:
            self.stdout.write(self.style.ERROR(f"  - TCP connection TIMED OUT after 5 seconds!"))
            self.stdout.write(self.style.WARNING(
                "    CAUSE: Packets to this host/port are being dropped. Most common causes:\n"
                "    1. Aiven IP Filter (Firewall): In Aiven Console -> Service Settings -> IP Filter, "
                "ensure 0.0.0.0/0 is allowed so Render can connect.\n"
                "    2. Incorrect Port: Ensure DB_PORT matches the Port shown in Aiven Console (not 3306).\n"
                "    3. Aiven Service Paused/Stopped: Check if the service status in Aiven is 'RUNNING'."
            ))
            return
        except ConnectionRefusedError:
            self.stdout.write(self.style.ERROR(f"  - TCP connection REFUSED on port {port}!"))
            self.stdout.write(
                "    CAUSE: The host is reachable, but no service is listening on this port. "
                "Check the Port number in Aiven Console."
            )
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - TCP connection FAILED: {e}"))
            return

        # 5. Django MySQL Connection & SSL Handshake
        self.stdout.write("\n[5/5] Testing Django Database Connection & SSL Handshake...")
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                db_version = cursor.fetchone()
                version_str = db_version[0] if db_version else "Unknown"

            self.stdout.write(self.style.SUCCESS(
                f"\n[SUCCESS] Django successfully connected to database '{name}' on MySQL {version_str}!"
            ))
        except OperationalError as e:
            err_code = e.args[0] if e.args else None
            err_msg = str(e)
            self.stdout.write(self.style.ERROR(f"\n[FAILED] Django Database Connection Error: {err_msg}"))

            if err_code == 2013:
                self.stdout.write(self.style.WARNING(
                    "\n--- Diagnosis for MySQL Error 2013 ((2013, \"Can't connect to server (11)\")) ---\n"
                    "The TCP connection was established, but the server/proxy immediately closed the link.\n"
                    "Primary Causes on Aiven MySQL:\n"
                    "1. Aiven IP Allowlist: An IP Filter is configured in Aiven that dropped the connection.\n"
                    "   Fix: Go to Aiven Console -> Service -> IP Filter, add 0.0.0.0/0.\n"
                    "2. SSL Certificate / Handshake: The CA certificate at /etc/secrets/ca.pem is missing or invalid.\n"
                    "   Fix: Download ca.pem from Aiven and upload it as a Render Secret File named 'ca.pem'.\n"
                    "3. Service State: The Aiven service is currently rebuilding or paused."
                ))
            elif err_code == 1045:
                self.stdout.write(self.style.WARNING(
                    "\n--- Diagnosis for MySQL Error 1045 (Access Denied) ---\n"
                    "Authentication failed. Check DB_USER and DB_PASSWORD environment variables."
                ))
            elif err_code == 1049:
                self.stdout.write(self.style.WARNING(
                    f"\n--- Diagnosis for MySQL Error 1049 (Unknown Database '{name}') ---\n"
                    "Database does not exist on the server. On Aiven, the default database is 'defaultdb'.\n"
                    "Either set DB_NAME=defaultdb in Render, or create this database in Aiven Console."
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[FAILED] Unexpected Connection Error: {e}"))
