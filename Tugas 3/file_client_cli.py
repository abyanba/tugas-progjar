import socket
import json
import base64
import logging

server_address=('0.0.0.0',7777)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        logging.warning(f"sending message ")
        sock.sendall(command_str.encode())
        # Look for the response, waiting until socket is done (no more data)
        data_received="" #empty string
        while True:
            #socket does not receive all data at once, data comes in part, need to be concatenated at the end of process
            data = sock.recv(1024)
            if data:
                #data is not empty, concat with previous content
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                # no more data, stop the process by break
                break
        # at this point, data_received (string) will contain all data coming from the socket
        # to be able to use the data_received as a dict, need to load it using json.loads()
        hasil = json.loads(data_received)
        logging.warning("data received from server:")
        return hasil
    except:
        logging.warning("error during data receiving")
        return False


def remote_list():
    command_str=f"LIST"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False

def remote_get(filename=""):
    command_str=f"GET {filename}"
    hasil = send_command(command_str)
    if (hasil['status']=='OK'):
        #proses file dalam bentuk base64 ke bentuk bytes
        namafile= hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        fp = open(namafile,'wb+')
        fp.write(isifile)
        fp.close()
        return True
    else:
        print("Gagal")
        return False

def remote_upload(filename):
    try:
        with open(filename, 'rb') as f:
            filedata = f.read()
        filedata_b64 = base64.b64encode(filedata).decode()
        # Bungkus base64 dengan tanda kutip agar tidak terpecah di server
        command_str = f'UPLOAD {filename} "{filedata_b64}"'
        hasil = send_command(command_str)
        if hasil['status'] == 'OK':
            print(hasil['data'])
            return True
        else:
            print("Gagal upload:", hasil['data'])
            return False
    except Exception as e:
        print(f"Gagal upload: {e}")
        return False

def remote_delete(filename):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print(hasil['data'])
        return True
    else:
        print("Gagal delete:", hasil['data'])
        return False


if __name__=='__main__':
    server_address=('127.0.0.1',6969)
    while True:
        print("\n=== FILE CLIENT CLI ===")
        print("1. LIST")
        print("2. GET")
        print("3. UPLOAD")
        print("4. DELETE")
        print("5. EXIT")
        pilihan = input("Pilih menu [1-5]: ").strip()
        if pilihan == '1':
            remote_list()
        elif pilihan == '2':
            filename = input("Masukkan nama file yang ingin diunduh: ").strip()
            remote_get(filename)
        elif pilihan == '3':
            filename = input("Masukkan nama file lokal yang ingin diupload: ").strip()
            remote_upload(filename)
        elif pilihan == '4':
            filename = input("Masukkan nama file yang ingin dihapus di server: ").strip()
            remote_delete(filename)
        elif pilihan == '5':
            print("Keluar.")
            break
        else:
            print("Pilihan tidak valid.")