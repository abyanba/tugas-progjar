import sys
import os
import os.path
from datetime import datetime
import json
import base64

class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        self.types['.json'] = 'application/json'

        self.file_dir = 'files'  # Directory for file uploads
        if not os.path.exists(self.file_dir):
            os.makedirs(self.file_dir)
        if not os.path.isdir(self.file_dir):
            print(f"Error: '{self.file_dir}' exists but is not a directory. Operations may fail.", file=sys.stderr)

    def response(self, kode=404, message='Not Found', messagebody_input=b"", headers=None):
        if headers is None:
            headers = {}
        tanggal = datetime.now().strftime('%c')

        if not isinstance(messagebody_input, bytes):
            messagebody_bytes = messagebody_input.encode('utf-8')
        else:
            messagebody_bytes = messagebody_input
        
        resp_lines=[]
        resp_lines.append(f"HTTP/1.0 {kode} {message}\r\n")
        resp_lines.append(f"Date: {tanggal}\r\n")
        resp_lines.append("Connection: close\r\n")
        resp_lines.append("Server: myserver/1.0\r\n")
        resp_lines.append(f"Content-Length: {len(messagebody_bytes)}\r\n")

        for kk, vv in headers.items():
            resp_lines.append(f"{kk}: {vv}\r\n")
        resp_lines.append("\r\n")

        response_headers_str = "".join(resp_lines)
        final_response_bytes = response_headers_str.encode('utf-8') + messagebody_bytes
        return final_response_bytes

    def proses(self, data):
        parts = data.split("\r\n\r\n", 1)
        header_section = parts[0]
        body_section = parts[1] if len(parts) > 1 else ""

        requests = header_section.split("\r\n")
        if not requests or not requests[0]:
            return self.response(400, 'Bad Request', b'Empty request line', {})

        baris = requests[0]
        all_headers_list = [n for n in requests[1:] if n != '']

        j = baris.split(" ")
        if len(j) < 2:
            return self.response(400, 'Bad Request', b'Malformed request line', {})
        
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()

            request_headers_dict = {}
            for header_line in all_headers_list:
                if ':' in header_line:
                    key, value = header_line.split(":", 1)
                    request_headers_dict[key.strip().lower()] = value.strip()

            if method == 'GET':
                return self.http_get(object_address, request_headers_dict)
            elif method == 'POST':
                return self.http_post(object_address, request_headers_dict, body_section)
            else:
                return self.response(405, 'Method Not Allowed', f'{method} not supported'.encode('utf-8'), {})
        except IndexError:
            return self.response(400, 'Bad Request', b'Malformed request line (IndexError)', {})
        except Exception as e:
            print(f"Error processing request: {e}", file=sys.stderr)
            return self.response(500, 'Internal Server Error', f'Error processing request: {str(e)}'.encode('utf-8'), {})

    def http_get(self, object_address, request_headers):
        if object_address == '/list':
            try:
                current_working_directory = '.' # Server's root directory
                if not os.path.isdir(current_working_directory):
                     return self.response(500, 'Internal Server Error', b"Server root directory not found or is not a directory.", {})
                
                file_list = os.listdir(current_working_directory)
                files_only = [f for f in file_list if os.path.isfile(os.path.join(current_working_directory, f))]
                json_response_body = json.dumps(files_only)
                return self.response(200, 'OK', json_response_body.encode('utf-8'), {'Content-Type': 'application/json'})
            except Exception as e:
                print(f"Error listing files in root directory: {e}", file=sys.stderr)
                return self.response(500, 'Internal Server Error', f'Error listing files: {str(e)}'.encode('utf-8'), {})

        if object_address == '/':
            return self.response(200, 'OK', b'Ini Adalah web Server percobaan', {})
        if object_address == '/video':
            return self.response(302, 'Found', b'', {'Location': 'https://youtu.be/katoxpnTf04'})
        if object_address == '/santai':
            return self.response(200, 'OK', b'santai saja', {})

        target_file_path_relative = object_address
        if target_file_path_relative.startswith('/'):
            target_file_path_relative = target_file_path_relative[1:]

        # Security: Prevent access outside current directory.
        base_dir = os.path.abspath(".") 
        abs_target_path = os.path.abspath(os.path.join(base_dir, target_file_path_relative))

        if not abs_target_path.startswith(base_dir):
            return self.response(403, "Forbidden", b"Access denied.", {})

        if os.path.isfile(abs_target_path):
            try:
                with open(abs_target_path, 'rb') as fp:
                    isi = fp.read()
                
                fext = os.path.splitext(abs_target_path)[1].lower()
                content_type = self.types.get(fext, 'application/octet-stream')
                
                headers_resp = {'Content-Type': content_type}
                return self.response(200, 'OK', isi, headers_resp)
            except Exception as e:
                print(f"Error serving file {abs_target_path}: {e}", file=sys.stderr)
                return self.response(500, 'Internal Server Error', f'Error serving file: {str(e)}'.encode('utf-8'), {})
        else:
            return self.response(404, 'Not Found', f"Resource '{object_address}' not found.".encode('utf-8'), {})

    def http_post(self, object_address, request_headers, body_str):
        content_type = request_headers.get('content-type', '').lower()
        if 'application/json' not in content_type:
            return self.response(415, 'Unsupported Media Type', b'Content-Type must be application/json', {})

        try:
            payload = json.loads(body_str)
        except json.JSONDecodeError:
            return self.response(400, 'Bad Request', b'Invalid JSON body', {})

        if object_address == '/upload':
            if not os.path.isdir(self.file_dir):
                return self.response(500, 'Internal Server Error', f"Upload directory '{self.file_dir}' is not accessible.".encode('utf-8'), {})
            
            filename = payload.get('filename')
            filedata_b64 = payload.get('filedata')

            if not filename or not filedata_b64:
                return self.response(400, 'Bad Request', b'Missing filename or filedata', {})
            
            base_filename = os.path.basename(filename) # Sanitize against directory traversal
            filepath = os.path.join(self.file_dir, base_filename) # Uploads to self.file_dir
            
            try:
                decoded_data = base64.b64decode(filedata_b64)
                with open(filepath, 'wb') as f:
                    f.write(decoded_data)
                return self.response(200, 'OK', f"File '{base_filename}' uploaded successfully to '{self.file_dir}'.".encode('utf-8'), {'Content-Type': 'text/plain'})
            except (base64.binascii.Error, ValueError):
                return self.response(400, 'Bad Request', b'Invalid base64 data', {})
            except IOError as e:
                print(f"Error writing file {filepath}: {e}", file=sys.stderr)
                return self.response(500, 'Internal Server Error', f'Error writing file: {str(e)}'.encode('utf-8'), {})
            except Exception as e:
                print(f"Unexpected error during upload of {filepath}: {e}", file=sys.stderr)
                return self.response(500, 'Internal Server Error', b'Unexpected error during upload.', {})

        elif object_address == '/delete':
            filename = payload.get('filename')
            if not filename:
                return self.response(400, 'Bad Request', b'Missing filename', {})

            base_filename = os.path.basename(filename) # Sanitize
            filepath_in_root = os.path.join('.', base_filename) # Delete from server's root directory

            if not os.path.isfile(filepath_in_root):
                return self.response(404, 'Not Found', f"File '{base_filename}' not found in server root for deletion.".encode('utf-8'), {'Content-Type': 'text/plain'})
            
            try:
                os.remove(filepath_in_root)
                return self.response(200, 'OK', f"File '{base_filename}' deleted successfully from server root.".encode('utf-8'), {'Content-Type': 'text/plain'})
            except OSError as e:
                print(f"Error deleting file {filepath_in_root}: {e}", file=sys.stderr)
                return self.response(500, 'Internal Server Error', f'Error deleting file: {str(e)}'.encode('utf-8'), {})
            except Exception as e:
                print(f"Unexpected error during deletion of {filepath_in_root}: {e}", file=sys.stderr)
                return self.response(500, 'Internal Server Error', b'Unexpected error during deletion.', {})
        
        else:
            return self.response(404, 'Not Found', f"POST endpoint '{object_address}' not found.".encode('utf-8'), {})

if __name__=="__main__":
    print("HttpServer class definition. Not meant to be run directly without a controlling server script.")