import multiprocessing
import math
import time

def heavy_factorial(n):
    # Compute factorial repeatedly to maximize CPU load
    result = 1
    for _ in range(1000):  # Repeat to extend workload
        result = math.factorial(n)
    return result

def worker(core_id, n):
    print(f"Core {core_id} started heavy factorial calc.")
    start = time.time()
    heavy_factorial(n)
    end = time.time()
    print(f"Core {core_id} finished in {end - start:.2f} seconds.")

if __name__ == "__main__":
    cpu_count = multiprocessing.cpu_count()
    n = 30000  # Large number for factorial (adjust if too slow/fast)
    
    processes = []
    for i in range(cpu_count):
        p = multiprocessing.Process(target=worker, args=(i, n))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()
