"""
Simple HTTPS proxy for Stagforge.

Provides SSL termination and forwards requests to the HTTP backend.
Required for browser features that need secure contexts (camera, geolocation, etc.).

Usage:
    # Start proxy programmatically
    from stagforge.https_proxy import start_https_proxy
    proxy = start_https_proxy(https_port=8443, http_port=8080)

    # Or run as standalone script
    python -m stagforge.https_proxy --https-port 8443 --http-port 8080
"""

import asyncio
import ipaddress
import signal
import ssl
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from typing import Optional

from stagforge.config import settings


def get_certs_dir() -> Path:
    """Get the certificates directory, creating if needed."""
    certs_dir = settings.CERTS_DIR
    certs_dir.mkdir(parents=True, exist_ok=True)
    return certs_dir


def get_cert_paths() -> tuple[Path, Path]:
    """Get paths to certificate and key files."""
    certs_dir = get_certs_dir()
    return certs_dir / "localhost.crt", certs_dir / "localhost.key"


def generate_self_signed_cert(cert_path: Path, key_path: Path) -> bool:
    """
    Generate a self-signed certificate for localhost.

    Uses OpenSSL if available, falls back to Python cryptography library.

    Returns:
        True if certificate was generated successfully
    """
    # Try OpenSSL first (most reliable)
    try:
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:4096",
                "-keyout", str(key_path),
                "-out", str(cert_path),
                "-days", "365",
                "-nodes",  # No passphrase
                "-subj", "/CN=localhost/O=Stagforge Development",
                "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
            ],
            check=True,
            capture_output=True,
        )
        print(f"[HTTPS Proxy] Generated self-signed certificate at {cert_path}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback to Python cryptography library
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID

        # Generate key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Stagforge Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256(), default_backend())
        )

        # Write key
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write certificate
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[HTTPS Proxy] Generated self-signed certificate at {cert_path}")
        return True

    except ImportError:
        print("[HTTPS Proxy] ERROR: Neither openssl nor cryptography library available")
        print("[HTTPS Proxy] Install cryptography: pip install cryptography")
        print("[HTTPS Proxy] Or install openssl and ensure it's in PATH")
        return False


def ensure_certificates() -> tuple[Path, Path] | None:
    """
    Ensure SSL certificates exist, generating if needed.

    Returns:
        Tuple of (cert_path, key_path) or None if failed
    """
    cert_path, key_path = get_cert_paths()

    if cert_path.exists() and key_path.exists():
        print(f"[HTTPS Proxy] Using existing certificates from {cert_path.parent}")
        return cert_path, key_path

    print("[HTTPS Proxy] Generating self-signed certificates...")
    if generate_self_signed_cert(cert_path, key_path):
        return cert_path, key_path

    return None


class HTTPSProxy:
    """
    Simple HTTPS to HTTP proxy using asyncio.

    Terminates SSL and forwards raw TCP to the HTTP backend.
    """

    def __init__(
        self,
        https_port: int = 8443,
        http_port: int = 8080,
        host: str = "0.0.0.0",
    ):
        self.https_port = https_port
        self.http_port = http_port
        self.host = host
        self.server: Optional[asyncio.Server] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def _pipe(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        label: str = "",
    ):
        """Pipe data from reader to writer."""
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
    ):
        """Handle an incoming HTTPS connection."""
        backend_reader = None
        backend_writer = None

        try:
            # Connect to HTTP backend
            backend_reader, backend_writer = await asyncio.open_connection(
                "127.0.0.1", self.http_port
            )

            # Pipe data bidirectionally
            await asyncio.gather(
                self._pipe(client_reader, backend_writer, "client->backend"),
                self._pipe(backend_reader, client_writer, "backend->client"),
            )

        except ConnectionRefusedError:
            # Backend not running
            error_response = (
                b"HTTP/1.1 502 Bad Gateway\r\n"
                b"Content-Type: text/plain\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                b"Backend server not available. Start Stagforge on port "
                + str(self.http_port).encode()
                + b" first."
            )
            try:
                client_writer.write(error_response)
                await client_writer.drain()
            except Exception:
                pass

        except Exception as e:
            print(f"[HTTPS Proxy] Connection error: {e}")

        finally:
            # Clean up
            for writer in [client_writer, backend_writer]:
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except Exception:
                        pass

    async def start(self) -> bool:
        """
        Start the HTTPS proxy server.

        Returns:
            True if started successfully
        """
        # Ensure certificates exist
        certs = ensure_certificates()
        if not certs:
            print("[HTTPS Proxy] Failed to get certificates")
            return False

        cert_path, key_path = certs

        # Create SSL context
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            ssl_context.load_cert_chain(str(cert_path), str(key_path))
        except ssl.SSLError as e:
            print(f"[HTTPS Proxy] Failed to load certificates: {e}")
            return False

        # Start server
        try:
            self.server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.https_port,
                ssl=ssl_context,
            )
            self._running = True
            self._loop = asyncio.get_event_loop()

            addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
            print(f"[HTTPS Proxy] Listening on {addrs}")
            print(f"[HTTPS Proxy] Forwarding HTTPS:{self.https_port} -> HTTP:{self.http_port}")
            print(f"[HTTPS Proxy] Access at: https://localhost:{self.https_port}")

            return True

        except OSError as e:
            print(f"[HTTPS Proxy] Failed to start server: {e}")
            if "Address already in use" in str(e):
                print(f"[HTTPS Proxy] Port {self.https_port} is already in use")
            return False

    async def serve_forever(self):
        """Serve until stopped."""
        if self.server:
            async with self.server:
                await self.server.serve_forever()

    def stop(self):
        """Stop the proxy server."""
        self._running = False
        if self.server:
            self.server.close()
            print("[HTTPS Proxy] Stopped")

    @property
    def is_running(self) -> bool:
        """Check if proxy is running."""
        return self._running and self.server is not None


def _run_proxy_thread(proxy: HTTPSProxy):
    """Run proxy in a dedicated thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def run():
        if await proxy.start():
            await proxy.serve_forever()

    try:
        loop.run_until_complete(run())
    except Exception as e:
        print(f"[HTTPS Proxy] Thread error: {e}")
    finally:
        loop.close()


def start_https_proxy(
    https_port: int | None = None,
    http_port: int | None = None,
    host: str | None = None,
    background: bool = True,
) -> HTTPSProxy:
    """
    Start the HTTPS proxy.

    Args:
        https_port: HTTPS port (default from settings)
        http_port: HTTP backend port (default from settings)
        host: Host to bind to (default from settings)
        background: Run in background thread (default True)

    Returns:
        HTTPSProxy instance
    """
    proxy = HTTPSProxy(
        https_port=https_port or settings.HTTPS_PORT,
        http_port=http_port or settings.PORT,
        host=host or settings.HOST,
    )

    if background:
        thread = Thread(target=_run_proxy_thread, args=(proxy,), daemon=True)
        thread.start()
        # Give it a moment to start
        import time
        time.sleep(0.5)
    else:
        # Run in current thread (blocking)
        asyncio.run(_run_proxy_sync(proxy))

    return proxy


async def _run_proxy_sync(proxy: HTTPSProxy):
    """Run proxy synchronously (for non-background mode)."""
    if await proxy.start():
        await proxy.serve_forever()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HTTPS proxy for Stagforge development"
    )
    parser.add_argument(
        "--https-port", "-s",
        type=int,
        default=settings.HTTPS_PORT,
        help=f"HTTPS port to listen on (default: {settings.HTTPS_PORT})"
    )
    parser.add_argument(
        "--http-port", "-p",
        type=int,
        default=settings.PORT,
        help=f"HTTP backend port to forward to (default: {settings.PORT})"
    )
    parser.add_argument(
        "--host", "-H",
        default=settings.HOST,
        help=f"Host to bind to (default: {settings.HOST})"
    )
    parser.add_argument(
        "--generate-cert", "-g",
        action="store_true",
        help="Only generate certificates and exit"
    )

    args = parser.parse_args()

    if args.generate_cert:
        ensure_certificates()
        return

    proxy = HTTPSProxy(
        https_port=args.https_port,
        http_port=args.http_port,
        host=args.host,
    )

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n[HTTPS Proxy] Shutting down...")
        proxy.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"[HTTPS Proxy] Starting proxy: https://localhost:{args.https_port} -> http://localhost:{args.http_port}")

    asyncio.run(_run_proxy_sync(proxy))


if __name__ == "__main__":
    main()
