from socket import *
import socket
import sys
import logging
from concurrent.futures import ProcessPoolExecutor
from http import HttpServer

def ProcessTheClient(connection, address):
    httpserver_local = HttpServer() # Instantiate HttpServer locally for each process
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
                            hasil = httpserver_local.proses(full_request_str) # Use local instance
                            
                            if hasil is not None:
                                connection.sendall(hasil) # Send 'hasil' directly
                                logging.info(f"Client {address}: Response sent to client.")
                            else:
                                logging.error(f"Client {address}: 'hasil' from httpserver_local.proses() is None. No response sent.")
                            return 

                    else: # headers_ended is True
                        try:
                            request_line_info = rcv.decode(errors='ignore').split('\r\n')[0] if rcv else "Unknown (in 'else headers_ended' branch)"
                        except IndexError:
                            request_line_info = "Malformed Request Line (in 'else headers_ended' branch)"
                        logging.warning(f"Client {address}: Reached 'headers_ended==True' branch. Request: {request_line_info}")
                        
                        hasil = httpserver_local.proses(rcv.decode(errors='ignore')) # Use local instance
                        if hasil is not None:
                            connection.sendall(hasil) # Send 'hasil' directly
                        else:
                            logging.error(f"Client {address}: 'hasil' from httpserver_local.proses() (headers_ended==True branch) is None.")
                        return 
                else: # No data received, client closed connection
                    if rcv and not headers_ended : 
                        try:
                            request_line_info = rcv.decode(errors='ignore').split('\r\n')[0]
                        except IndexError:
                            request_line_info = "Malformed Request Line (partial data)"
                        logging.info(f"Client {address}: Connection closed by client with partial data. Processing as simple request: {request_line_info}")
                        hasil = httpserver_local.proses(rcv.decode(errors='ignore')) # Use local instance
                        if hasil is not None:
                            connection.sendall(hasil) # Send 'hasil' directly
                        else:
                            logging.error(f"Client {address}: 'hasil' from httpserver_local.proses() (partial data) is None.")
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
        try:
            # Signal that no more data will be sent from this end.
            # This can help ensure that any buffered data is flushed.
            connection.shutdown(socket.SHUT_WR)
        except OSError as e:
            # This can happen if the socket is already closed or in a bad state.
            logging.warning(f"Client {address}: OSError during connection.shutdown(SHUT_WR): {e}")
        except Exception as e: # Catch any other unexpected errors during shutdown
            logging.error(f"Client {address}: Unexpected error during connection.shutdown(SHUT_WR): {e}")
        finally:
            # Always attempt to close the connection.
            connection.close()
            logging.info(f"Connection with {address} closed. (Last identified request: {request_line_info})")


def Server():
    # Setup logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(processName)s - %(message)s', 
                        stream=sys.stdout)

    the_clients = []
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    my_socket.bind(('0.0.0.0', 8889))
    my_socket.listen(1)
    logging.info("Server (Process Pool) listening on port 8889")

    with ProcessPoolExecutor(20) as executor:
        while True:
            try:
                connection, client_address = my_socket.accept()
                p = executor.submit(ProcessTheClient, connection, client_address)
                the_clients.append(p)
                # Clean up completed futures to prevent the list from growing indefinitely
                the_clients = [client for client in the_clients if not client.done()]
                # active_tasks = sum(1 for client in the_clients if client.running()) # This is for server info, not an error response
                # print(f"Current active/pending processes in pool (approx): {active_tasks}") # This is for server info
            except Exception as e:
                logging.exception(f"Error in server accept loop: {e}")


def main():
    Server()

if __name__=="__main__":
    main()
