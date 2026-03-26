import socket
import threading
import os

waiting_receiver = None
lock = threading.Lock()


def relay(src, dst):
    """
    Relay raw bytes from src to dst until src closes or an error occurs.
    """
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break  # connection closed by src
            dst.sendall(data)
    except Exception as e:
        # Optional: log if needed
        # print(f"Relay error: {e}")
        pass


def link_peers(conn1, conn2):
    """
    Start bidirectional relaying between two connected sockets.
    """
    # One thread: conn1 -> conn2
    t1 = threading.Thread(target=relay, args=(conn1, conn2), daemon=True)
    # Other thread: conn2 -> conn1
    t2 = threading.Thread(target=relay, args=(conn2, conn1), daemon=True)

    t1.start()
    t2.start()

    # Wait for any one direction to finish
    t1.join()
    t2.join()

    # Close both sockets when done
    try:
        conn1.close()
    except OSError:
        pass
    try:
        conn2.close()
    except OSError:
        pass


def handle_client(conn, addr):
    global waiting_receiver

    try:
        role = conn.recv(1024).decode(errors="ignore").strip()
        if not role:
            conn.close()
            return

        if role == "RECEIVER":
            print(f"[+] Receiver connected: {addr}")
            with lock:
                # If there is already a waiting receiver, reject this one
                if waiting_receiver is None:
                    waiting_receiver = conn
                    # Let the receiver know it is waiting for a sender
                    conn.sendall(b"WAITING\n")
                else:
                    conn.sendall(b"BUSY\n")
                    conn.close()

        elif role == "SENDER":
            print(f"[+] Sender connected: {addr}")
            with lock:
                if waiting_receiver is not None:
                    receiver = waiting_receiver
                    waiting_receiver = None  # consume the receiver

                    # Inform both ends that relay is starting
                    try:
                        conn.sendall(b"START\n")
                        receiver.sendall(b"START\n")
                    except OSError:
                        conn.close()
                        receiver.close()
                        return

                    print("[*] Linking sender and receiver...")
                    link_peers(conn, receiver)
                else:
                    conn.sendall(b"NO_RECEIVER\n")
                    conn.close()

        else:
            # Unknown role
            conn.close()

    except Exception as e:
        print("Error in handle_client:", e)
        try:
            conn.close()
        except OSError:
            pass
        # Ensure waiting_receiver is not left pointing to a dead socket
        with lock:
            if waiting_receiver is conn:
                waiting_receiver = None


def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 9000))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()

    print(f"[🚀] Relay server running on port {port}")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.close()


if __name__ == "__main__":
    main()
