import socket
import base64
import json
import os

def send_http_request(host, port, method, path, headers=None, body=None):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        request_line = f"{method} {path} HTTP/1.0\r\n"
        
        # Prepare headers
        header_lines = []
        if headers:
            for key, value in headers.items():
                header_lines.append(f"{key}: {value}\r\n")
        
        if body:
            # Ensure Content-Length is set if there's a body
            if not any(h.lower().startswith('content-length:') for h in (headers if headers else {})):
                 header_lines.append(f"Content-Length: {len(body)}\r\n")
            # Ensure Content-Type for JSON if it's a dict/list and not already set
            if isinstance(body, (dict, list)) and not any(h.lower().startswith('content-type:') for h in (headers if headers else {})):
                header_lines.append("Content-Type: application/json\r\n")
        
        full_headers = "".join(header_lines)
        request_str = request_line + full_headers + "\r\n"
        
        # Encode request string part
        request_bytes = request_str.encode('utf-8')

        # Add body if present (must be bytes)
        if body:
            if isinstance(body, (dict, list)):
                body_bytes = json.dumps(body).encode('utf-8')
            elif isinstance(body, str):
                body_bytes = body.encode('utf-8')
            elif isinstance(body, bytes):
                body_bytes = body
            else:
                raise TypeError("Request body must be dict, list, str, or bytes")
            request_bytes += body_bytes
            
        s.sendall(request_bytes)
        
        response = b""
        while True:
            data = s.recv(4096) 
            if not data:
                break
            response += data
        return response
    except socket.error as e:
        print(f"Socket error: {e}")
        return None
    except Exception as e:
        print(f"An error occurred in send_http_request: {e}")
        return None
    finally:
        s.close()

def parse_response(resp_bytes):
    if resp_bytes is None:
        return None, None, None
    try:
        resp_str = resp_bytes.decode('utf-8', errors='ignore')
        parts = resp_str.split('\r\n\r\n', 1)
        header_section = parts[0]
        body_section = parts[1] if len(parts) > 1 else ""
        
        header_lines = header_section.split('\r\n')
        status_line = header_lines[0] if header_lines else ""
        
        # Further parse headers into a dict if needed, for now just return sections
        return status_line, header_section, body_section
    except Exception as e:
        print(f"Error parsing response: {e}")
        # If parsing fails, return the raw decoded string as body for inspection
        return "", "", resp_bytes.decode('utf-8', errors='ignore')


def list_local_files_for_upload():
    """Lists files in the client's current directory for easy selection."""
    try:
        local_files = [f for f in os.listdir(".") if os.path.isfile(f)]
        if not local_files:
            print("Tidak ada file di direktori lokal saat ini untuk di-upload.")
            return None
        
        print("\nFile yang tersedia di direktori lokal untuk di-upload:")
        for i, f_name in enumerate(local_files):
            print(f"{i+1}. {f_name}")
        
        while True:
            try:
                choice = input(f"Pilih nomor file untuk di-upload (1-{len(local_files)}) atau 0 untuk batal: ")
                choice_int = int(choice)
                if 0 <= choice_int <= len(local_files):
                    if choice_int == 0:
                        return None # Batal
                    return local_files[choice_int - 1]
                else:
                    print("Nomor tidak valid.")
            except ValueError:
                print("Masukkan nomor yang valid.")
    except Exception as e:
        print(f"Error saat listing file lokal: {e}")
        return None

def list_server_files_for_delete(host='localhost', port=8885):
    """Gets list of files from server (root) for deletion selection."""
    print(f"\nMendapatkan daftar file dari server {host}:{port} untuk dihapus...")
    resp_bytes = send_http_request(host, port, "GET", "/list")
    status_line, _, body = parse_response(resp_bytes)

    if status_line and "200 OK" in status_line:
        try:
            server_files = json.loads(body)
            if not server_files:
                print("Tidak ada file di direktori root server untuk dihapus.")
                return None
            
            print("\nFile yang tersedia di direktori root server untuk dihapus:")
            for i, f_name in enumerate(server_files):
                print(f"{i+1}. {f_name}")

            while True:
                try:
                    choice = input(f"Pilih nomor file untuk dihapus (1-{len(server_files)}) atau 0 untuk batal: ")
                    choice_int = int(choice)
                    if 0 <= choice_int <= len(server_files):
                        if choice_int == 0:
                            return None # Batal
                        return server_files[choice_int - 1]
                    else:
                        print("Nomor tidak valid.")
                except ValueError:
                    print("Masukkan nomor yang valid.")
        except json.JSONDecodeError:
            print("Gagal mem-parse daftar file dari server.")
            return None
        except Exception as e:
            print(f"Error saat memproses daftar file server: {e}")
            return None
    else:
        print("Gagal mendapatkan daftar file dari server.")
        return None


def list_files(host='localhost', port=8885):
    print(f"\nAttempting to list files from server {host}:{port} (root directory)...")
    resp_bytes = send_http_request(host, port, "GET", "/list")
    status_line, headers, body = parse_response(resp_bytes)

    if not status_line:
        print("No response or error in connection.")
        return

    print(f"Status: {status_line}")
    # print(f"Headers:\n{headers}") # Optional: for debugging
    
    if status_line and "200 OK" in status_line:
        try:
            files = json.loads(body)
            print("\nDaftar file di direktori root server:")
            if files:
                for f_name in files:
                    print(f" - {f_name}")
            else:
                print("Tidak ada file di direktori root server.")
        except json.JSONDecodeError:
            print("Gagal mem-parse daftar file dari server. Respons mentah:")
            print(body)
        except Exception as e:
            print(f"Error saat memproses daftar file: {e}")
            print(f"Body mentah: {body}")
    else:
        print("Gagal mendapatkan daftar file dari server.")
        print(f"Body respons:\n{body}")

def upload_file(filepath, host='localhost', port=8885):
    if not filepath or not os.path.isfile(filepath): # Check if filepath is valid
        print(f"Filepath \'{filepath}\' tidak valid atau file tidak ditemukan.")
        return

    filename = os.path.basename(filepath)
    # Uploads will go to the 'files' directory on the server as per http.py logic for /upload
    print(f"\nMengupload file \'{filename}\' ke direktori \'files\' di server {host}:{port}...")

    try:
        with open(filepath, 'rb') as f:
            filedata_bytes = f.read()
        filedata_b64 = base64.b64encode(filedata_bytes).decode('utf-8')
    except Exception as e:
        print(f"Gagal membaca atau encode file: {e}")
        return

    payload = {'filename': filename, 'filedata': filedata_b64}
    
    resp_bytes = send_http_request(host, port, "POST", "/upload", 
                                   headers={"Content-Type": "application/json"}, 
                                   body=payload)
    
    status_line, headers, body = parse_response(resp_bytes)

    if not status_line:
        print("Tidak ada respons atau error saat upload.")
        return
        
    print(f"Status: {status_line}")
    print(f"Respons Server:\n{body.strip()}")


def delete_file(filename_on_server, host='localhost', port=8885):
    if not filename_on_server: # Check if filename is provided
        print("Nama file untuk dihapus tidak boleh kosong.")
        return
        
    # Deletion will target the root directory on the server as per http.py logic for /delete
    print(f"\nMencoba menghapus file \'{filename_on_server}\' dari direktori root server {host}:{port}...")
    payload = {'filename': filename_on_server}
    
    resp_bytes = send_http_request(host, port, "POST", "/delete",
                                   headers={"Content-Type": "application/json"},
                                   body=payload)
    
    status_line, headers, body = parse_response(resp_bytes)

    if not status_line:
        print("Tidak ada respons atau error saat delete.")
        return

    print(f"Status: {status_line}")
    print(f"Respons Server:\n{body.strip()}")


def main():
    host = input("Masukkan host server (default: localhost): ") or "localhost"
    port_input = input("Masukkan port server (default: 8885 for thread pool, 8889 for process pool): ") or "8885"
    try:
        port = int(port_input)
    except ValueError:
        print(f"Port tidak valid, menggunakan default port {port_input} (jika itu 8885 atau 8889) atau 8885.")
        port = 8885 # Fallback default

    while True:
        print("\n===== MENU CLIENT =====")
        print("1. LIST FILES (dari direktori root di server)")
        print("2. UPLOAD FILE (ke direktori \'files\' di server)")
        print("3. DELETE FILE (dari direktori root di server)")
        print("4. EXIT")
        pilihan = input("Pilih menu [1-4]: ").strip()

        if pilihan == "1":
            list_files(host, port)
        elif pilihan == "2":
            selected_file_to_upload = list_local_files_for_upload()
            if selected_file_to_upload:
                upload_file(selected_file_to_upload, host, port)
            else:
                print("Upload dibatalkan atau tidak ada file yang dipilih.")
        elif pilihan == "3":
            selected_file_to_delete = list_server_files_for_delete(host, port)
            if selected_file_to_delete:
                delete_file(selected_file_to_delete, host, port)
            else:
                print("Delete dibatalkan atau tidak ada file yang dipilih.")
        elif pilihan == "4":
            print("Keluar dari program klien.")
            break
        else:
            print("Pilihan tidak valid. Silakan coba lagi.")

if __name__ == "__main__":
    main()