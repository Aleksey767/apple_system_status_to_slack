import json
import schedule
import time
import requests
from random import choice
import logging
import datetime

prev = None
counter = 0


def check_service_status():
    now = datetime.datetime.now()
    global counter
    print(counter, '. i am working', now)
    counter += 1
    logging.basicConfig(level=logging.INFO,
                        filename="py_log.log", filemode="w", format="%(asctime)s %(levelname)s %(message)s")
    desktop_agents = ['Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                      'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
                      'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
                      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
                      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
                      'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
                      'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                      'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0']

    def random_headers():
        return {'User-Agent': choice(desktop_agents), 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}

    URL_TEMPLATE = "https://www.apple.com/support/systemstatus/data/developer/system_status_en_US.js"
    r = requests.get(URL_TEMPLATE, headers=random_headers())

    text = r.text
    if "jsonCallback" in r.text:
        text = text.replace("jsonCallback", "", 1)
        text = text.replace('(', "")
        text = text.replace(')', "")
        text = text.replace(';', "")

    now = json.loads(text)
    global prev
    if prev is None:
        prev = now
        return

    def add_circle_to_status(word):
        if word == 'Available':
            new_word = ':large_green_circle:'
        elif word == 'Outage':
            new_word = ':red_circle:'
        elif word == 'Issue':
            new_word = ':large_yellow_circle:'
        elif word == 'Maintenance':
            new_word = ':wrench:'
        elif word == "Performance":
            new_word = ":large_blue_circle:"
        return new_word

    def send_message_slack(service_name, service_status, service_message):
        headers = {'Content-type': 'application/json', }
        json_data = {
            'text': f':mega:  Name: *{service_name} * \n:desktop_computer: Status: {service_status} {add_circle_to_status(service_status)} \n:email: Message: {service_message} '}
        requests.post('your_slack_hoock',
                      headers=headers, json=json_data,)
        return

    for index, key in enumerate(now["services"]):
        if key['events']:
            if len(prev['services'][index]['events']) == 0:  # Если раньше было пусто
                serv_stat = now['services'][index]['events'][0]['statusType']
                start = now['services'][index]['events'][0]['startDate']
                end = now['services'][index]['events'][0]['endDate']
                serv_name = now['services'][index]['serviceName']
                if now['services'][index]['events'][0]['eventStatus'] == 'upcoming':  # Если обслуживание
                    send_message_slack(
                        serv_name, serv_stat, f'Maintenance scheduled. Start at *{start}*, end at *{end}*')
                    logging.info('From 0 to Maintenance')
                else:
                    send_message_slack(
                        serv_name, serv_stat, f'Repair work on the server has been started *{start}*')
                    logging.info('From 0 to Issue or Outage')
                    print(now['services'][index]['events'][0]['eventStatus'])
            else:  # Если пусто не было

                for index2, key2 in enumerate(key['events']):
                    # считаем длину у было и стало
                    if len(prev['services'][index]['events']) == len(key['events']):
                        serv_stat = now['services'][index]['events'][index2]['statusType']
                        start = now['services'][index]['events'][index2]['startDate']
                        end = now['services'][index]['events'][index2]['endDate']
                        serv_name = now['services'][index]['serviceName']
                        # Если ongoing->resolved
                        if key2['eventStatus'] == 'resolved' and prev['services'][index]['events'][index2]['eventStatus'] != 'resolved':
                            send_message_slack(
                                serv_name, 'Available', f'Repair work completed *{end}*')
                            logging.info('Ongoing -> resolved')
                        if key2['eventStatus'] == 'ongoing' and prev['services'][index]['events'][index2]['eventStatus'] == 'resolved':
                            send_message_slack(
                                serv_name, serv_stat, f'Repair work on the server has been started *{start}*')
                            logging.info('Resolved->Ongoing')
                        if key2['eventStatus'] == 'upcoming' and prev['services'][index]['events'][index2]['eventStatus'] != 'upcoming':
                            send_message_slack(
                                serv_name, serv_stat, f'Maintenance scheduled. Start at *{start}*, end at *{end}*')
                            logging.info('Maintenance after somethink')
                    else:  # Если len now > len prev
                        if len(prev['services'][index]['events']) < len(key['events']):
                            if key2['eventStatus'] == 'upcoming' or key2['eventStatus'] == 'ongoing':
                                serv_stat = now['services'][index]['events'][index2]['statusType']
                                start = now['services'][index]['events'][index2]['startDate']
                                end = now['services'][index]['events'][index2]['endDate']
                                serv_name = now['services'][index]['serviceName']
                                if key2['eventStatus'] == 'upcoming':
                                    send_message_slack(
                                        serv_name, serv_stat, f'Maintenance scheduled. Start at *{start}*, end at *{end}*')
                                    logging.info('New maintenance')
                                else:
                                    send_message_slack(
                                        serv_name, serv_stat, f'Repair work on the server has been started *{start}*')
                                    print(key2['eventStatus'])
                                    logging.info('New ongoing')

    prev = now


check_service_status()
schedule.every(10).minutes.do(check_service_status)

while True:
    schedule.run_pending()
    time.sleep(1)
