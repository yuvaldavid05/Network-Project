import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

clients = {}   
pairs = {}    
lock = threading.Lock()


def send_line(sock: socket.socket, line: str):
    try:
        sock.sendall((line + "\n").encode("utf-8"))
    except Exception:
        pass


def end_chat_for(name: str, reason: str):
    """
    Ends chat pairing for 'name' (if exists) and notifies peer.
    reason: text shown to the peer (e.g. "peer disconnected" / "peer left")
    """
    peer_name = None
    peer_sock = None

    with lock:
        peer_name = pairs.get(name)
        if peer_name:
            
            pairs.pop(name, None)
            pairs.pop(peer_name, None)
            peer_sock = clients.get(peer_name)

    if peer_sock and peer_name:
        send_line(peer_sock, f"PEER_LEFT {name}")
        send_line(peer_sock, f"OK chat ended ({reason})")


def cleanup(name: str):
    if not name:
        return

    
    end_chat_for(name, "peer disconnected")

    
    with lock:
        clients.pop(name, None)


def start_chat(a: str, b: str):
    with lock:
        if a == b:
            return False, "ERR cannot chat with yourself"
        if b not in clients:
            return False, "USER_NOT_FOUND"
        if a in pairs and pairs[a] != b:
            return False, f"ERR_ALREADY_IN_CHAT_WITH {pairs[a]}"
        if b in pairs and pairs[b] != a:
            return False, f"ERR_USER_BUSY {b}"

        pairs[a] = b
        pairs[b] = a

        a_sock = clients.get(a)
        b_sock = clients.get(b)

    
    if a_sock:
        send_line(a_sock, f"CHAT_STARTED {b}")
    if b_sock:
        send_line(b_sock, f"CHAT_STARTED {a}")

    return True, "OK"


def relay(sender: str, text: str):
    with lock:
        peer = pairs.get(sender)
        peer_sock = clients.get(peer) if peer else None

    if not peer_sock:
        return False, "ERR you are not in a chat (use /chat <name> or target:message)"

    send_line(peer_sock, f"FROM {sender}: {text}")
    return True, "OK"


def handle_client(sock: socket.socket, addr):
    name = None
    f = None
    try:
        send_line(sock, "OK Welcome. Send your name:")

        f = sock.makefile("r", encoding="utf-8", newline="\n")
        name = f.readline().strip()
        if not name:
            send_line(sock, "ERR empty name")
            return

        with lock:
            if name in clients:
                send_line(sock, "NAME_TAKEN")
                return
            clients[name] = sock

        send_line(sock, "CONNECTED")
        send_line(sock, "OK Commands: /chat <name> | /leave | /bye | target:message | or plain message after /chat")
        print(f"[+] {name} connected from {addr}")

        while True:
            line = f.readline()
            if not line:
                
                break

            line = line.strip()
            if not line:
                continue

            low = line.lower()

            
            if low in ("/bye", "bye", "exit"):
                
                end_chat_for(name, "peer closed the window")
                send_line(sock, "OK bye")
                break

           
            if low == "/leave":
                end_chat_for(name, "peer left the chat")
                send_line(sock, "OK left chat")
                continue

            
            if low.startswith("/chat "):
                target = line[6:].strip()
                if not target:
                    send_line(sock, "ERR usage: /chat <name>")
                    continue
                ok, msg = start_chat(name, target)
                if not ok:
                    send_line(sock, msg)
                continue

           
            if ":" in line:
                target, msg = line.split(":", 1)
                target = target.strip()
                msg = msg.strip()

                ok, res = start_chat(name, target)
                if not ok and not res.startswith("OK"):
                    send_line(sock, res)
                    continue

                ok, res = relay(name, msg)
                send_line(sock, "OK sent" if ok else res)
                continue

            
            ok, res = relay(name, line)
            send_line(sock, "OK sent" if ok else res)

    except (ConnectionResetError, OSError):
        pass
    finally:
        try:
            if f:
                f.close()
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass

        cleanup(name)
        if name:
            print(f"[-] {name} disconnected")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    while True:
        client_sock, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()


if __name__ == "__main__":
    main()
