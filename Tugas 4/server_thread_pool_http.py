from socket import *
import socket
import sys
import logging
from concurrent.futures import ThreadPoolExecutor
from http import HttpServer 

httpserver = HttpServer()

def ProcessTheClient(connection, address):
    logging.info(f"Connection accepted from {address}")
    rcv = b""
    headers_ended = False
    content_length = 0
    request_line_info = "N/A"

    try:
        while True:
            try:
                data = connection.recv(1024*1024) 
                if data:
                    rcv += data
                    if not headers_ended:
                        if b"\r\n\r\n" in rcv:
                            headers_ended = True
                            header_bytes, rest_bytes = rcv.split(b"\r\n\r\n", 1)
                            
                            try:
                                request_line_info = header_bytes.decode(errors='ignore').split("\r\n")[0]
                            except IndexError:
                                request_line_info = "Malformed Request Line"
                            logging.info(f"Client {address}: Request: {request_line_info}")

                            header_str = header_bytes.decode(errors='ignore')
                            for line in header_str.split("\r\n"):
                                if line.lower().startswith("content-length:"):
                                    try:
                                        content_length = int(line.split(":", 1)[1].strip())
                                    except ValueError:
                                        logging.warning(f"Client {address}: Invalid Content-Length value in '{line.strip()}' for request '{request_line_info}'")
                                        content_length = 0 
                            
                            body = rest_bytes
                            if content_length > 0:
                                while len(body) < content_length:
                                    more = connection.recv(1024*1024)
                                    if not more:
                                        logging.warning(f"Client {address}: Connection closed by client while reading body for '{request_line_info}'. Received {len(body)}/{content_length} bytes.")
                                        break 
                                    body += more
                            
                            full_request_str = (header_bytes + b"\r\n\r\n" + body).decode(errors='ignore')
                            hasil = httpserver.proses(full_request_str)
                            connection.sendall(hasil + b"\r\n\r\n") # Ensure this is the correct way to send for thread pool
                            return 
                    else: 
                        # try:
                        #     request_line_info = rcv.decode(errors='ignore').split('\r\n')[0] if rcv else "Unknown (in 'else headers_ended' branch)" # Debug info
                        # except IndexError:
                        #     request_line_info = "Malformed Request Line (in 'else headers_ended' branch)" # Debug info
                        # logging.warning(f"Client {address}: Reached 'headers_ended==True' branch. Processing potentially incomplete request: {request_line_info}") # Debug log
                        
                        hasil = httpserver.proses(rcv.decode(errors='ignore'))
                        connection.sendall(hasil + b"\r\n\r\n")
                        return 
                else: 
                    if rcv and not headers_ended : 
                        try:
                            request_line_info = rcv.decode(errors='ignore').split('\r\n')[0]
                        except IndexError:
                            request_line_info = "Malformed Request Line (partial data)"
                        logging.info(f"Client {address}: Connection closed by client with partial data. Processing as simple request: {request_line_info}")
                        hasil = httpserver.proses(rcv.decode(errors='ignore'))
                        connection.sendall(hasil + b"\r\n\r\n")
                        return
                    break 
            except OSError as e:
                logging.error(f"Client {address}: OSError in communication loop: {e}. Request hint: {request_line_info}")
                break 
            except ValueError as e: 
                logging.error(f"Client {address}: ValueError processing request data (e.g. Content-Length): {e}. Request hint: {request_line_info}")
                break
            except Exception as e:
                logging.exception(f"Client {address}: Unexpected error in communication loop for request hint '{request_line_info}': {e}")
                break
    finally:
        logging.info(f"Connection with {address} closed. (Last identified request: {request_line_info})")
        connection.close()


def Server():
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s', 
                        stream=sys.stdout)

    the_clients_futures = [] 
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.bind(('0.0.0.0', 8885))
    my_socket.listen(1)
    logging.info("Server (Thread Pool) listening on port 8885")

    with ThreadPoolExecutor(max_workers=20) as executor:
        while True:
            try:
                connection, client_address = my_socket.accept()
                future = executor.submit(ProcessTheClient, connection, client_address)
                the_clients_futures.append(future)
                
                # Clean up completed futures to prevent the list from growing indefinitely
                the_clients_futures = [f for f in the_clients_futures if not f.done()]
                
                # active_threads = sum(1 for f in the_clients_futures if f.running()) # Server info, not error response
                # print(f"Current active threads (approx): {active_threads}") # Server info
            except Exception as e:
                logging.exception(f"Error in server accept loop: {e}")

def main():
    Server()

if __name__=="__main__":
    main()
