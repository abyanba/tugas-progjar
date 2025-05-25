import socket
import threading
import logging
from datetime import datetime

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        try:
            while True:
                # Menerima data, 32 bytes cukup untuk request TIME/QUIT
                data = self.connection.recv(32)
                if not data:
                    break
                request = data.decode('utf-8')

                # Cek request sesuai ketentuan
                if request == "TIME\r\n":
                    logging.warning(f"Client {self.address} requested TIME")
                    # Ambil waktu saat ini dalam format hh:mm:ss
                    now = datetime.now()
                    waktu = now.strftime("%H:%M:%S")
                    # Format response
                    response = f"JAM {waktu}\r\n"
                    self.connection.sendall(response.encode('utf-8'))
                elif request == "QUIT\r\n":
                    # Jika request quit, langsung tutup koneksi
                    break
                else:
                    # Respon jika request tidak valid
                    self.connection.sendall(b"Invalid request\r\n")
        except Exception as e:
            logging.error(f"Error: {e}")
        finally:
            self.connection.close()
            logging.warning(f"Connection closed: {self.address}")

class TimeServer(threading.Thread):
    def __init__(self, port=45000):
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threading.Thread.__init__(self)
        self.port = port

    def run(self):
        self.my_socket.bind(('0.0.0.0', self.port))
        self.my_socket.listen(5)
        logging.warning(f"Time Server running on port {self.port}...")
        while True:
            connection, client_address = self.my_socket.accept()
            logging.warning(f"Connection from {client_address}")
            clt = ProcessTheClient(connection, client_address)
            clt.start()
            self.the_clients.append(clt)

def main():
    svr = TimeServer()
    svr.start()

if __name__ == "__main__":
    main()
