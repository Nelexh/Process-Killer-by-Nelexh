import psutil
#from plyer import notification
import time
from playsound3 import playsound
import logging
import threading
import os
from dataclasses import dataclass
from winotify import Notification
import json

PROCESS_EXTENSIONS = ['exe', 'dll', 'sys', 'src', 'com']

# Paths
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(BASE_PATH, 'files/notification.ico')
mp3_path = os.path.join(BASE_PATH, 'files/sound.mp3')
list_path = os.path.join(BASE_PATH, 'data/list.txt')
whilelist_path = os.path.join(BASE_PATH, 'data/whitelist.txt')
log_path = os.path.join(BASE_PATH, 'data/app.log')
if not os.path.exists(log_path):
    with open(log_path, 'w', encoding='utf-8') as file:
        file.write('app.log')



def run_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Old ver
    # logging.basicConfig(level=logging.INFO,
    #    format='%(asctime)s - %(levelname)s - %(message)s',
    #    filename=log_path,
    #    filemode='a')

#Main class
class Process_Killer:
    # Initialization
    def __init__(self, config):
        logging.info('The programm is starting')
        self.running = False

        self.config = config
        # self.icon_path = None
        # self.mp3_path = None
        # self.list_path = None
        # self.stats = None
        self._init_config()
        self._validate_files()
        self._init_stats()

        self.processes = self._load_processes_from_list()
        self.whitelist = self._load_whitelist_processes()
        self.last_notification = {}
        self.log_stats_count = 0

    #==== Initialization methods ====
    def _init_config(self):
        self.icon_path = self.config.ICON_PATH
        self.mp3_path = self.config.MP3_PATH
        self.list_path = self.config.LIST_PATH
        self.whitelist_path = self.config.WHITELIST_PATH
        self.checker_sleep_time = self.config.CHECKER_SLEEP_TIME
        self.anti_spam_time = self.config.ANTI_SPAM_TIME

        self.log_path = os.path.join(BASE_PATH, 'data/app.log')# app.log
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', encoding='utf-8') as file:
                file.write(self.log_path)
        self.stats_path = os.path.join(BASE_PATH, 'data/stats.json') # stats.json
        if not os.path.exists(self.stats_path):
            with open(self.stats_path, 'w', encoding='utf-8') as file:
                json.dump({}, file, indent=4, ensure_ascii=False)
    def _validate_files(self):
        try:
            paths = [self.list_path, self.whitelist_path, self.icon_path, self.mp3_path, self.log_path, self.stats_path]
            missing_files = [p for p in paths if not os.path.exists(p)]
            if missing_files:
                for f in missing_files:
                    self._log_success('_validate_files', f'File {f} not found')
            else:
                self._log_success('_validate_files', 'All needed files found')
        except Exception as e:
            self._log_error('_validate_files', f'Unexpectable {e}')
    def _init_stats(self):
        with open(self.stats_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if not data:
                self._log_error('_init_stats', 'stats.json is empty')
                self.stats = {
                    'total_checks': 0,
                    'total_kills': 0,
                    'total_errors': 0,
                    'start_time': time.time()
                }
            else:
                self._log_success('_init_stats', f'stats.json has got info: {data}')
                self.stats = data
        # self.stats = {
        #     'total_checks': 0,
        #     'total_kills': 0,
        #     'total_errors': 0,
        #     'start_time': time.time()
        # }

    # ==== Loading data methods ====
    def _load_processes_from_list(self):
        try:
            with open(self.list_path, 'r', encoding='utf-8') as file:
                data  = file.read().split()
            data_dict = {}
            for i in data:
                result = self._parse_process_line(i)
                if result:
                    data_dict.update(result)
            if not data_dict:
                self._log_error('_load_processes_from_file', 'list.txt is empty or has got incorrect format data')
                return {}
            self.running = True
            self._log_success('_load_processes_from_list', f'Processes: {data_dict}')
            return data_dict
        except FileNotFoundError:
            self._log_error('_load_processes_from_file', 'list.txt not found')
        except Exception as e:
            self._log_error('_load_processes_from_file', f'Unexpectable {e}')
    def _load_whitelist_processes(self):
        try:
            with open(self.whitelist_path, 'r', encoding='utf-8') as file:
                old_data = file.read().split()
            if not old_data:
                self._log_error('_load_whitelist_processes', 'Whitelist.txt is empty')
            new_data = []
            for proc_name in old_data:
                _, _, extension = proc_name.partition('.')  
                if extension not in PROCESS_EXTENSIONS:
                    self._log_error('_load_whitelist_processes', f'Uncorrect process format - {proc_name}')
                    continue
                new_data.append(proc_name)
            self._log_success('_load_whitelist_processes', f'White processes: {new_data}')
            return new_data
        except Exception as e:
            self._log_error('_load_whitelist_processes', f'Unexpectable {e}')
    def _parse_process_line(self, line):
        if ':' not in line:
            self._log_success('_parse_process_line', f'Skip incorrect format: {line}')
            return None
        
        process, message = line.split(':', 1)
        message = message.replace('_', ' ')

        return {process: message} if self._validate_process_data(process, message) else None
    def _validate_process_data(self, process, message):
        if not process or not message:
            self._log_error('_validate_process_data', f'Uncorrect process data: {process}, {message}')
            return False
        return True

    # ==== Works with processes methods ====
    def _get_running_processes(self):
        return psutil.process_iter(['name', 'pid'])
    def _check_single_process(self, proc):
        try:
            proc_name = proc.info['name']
            if proc_name in self.processes.keys():
                if proc_name in self.whitelist:
                    self._log_error('_check_single_process', f'The proc. {proc_name} is in whilelist.txt and it will not be stopped')
                    return
                if self._is_process_running(proc):
                    self._kill_process(proc)
                    self._notify_user(self.processes[proc_name], proc_name)
        except Exception as e:
            self._log_error('_check_single_process', f'Unexpectable {e}')
    def _kill_process(self, proc):
        try:
            proc.kill()
            self.stats['total_kills'] += 1
            self._log_success('_kill_process', f'Process {proc.info['name']} (PID:{proc.info['pid']}) has been stoped')
        except Exception as e:
            self._log_error('_kill_process', f'Unexpectable {e}')
    def _is_process_running(self, proc):
        try:
            return True if proc.is_running() else False
        except Exception as e:
            self._log_error('_is_process_running', f'Unexpectable: {e}')
            return False
    
    # ==== Notification methods ====
    def _notify_user(self, message, proc_name):
        try:
            if self._should_notify(proc_name):
                #liblary - winotify.Notification
                toast = Notification(app_id='Process_Killer',
                                     title=f'{proc_name} has been stoped',
                                     msg=message,
                                     icon=self.icon_path,
                                     duration='short')
                toast.show()
                self._log_success('_notify_user', 'message has been displayed')
                self.last_notification = {'proc_name': proc_name, 'time': time.time()}
                threading.Thread(target=self._play_notification_sound, daemon=True).start()
                #Library - plyer.notification
                # notification.notify(
                #     title='Magic programm',
                #     message=message,
                #     app_icon=self.icon_path,
                #     app_name='Process Killer',
                #     timeout=3
                # )
        except Exception as e:
            self._log_error('_notify_user', f'Unexpectable: {e}')
    def _play_notification_sound(self):
        try:
            if os.path.exists(self.mp3_path):
                playsound(self.mp3_path, block=False)
            else:
                self._log_error('_play_notification_sound', 'Sound file not found')
        except Exception as e:
            self._log_error('_play_notification_sound', f'Unexpectable: {e}')
    def _should_notify(self, proc_name):
        if self.last_notification:
            cur_time = time.time()
            if proc_name == self.last_notification['proc_name']:
                if cur_time - self.last_notification['time'] < self.anti_spam_time:
                    self._log_success('_should_notify', 'Notification will be not displayed - Anti spam')
                    return False
        self._log_success('_should_notify', 'Notification will be displayed - Anti spam')
        return True

    # ==== Logging methods ====
    #Simplify works with logging
    def _log_success(self, func_name: str, msg: str=None):
        logging.info(f'Success - ({func_name}): {msg if msg else 'No message'}')
    def _log_error(self, func_name: str, message: str):
        logging.error(f'Error - {func_name}: {message}')
        if self.stats:
            self.stats['total_errors'] += 1
    def _log_stats(self):
        s = self.stats
        logging.info(f"""Stats:
                     === Total checks - {s['total_checks']},
                     === Total kills - {s['total_kills']},
                     === Total errors - {s['total_errors']}
                     === Work's time{time.time() - s['start_time']:.2f}""")
        

    # ==== Main methods ====
    def main(self, stats_auto: bool=False):
        # PARAMS:
        # stats_auto: bool - auto-output stats of programs's work
        processes = self._get_running_processes()
        for proc in processes:
            self._check_single_process(proc)
        self.stats['total_checks'] += 1
        if stats_auto:
            if self.log_stats_count == 2:
                self._log_stats()
                self.log_stats_count = 0
                self.reload_config()
                self.write_stats_json()
            else:
                self.log_stats_count += 1
    def stop(self):
        if self.running:
            self.running = not self.running
            logging.info('The programm will be stoped')
    def reload_config(self, show_processes: bool=False):
        # PARAMS:
        # show_processes: bool - show new processes when calling a func
        if self.running:
            logging.info('Reloading config file...')
            new_processes = self._load_processes_from_list()
            if new_processes:
                self.processes = new_processes
                self._log_success('_reload_config', 'Reloading has been ended')
                self._log_success('_reload_config', f'Processes: {self.processes}') if show_processes else None
    def write_stats_json(self):
        with open(self.stats_path, 'w', encoding='utf-8') as file:
            json.dump(self.stats, file, indent=4, ensure_ascii=False)

#Config dataclass
@dataclass
class Config:
    #Paths
    LIST_PATH: str = list_path
    WHITELIST_PATH: str = whilelist_path
    ICON_PATH: str = icon_path
    MP3_PATH: str = mp3_path
    LOG_PATH: str = log_path
    #Sleep time
    CHECKER_SLEEP_TIME: int = 3
    ANTI_SPAM_TIME: int = 5

if __name__ == '__main__':
    run_logging()
    config = Config(list_path, whilelist_path,icon_path, mp3_path, log_path)
    killer = Process_Killer(config)
    try:
        while killer.running:
            killer.main(stats_auto=True)
            sleep_time = config.CHECKER_SLEEP_TIME
            time.sleep(sleep_time)
    except Exception as e:
        logging.error(f'Unexpectable error main "while" cycle: {e}')