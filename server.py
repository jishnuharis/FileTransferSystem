import socket
import threading
import os

waiting_receiver = None
lock = threading.Lock()


def relay(sender, receiver):
    try:
        while True:
            data = sender.recv(4096)
            if not data:
                break
            receiver.sendall(data)
    except:
        pass
    finally:
        sender.close()
        receiver.close()


def handle_client(conn, addr):
    global waiting_receiver

    try:
        role = conn.recv(1024).decode().strip()

        if role == "RECEIVER":
            print(f"[+] Receiver connected: {addr}")

            with lock:
                if waiting_receiver is None:
                    waiting_receiver = conn
                    conn.send(b"WAITING")
                else:
                    conn.send(b"BUSY")
                    conn.close()

        elif role == "SENDER":
            print(f"[+] Sender connected: {addr}")

            with lock:
                if waiting_receiver is not None:
                    receiver = waiting_receiver
                    waiting_receiver = None

                    conn.send(b"START")

                    print("[*] Linking sender and receiver...")

                    threading.Thread(target=relay, args=(conn, receiver)).start()
                else:
                    conn.send(b"NO_RECEIVER")
                    conn.close()

        else:
            conn.close()

    except Exception as e:
        print("Error:", e)
        conn.close()


def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 9000))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()

    print(f"[🚀] Relay server running on port {port}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()


if __name__ == "__main__":
    main()
