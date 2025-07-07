import requests
from termcolor import colored
import threading
import time
import random
import os
import signal
from urllib.parse import urlparse

stop_flag = False

def signal_handler(sig, frame):
    global stop_flag
    print(colored("\n[!] Kullanıcı tarafından durduruldu. Program sonlandırılıyor...", 'yellow'))
    stop_flag = True

signal.signal(signal.SIGINT, signal_handler)

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print(colored("************************", 'blue'))
    print(colored("*                      *", 'blue'))
    print(colored("*   Advanced Load Test  *", 'blue'))
    print(colored("*                      *", 'blue'))
    print(colored("************************", 'blue'))
    print(colored("|    made by: Semih    |\n", 'green'))

def validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        return False
    if not parsed.netloc:
        return False
    return True

class LoadTester:
    def __init__(self, url, requests_per_thread, thread_count, delay_range=(0.3, 1.0), extra_headers=None, proxies=None, max_retries=3):
        self.url = url
        self.requests_per_thread = requests_per_thread
        self.thread_count = thread_count
        self.delay_range = delay_range
        self.extra_headers = extra_headers or {}
        self.proxies = proxies
        self.max_retries = max_retries
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()

        # Default User-Agent ekle, yoksa ekle
        if 'User-Agent' not in self.extra_headers:
            self.extra_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'

    def send_requests(self):
        global stop_flag
        for i in range(self.requests_per_thread):
            if stop_flag:
                break

            success = False
            for attempt in range(self.max_retries):
                try:
                    response = requests.get(self.url, headers=self.extra_headers, proxies=self.proxies, timeout=7)
                    with self.lock:
                        self.success_count += 1
                    print(colored(f"[{threading.current_thread().name}] İstek #{i+1} başarılı, Durum Kodu: {response.status_code}", 'cyan'))
                    success = True
                    break
                except requests.RequestException as e:
                    if attempt == self.max_retries -1:
                        with self.lock:
                            self.fail_count += 1
                        print(colored(f"[{threading.current_thread().name}] İstek #{i+1} başarısız: {e}", 'red'))
                    else:
                        time.sleep(0.5 + random.random())  # Retry arası ufak gecikme

            time.sleep(random.uniform(*self.delay_range))

    def start(self):
        threads = []
        for i in range(self.thread_count):
            t = threading.Thread(target=self.send_requests, name=f"Thread-{i+1}")
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def report(self):
        total = self.success_count + self.fail_count
        print(colored("\n--- Test Sonuçları ---", 'green'))
        print(colored(f"Toplam İstek: {total}", 'yellow'))
        print(colored(f"Başarılı İstekler: {self.success_count}", 'green'))
        print(colored(f"Başarısız İstekler: {self.fail_count}", 'red'))
        success_rate = (self.success_count / total * 100) if total > 0 else 0
        print(colored(f"Başarı Oranı: %{success_rate:.2f}", 'blue'))

def get_proxies_from_file(file_path):
    proxies = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Örnek format: http://user:pass@ip:port veya sadece ip:port
                    if not line.startswith("http"):
                        line = "http://" + line
                    proxies.append({
                        'http': line,
                        'https': line,
                    })
    except Exception as e:
        print(colored(f"Proxy dosyası okunamadı: {e}", 'red'))
    return proxies

def main():
    clear_console()
    print_banner()

    url = input(colored("Hedef URL gir (örnek: https://example.com): ", 'magenta')).strip()
    if not validate_url(url):
        print(colored("Geçersiz URL! Lütfen 'http://' veya 'https://' ile başlayan doğru bir URL gir.", 'red'))
        return

    try:
        requests_per_thread = int(input(colored("Her thread için istek sayısı (1-1000): ", 'yellow')))
        thread_count = int(input(colored("Thread sayısı (1-100 arası olabilir, mesela 50): ", 'yellow')))
    except ValueError:
        print(colored("Lütfen geçerli bir sayı giriniz.", 'red'))
        return

    if not (1 <= requests_per_thread <= 1000):
        print(colored("İstek sayısı 1-1000 arasında olmalıdır.", 'red'))
        return

    if not (1 <= thread_count <= 100):
        print(colored("Thread sayısı 1 ile 100 arasında olmalıdır.", 'red'))
        return

    use_proxies = input(colored("Proxy kullanmak ister misin? (y/n): ", 'yellow')).lower()
    proxies = None
    if use_proxies == 'y':
        proxy_file = input(colored("Proxy listesinin dosya yolunu gir (her satırda 1 proxy, format: http://ip:port veya http://user:pass@ip:port): ", 'cyan')).strip()
        proxy_list = get_proxies_from_file(proxy_file)
        if not proxy_list:
            print(colored("Proxy listesi boş veya okunamadı, devam ediliyor proxiesiz.", 'yellow'))
        else:
            # Round-robin proxy kullanmak için listeyi döndür
            proxies = proxy_list

    extra_headers = {}
    add_headers = input(colored("Özel HTTP header eklemek ister misin? (y/n): ", 'yellow')).lower()
    if add_headers == 'y':
        while True:
            header = input(colored("Header (anahtar:değer) formatında, bitirmek için boş bırak: ", 'cyan')).strip()
            if not header:
                break
            if ':' not in header:
                print(colored("Format yanlış! Tekrar dene.", 'red'))
                continue
            key, value = map(str.strip, header.split(':', 1))
            extra_headers[key] = value

    print(colored(f"\nTest başlıyor! {thread_count} thread ile, her thread {requests_per_thread} istek gönderecek.\nCtrl+C ile iptal edebilirsiniz.\n", 'green'))

    if proxies:
        # Proxy listesi varsa round robin yap
        def proxy_generator():
            while True:
                for p in proxies:
                    yield p
        proxy_iter = proxy_generator()
    else:
        proxy_iter = None

    # Proxy desteği olan LoadTester versiyonu
    class LoadTesterWithProxies(LoadTester):
        def send_requests(self_inner):
            global stop_flag
            for i in range(self_inner.requests_per_thread):
                if stop_flag:
                    break

                success = False
                for attempt in range(self_inner.max_retries):
                    try:
                        proxy = None
                        if proxy_iter:
                            proxy = next(proxy_iter)
                        response = requests.get(self_inner.url, headers=self_inner.extra_headers, proxies=proxy, timeout=7)
                        with self_inner.lock:
                            self_inner.success_count += 1
                        print(colored(f"[{threading.current_thread().name}] İstek #{i+1} başarılı, Durum Kodu: {response.status_code}", 'cyan'))
                        success = True
                        break
                    except requests.RequestException as e:
                        if attempt == self_inner.max_retries -1:
                            with self_inner.lock:
                                self_inner.fail_count += 1
                            print(colored(f"[{threading.current_thread().name}] İstek #{i+1} başarısız: {e}", 'red'))
                        else:
                            time.sleep(0.5 + random.random())

                time.sleep(random.uniform(*self_inner.delay_range))

    if proxies:
        tester = LoadTesterWithProxies(url, requests_per_thread, thread_count, extra_headers=extra_headers, proxies=None)
    else:
        tester = LoadTester(url, requests_per_thread, thread_count, extra_headers=extra_headers)

    tester.start()
    tester.report()

if __name__ == "__main__":
    main()
