import time
from threading import Thread

import psutil


def get_processes_by_mem():
    processes = []
    for proc in psutil.process_iter():
        try:
            if proc.status() == "zombie":
                # Avoid logging zombie processes
                continue

            processes.append(proc.as_dict())
        except psutil.NoSuchProcess:
            pass

    processes.sort(key=lambda x: x["memory_percent"], reverse=True)
    return processes


def print_mem_usage(seconds_between_calls):
    while True:
        processes = "\n".join([str(proc) for proc in get_processes_by_mem()])
        print(
            f"Memory usage: {psutil.virtual_memory().percent}\n=============================================\n{processes}\n============================================="
        )
        time.sleep(seconds_between_calls)


def start_mem_monitoring(seconds_between_calls=30):
    thread = Thread(target=print_mem_usage, args=(seconds_between_calls,), daemon=True)
    thread.start()


if __name__ == "__main__":
    start_mem_monitoring(seconds_between_calls=2)
    for i in range(30):
        print("still here")
        time.sleep(1)
