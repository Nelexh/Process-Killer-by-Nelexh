import psutil
from plyer import notification
import time
from playsound3 import playsound
import logging
import threading
import os
from dataclasses import dataclass

# Paths
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(BASE_PATH, 'data/notification.ico')
mp3_path = os.path.join(BASE_PATH, 'data/sound.mp3')
list_path = os.path.join(BASE_PATH, 'data/list.txt')

#Main class
class Process_Killer:
    # Initialization
    def __init__(self, config):
        self.running = False
        self.icon_path = config.ICON_PATH
        self.mp3_path = config.MP3_PATH
        self.list_path = config.LIST_PATH
        self.processes = self.init_processes()

        print(self.processes)

    #Processes initializatiopn(from txt file)
    def init_processes(self):
        try:
            with open(self.list_path, 'r', encoding='utf-8') as file:
                data  = file.read().split()

            data_dict = {}
            for i in data:
                if ':' not in i:
                    logging.warning(f'Skip incorrect format: {i}')
                    continue
                process, message = i.split(':', 1)
                data_dict[process] = message.replace('_', ' ')

            if not data_dict:
                logging.error('list.txt is empty or has got incorrect format data')
                return {}

            self.running = True
            return data_dict
        
        except FileNotFoundError:
            logging.error('list.txt not found')

        except Exception as e:
            logging.error(f'Unexpectable error in init_processes: {e}')

    # notification for user
    def show_notification(self, message):
        try:
            notification.notify(
                title='Magic programm',
                message=message,
                app_icon=self.icon_path
            )
            threading.Thread(target=self.play_sound, daemon=True).start()
        except Exception as e:
            logging.error(f'Unexpectable error in notification: {e}')

    # Play sound for user
    def play_sound(self):
        if os.path.exists(mp3_path):
            playsound(self.mp3_path, block=False)
        else:
            logging.error(f'Sound file not found')

    # main_killer function
    def main_killer(self):
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                proc_name = proc.info['name']

                if proc_name in self.processes.keys():
                    if proc.is_running():
                        proc.kill()
                        logging.info(f'Process {proc_name}(PID:{proc.info['pid']})has been stoped')
                        self.show_notification(message=self.processes[proc_name])          
                        time.sleep(5)

            except Exception as e:
                logging.error(f'Unexpectable Error in main_killer(): {e}')

#Config for programm
@dataclass
class Config:
    #Paths
    LIST_PATH: str = list_path
    ICON_PATH: str = icon_path
    MP3_PATH: str = mp3_path
    #Sleep time
    CHECKER_SLEEP_TIME: int = 3

    #Files validation
    def __post_init__(self):
        # warned about missing if it not found
        logging.info('Loading configuration of program...')

        paths = [self.LIST_PATH, self.ICON_PATH, self.MP3_PATH]

        missing_files = [p for p in paths if not os.path.exists(p)]
        if missing_files:
            for f in missing_files:
                logging.warning(f'File {f} not found')
        else:
            logging.warning('All needed file are founded')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    config = Config(list_path, icon_path, mp3_path)
    killer = Process_Killer(config)

    try:
        while killer.running:
            killer.main_killer()
            time.sleep(2)
    except Exception as e:
        logging.error(f'Unexpectable error main "while" cycle: {e}')