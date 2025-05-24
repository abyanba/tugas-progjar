def stress_test(
        mode, # "thread" atau "process"
        operation, # 'UPLOAD' atau 'DOWNLOAD'
        volume_file, # path ke file
        host, port,
        n_worker_client,
        n_worker_server
    ):
    import time
    from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
    from clientworker import upload_file, download_file, list_files
    import os

    success = 0
    fail = 0

    if operation == "UPLOAD":
        fn = lambda args: upload_file(host, port, volume_file)
        args_list = [()] * n_worker_client
    elif operation == "DOWNLOAD":
        fname = os.path.basename(volume_file)
        dest_folder = "./client_download"
        os.makedirs(dest_folder, exist_ok=True)
        fn = lambda args: download_file(host, port, fname, dest_folder)
        args_list = [()] * n_worker_client

    pool_class = ThreadPoolExecutor if mode == "thread" else ProcessPoolExecutor

    start = time.time()
    with pool_class(n_worker_client) as pool:
        results = []
        for args in args_list:
            future = pool.submit(fn, args)
            results.append(future)
        for fut in as_completed(results):
            try:
                result = fut.result()
                if result:
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
    end = time.time()
    total_time = end - start
    throughput = (os.path.getsize(volume_file) * success / total_time / 1024) if total_time > 0 else 0

    return {
        "waktu_total": total_time,
        "throughput": throughput,
        "sukses": success,
        "gagal": fail,
        "server_sukses": success,
        "server_gagal": fail
    }
