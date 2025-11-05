import socket

class TcpPeer:
    def __init__(self, tcp_port: int = 5001) -> None:
        self.server = None
        self.setup_tcp_server(tcp_port)

        self.tcp_port = tcp_port

    def setup_tcp_server(self, tcp_port: int) -> socket.socket:
        # Create TCP server socket once; configure to avoid blocking UI loop
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow quick restart by reusing address
        try:
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        # Bind to all interfaces so peers can connect (adjust if you really want localhost only)
        self.server.bind(('0.0.0.0', tcp_port))
        # Start listening once (do not call listen() repeatedly inside the app loop)
        self.server.listen(5)
        # Non-blocking mode so accept() will not stall the main loop
        self.server.setblocking(False)

    def wait_for_connection(self):
        try:
            # Fast path: try non-blocking accept directly
            conn, addr = self.server.accept()
            conn.setblocking(False)
            # get message
            data = conn.recv(1024) if conn else b""
            print(f"[TcpPeer]Accepted connection from {addr}: {data.decode('utf-8', errors='ignore').strip()}")

            return conn, addr, data.decode("utf-8", errors="ignore").strip()
        except BlockingIOError:
            return None, None, None
        except Exception as e:
            print(f"[TcpPeer] wait_for_connection error: {e}")
            return None, None, None

    def send_message(self, ip: str, port: int, msg: str) -> bool:
        with socket.create_connection((ip, port), timeout=2.0) as s:
            s.sendall(msg.encode("utf-8"))
        print(f"[TcpPeer] Sent TCP message to {ip}:{port}: {msg}")

        
