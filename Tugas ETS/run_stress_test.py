import csv
import subprocess
import time
import os
import signal
from stresstest import stress_test

# Pengujian pada kedua tipe server pool
SERVER_CONFIGS = [
    {
        "name": "ThreadPool",
        "script": "server_multithreadpool.py",
        "mode": "thread",
        "port": 9000,
    },
    {
        "name": "ProcessPool",
        "script": "server_multiprocesspool.py",
        "mode": "process",
        "port": 9001,
    }
]

OPERATIONS = ['UPLOAD', 'DOWNLOAD']
VOLUME_FILES = ['file_10mb.bin', 'file_50mb.bin', 'file_100mb.bin']
CLIENT_WORKERS = [1, 5, 50]
SERVER_WORKERS = [1, 5, 50]
SERVER_HOST = 'localhost'

def prepare_test_files():
    for fname, size in zip(VOLUME_FILES, [10*1024**2, 50*1024**2, 100*1024**2]):
        if not os.path.exists(fname):
            with open(fname, 'wb') as f:
                f.write(os.urandom(size))

def start_server(server_script, server_workers, server_port):
    env = os.environ.copy()
    env["SERVER_POOL"] = str(server_workers)
    env["PORT"] = str(server_port)
    return subprocess.Popen(
        ['python', server_script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid if os.name != "nt" else None  # UNIX only
    )

def stop_server(proc):
    if proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

def wait_server_ready(host, port, timeout=5):
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            time.sleep(0.2)
    return False

def main():
    prepare_test_files()
    csv_path = 'stress_test_results.csv'
    if os.path.exists(csv_path):
        os.remove(csv_path)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'No', 'ServerType', 'Operasi', 'Volume', 'ClientWorker', 'ServerWorker',
            'WaktuTotal', 'Throughput (KB/s)', 'ClientSukses', 'ClientGagal', 'ServerSukses', 'ServerGagal'
        ])
        nomor = 1
        for server_cfg in SERVER_CONFIGS:
            print(f"\n=== Testing {server_cfg['name']} ===")
            for op in OPERATIONS:
                for vf in VOLUME_FILES:
                    for nc in CLIENT_WORKERS:
                        for ns in SERVER_WORKERS:
                            print(f"[{nomor}] {server_cfg['name']} | {op} {vf} client={nc} server={ns} ...")
                            proc = start_server(server_cfg['script'], ns, server_cfg['port'])
                            if not wait_server_ready(SERVER_HOST, server_cfg['port']):
                                print("Server gagal start!")
                                stop_server(proc)
                                continue
                            try:
                                result = stress_test(
                                    server_cfg['mode'],
                                    op,
                                    vf,
                                    SERVER_HOST,
                                    server_cfg['port'],
                                    nc,
                                    ns
                                )
                            finally:
                                stop_server(proc)
                                time.sleep(1)  # Biarkan port benar-benar free
                            writer.writerow([
                                nomor, server_cfg['name'], op, vf, nc, ns,
                                f"{result['waktu_total']:.2f}",
                                f"{result['throughput']:.2f}",
                                result['sukses'], result['gagal'],
                                result.get('server_sukses', result['sukses']),
                                result.get('server_gagal', result['gagal'])
                            ])
                            f.flush()
                            nomor += 1

if __name__ == '__main__':
    main()
