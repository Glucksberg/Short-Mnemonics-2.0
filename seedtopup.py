from mnemonic import Mnemonic
import multiprocessing
import time
from datetime import timedelta
from colorama import Fore, Style, init
import sys

def worker(queue, stop_event):
    mnemo = Mnemonic("english")
    while not stop_event.is_set():
        # Generate a 12-word mnemonic (128 bits of entropy)
        mnemonic = mnemo.generate(strength=128)
        total_chars = len(''.join(mnemonic.split()))
        # Put the mnemonic and its total_chars into the queue
        queue.put((mnemonic, total_chars))

def keyboard_listener(stop_event):
    print("Press 'q' and Enter to stop...")  # Moved outside the loop
    while not stop_event.is_set():
        try:
            if sys.platform == 'win32':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key.lower() == b'q':
                        stop_event.set()
            else:
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    line = sys.stdin.readline()
                    if 'q' in line.lower():
                        stop_event.set()
        except Exception:
            pass
        time.sleep(1)

def collector(queue, stop_event, character_threshold, mnemonics_per_count, log_file_name, start_time):
    init(autoreset=True)
    total_iterations = 0
    results_dict = {}
    print("Collector started.")

    while not stop_event.is_set():
        try:
            mnemonic, total_chars = queue.get(timeout=1)
            total_iterations += 1

            if total_chars <= character_threshold:
                if total_chars not in results_dict:
                    results_dict[total_chars] = set()

                if len(results_dict[total_chars]) < mnemonics_per_count:
                    if mnemonic not in results_dict[total_chars]:
                        results_dict[total_chars].add(mnemonic)
                        # Print the result
                        elapsed_time = time.time() - start_time
                        hms_time = str(timedelta(seconds=int(elapsed_time)))
                        print_output(mnemonic, total_chars, total_iterations, hms_time)
                        # Log the result
                        log_result(mnemonic, total_chars, total_iterations, hms_time, log_file_name)
                else:
                    # We've already collected enough mnemonics for this character count
                    pass

        except multiprocessing.queues.Empty:
            continue  # Continue if the queue is empty

    print("Collector terminating.")

def print_output(mnemonic, total_chars, total_iterations, hms_time):
    print(Fore.GREEN + Style.BRIGHT + f"Mnemonic: {mnemonic}")
    print(Fore.CYAN + Style.BRIGHT + f"Total characters: {total_chars}")
    print(Fore.YELLOW + Style.BRIGHT + f"Total iterations: {total_iterations}")
    print(Fore.MAGENTA + Style.BRIGHT + f"Time elapsed: {hms_time}")
    print(Fore.WHITE + Style.BRIGHT + "----------------------------------")

def log_result(mnemonic, total_chars, total_iterations, hms_time, log_file_name):
    with open(log_file_name, "a") as f:
        f.write(f"Mnemonic: {mnemonic}\n")
        f.write(f"Total characters: {total_chars}\n")
        f.write(f"Total iterations: {total_iterations}\n")
        f.write(f"Time elapsed: {hms_time}\n")
        f.write("----------------------------------\n")

if __name__ == '__main__':
    import argparse

    # Initialize colorama
    init(autoreset=True)

    # Argument parser for configuration options
    parser = argparse.ArgumentParser(description='Mnemonic Generator Script')
    parser.add_argument('--threshold', type=int, default=45, help='Character count threshold')
    parser.add_argument('--count', type=int, default=5, help='Number of mnemonics per character count')
    parser.add_argument('--logfile', type=str, default='mnemonics_log.txt', help='Log file name')
    args = parser.parse_args()

    # Configuration parameters
    character_threshold = args.threshold
    mnemonics_per_count = args.count
    log_file_name = args.logfile

    start_time = time.time()
    stop_event = multiprocessing.Event()
    queue = multiprocessing.Queue()

    # Start keyboard listener in a separate process
    listener_process = multiprocessing.Process(target=keyboard_listener, args=(stop_event,))
    listener_process.daemon = True
    listener_process.start()

    # Number of worker processes
    num_processes = multiprocessing.cpu_count()
    workers = []

    # Start worker processes
    for _ in range(num_processes):
        p = multiprocessing.Process(target=worker, args=(queue, stop_event))
        workers.append(p)
        p.start()

    # Start the collector in the main process
    collector(queue, stop_event, character_threshold, mnemonics_per_count, log_file_name, start_time)

    # Terminate worker processes
    for p in workers:
        p.terminate()
        p.join()

    # Terminate listener process
    listener_process.terminate()
    listener_process.join()

    print("All processes terminated.")
