import socket
import os

def list_files(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(b'LIST')
            data = s.recv(65536)
            return data.decode()
    except Exception as e:
        return f"ERROR: {e}"

def upload_file(host, port, filepath):
    fname = os.path.basename(filepath)
    fsize = os.path.getsize(filepath)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(f'UPLOAD {fname} {fsize}'.encode())
            ack = s.recv(32)
            if ack != b'READY':
                return False  # Server not ready
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    s.sendall(chunk)
            status = s.recv(32)
            return status == b'UPLOAD_OK'
    except Exception:
        return False

def download_file(host, port, fname, dest_folder):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(f'DOWNLOAD {fname}'.encode())
            size_data = s.recv(32)
            if size_data.startswith(b'ERROR'):
                return False
            try:
                fsize = int(size_data)
            except Exception:
                return False
            s.sendall(b'READY')
            dest = os.path.join(dest_folder, fname)
            with open(dest, 'wb') as f:
                received = 0
                while received < fsize:
                    chunk = s.recv(min(4096, fsize - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            status = s.recv(32)
            return status == b'DOWNLOAD_OK'
    except Exception:
        return False
