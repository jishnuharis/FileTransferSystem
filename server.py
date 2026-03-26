import socket
import threading
import os

waiting_receiver = None
lock = threading.Lock()

def relay(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        try:
            src.close()
        except:
            pass
        try:
            dst.close()
        except:
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
                # store receiver, no messages sent
                if waiting_receiver is None:
                    waiting_receiver = conn
                else:
                    # only one receiver allowed
                    conn.close()

        elif role == "SENDER":
            print(f"[+] Sender connected: {addr}")
            with lock:
                if waiting_receiver is None:
                    conn.sendall(b"NO_RECEIVER\n")
                    conn.close()
                    return

                receiver = waiting_receiver
                waiting_receiver = None

            # only sender gets START
            try:
                conn.sendall(b"START\n")
            except:
                conn.close()
                receiver.close()
                return

            print("[*] Linking sender and receiver...")
            t1 = threading.Thread(target=relay, args=(conn, receiver), daemon=True)
            t2 = threading.Thread(target=relay, args=(receiver, conn), daemon=True)
            t1.start()
            t2.start()

        else:
            conn.close()

    except Exception as e:
        print("Error in handle_client:", e)
        try:
            conn.close()
        except:
            pass

def main():
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 9000))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()

    print(f"[🚀] Relay server running on port {port}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
