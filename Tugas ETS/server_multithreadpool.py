import socket
import os
from concurrent.futures import ThreadPoolExecutor

HOST = '0.0.0.0'
PORT = int(os.getenv("PORT", 9000))
WORKER_POOL = int(os.getenv("SERVER_POOL", 5))
FILES_DIR = "files_thread"

if not os.path.exists(FILES_DIR):
    os.makedirs(FILES_DIR)

def handle_client(conn, addr):
    try:
        data = conn.recv(1024).decode()
        cmd, *args = data.split()
        if cmd == 'LIST':
            files = '\n'.join(os.listdir(FILES_DIR))
            conn.sendall(files.encode())
        elif cmd == 'UPLOAD':
            fname, fsize = args[0], int(args[1])
            conn.sendall(b'READY')
            with open(os.path.join(FILES_DIR, fname), 'wb') as f:
                received = 0
                while received < fsize:
                    chunk = conn.recv(min(4096, fsize - received))
                    if not chunk: break
                    f.write(chunk)
                    received += len(chunk)
            conn.sendall(b'UPLOAD_OK')
        elif cmd == 'DOWNLOAD':
            fname = args[0]
            fpath = os.path.join(FILES_DIR, fname)
            if not os.path.exists(fpath):
                conn.sendall(b'ERROR_NOT_FOUND')
            else:
                size = os.path.getsize(fpath)
                conn.sendall(f"{size}".encode())
                ack = conn.recv(32)
                if ack != b'READY':
                    return
                with open(fpath, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk: break
                        conn.sendall(chunk)
                conn.sendall(b'DOWNLOAD_OK')
        else:
            conn.sendall(b'UNKNOWN_CMD')
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server running on {HOST}:{PORT} with ThreadPool({WORKER_POOL})")
        with ThreadPoolExecutor(WORKER_POOL) as pool:
            while True:
                conn, addr = s.accept()
                pool.submit(handle_client, conn, addr)

if __name__ == '__main__':
    main()
