import socket
import select
import time
from app.naval_battle.player_model import Player
# 192.168.15.255

class UdpPeer:
    def __init__(self, udp_port: int = 5000, broadcast_addr: str = "255.255.255.255", tcp_peer=None) -> None:
        self.server = None
        self.udp_port = udp_port
        self.broadcast_addr = broadcast_addr
        # Track known participants (PlayerModel instances)
        self.participants = []
        # Optional TcpPeer instance for TCP communications (client/server)
        self.tcp_peer = tcp_peer
        # Detect local IP to ignore our own broadcast loopback
        self.local_ip = self._detect_local_ip()
        # Start UDP server after required attributes are initialized
        self.setup_udp_server(udp_port)

    def setup_udp_server(self, udp_port: int) -> socket.socket:
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.server.bind(('0.0.0.0', udp_port))

        # Add ourselves as an active participant
        self.participants.append(Player(self.local_ip, True))

    def wait_for_message(self):
        # read / write / error lists
        rlist, _, _ = select.select([self.server], [], [], 0.0)
        if not rlist:
            return None, None

        data, addr = self.server.recvfrom(1024)
        msg = data.decode("utf-8", errors="ignore").strip()
        ip = addr[0]
        # Ignore our own messages (e.g., broadcast loopback)
        if ip == getattr(self, "local_ip", None):
            return None, None
        print(f"Received message from {addr}: {msg}")

        # On discovery broadcast "Conectando": add sender as participant and reply via TCP:5001 with list
        if msg == "Conectando":
            # reactivate if already known, otherwise add
            found = False
            for p in self.participants:
                if p.ip == ip:
                    p.active = True
                    found = True
                    break
            if not found:
                self.participants.append(Player(ip, True))
            try:
                participant_ips = sorted({p.ip for p in self.participants})
                payload = "participantes: [" + ", ".join(f"'{ip}'" for ip in participant_ips) + "]"
                # Reply via UDP unicast to the requester with the participants list
                self.server.sendto(payload.encode("utf-8"), (ip, self.udp_port))
            except Exception as e:
                print(f"[UdpPeer] UDP send participants error: {e}")

        elif msg == "Saindo":
            for participant in self.participants:
                if participant.ip == ip:
                    participant.active = False
                    break

        elif ip not in [p.ip for p in self.participants]:
            self.participants.append(Player(ip, True))

        return addr, msg

    def _detect_local_ip(self) -> str:
        temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # This does not send traffic; it asks OS for the route/interface
            temp.connect(("8.8.8.8", 80))
            return temp.getsockname()[0]
       
        finally:
            temp.close()

    def send_broadcast_connecting(self) -> None:
        print("[UdpPeer] Sending broadcast 'Conectando'")
        msg = 'Conectando'
        self.server.sendto(msg.encode("utf-8"), (self.broadcast_addr, self.udp_port))

    def send_broadcast_leaving(self) -> None:
        print("[UdpPeer] Sending broadcast 'Saindo'")
        msg = 'Saindo'
        self.server.sendto(msg.encode("utf-8"), (self.broadcast_addr, self.udp_port))

    def send_shot_unicast(self, message: str) -> None:
        print(self.participants)
        for participant in self.participants:
            if participant.active:
                ip = participant.ip
                if ip != self.local_ip:
                    print("[UdpPeer] Sending unicast shot message to", ip)
                    self.server.sendto(message.encode("utf-8"), (ip, self.udp_port))

    def send_lost_unicast(self, message: str) -> None:
        for participant in self.participants:
            if participant.active:
                ip = participant.ip
                if ip != self.local_ip:
                    print("[UdpPeer] Sending unicast lost message to", ip)
                    self.server.sendto(message.encode("utf-8"), (ip, self.udp_port))

    def receive_participant_list(self, msg: str) -> None:
        """
        Processa uma mensagem UDP com a lista de participantes no formato:
        "participantes: ['ip1', 'ip2', ...]".
        Atualiza self.participants adicionando IPs novos e reativando existentes.
        """
        try:
            payload = msg.split(":", 1)[1]
            start = payload.find("[")
            end = payload.find("]")
            if start != -1 and end != -1 and end > start:
                inner = payload[start + 1:end]
                ips = []
                for part in inner.split(","):
                    ip = part.strip().strip("'").strip('"')
                    if ip:
                        ips.append(ip)
                known = {p.ip for p in self.participants}
                for ip in ips:
                    if ip == self.local_ip:
                        continue
                    if ip in known:
                        for p in self.participants:
                            if p.ip == ip:
                                p.active = True
                                break
                    else:
                        self.participants.append(Player(ip, True))
        except Exception as e:
            print(f"[UdpPeer] receive_participant_list parse error: {e}")

    def get_participants(self) -> list:
        return self.participants
    
    def get_local_ip(self) -> str:
        return self.local_ip
