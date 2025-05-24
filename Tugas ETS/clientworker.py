import socket
import os
import time

def list_files(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(b'LIST')
            data = s.recv(65536)
            return True, data.decode()
    except Exception as e:
        return False, str(e)

def upload_file(host, port, filepath):
    try:
        fname = os.path.basename(filepath)
        fsize = os.path.getsize(filepath)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(f'UPLOAD {fname} {fsize}'.encode())
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk: break
                    s.sendall(chunk)
            status = s.recv(1024)
            return status == b'UPLOAD_OK'
    except Exception as e:
        return False

def download_file(host, port, fname, dest_folder):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            s.sendall(f'DOWNLOAD {fname}'.encode())
            size_data = s.recv(32)
            if size_data.startswith(b'ERROR'):
                return False
            fsize = int(size_data)
            dest = os.path.join(dest_folder, fname)
            with open(dest, 'wb') as f:
                received = 0
                while received < fsize:
                    chunk = s.recv(min(4096, fsize - received))
                    if not chunk: break
                    f.write(chunk)
                    received += len(chunk)
            return received == fsize
    except Exception as e:
        return False

# For testing purpose
if __name__ == "__main__":
    print(list_files('localhost', 9000))
