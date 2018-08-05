from confluent_kafka import Producer
import sys
import time
import json
import random
import datetime

events_dict = {}
next_message_per_id = {}


def on_delivery(err, msg):
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))


def generate_message(event):
    msg = {
        'id': event['id'],
        'tz': event['tz'],
        'dateutc': event['dateutc'],
        'latitude': event['lat'],
        'longitude': event['lon'],
        'temperature': event['tempf_avg'],
        'baromin': event['baromin_first'],
        'humidity': event['humidity_avg'],
        'rainin': event['rainin']
    }
    return msg


def load_events_data():
    events_json_file = open('data/events.json')
    events_json_str = events_json_file.read()
    events = json.loads(events_json_str)

    for event in events:
        msg = generate_message(event)
        if msg['id'] in events_dict:
            events_dict[msg['id']].append(msg)
        else:
            events_dict[msg['id']] = [msg]
            next_message_per_id[msg['id']] = 0


def get_next_message():
    # choose random id
    id, msg_array = random.choice(list(events_dict.items()))
    next_for_id = next_message_per_id[id]
    msg = msg_array[next_for_id]
    msg['time_stamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    next_message_per_id[id] += 1
    if next_message_per_id[id] == len(msg_array):
        next_message_per_id[id] = 0
    return msg


def main():
    mh_creds = {
        # PASTE_MH_CREDENTIALS_HERE
    }

    topic = "dataHistorianStarterkitSampleData"

    if any(k not in mh_creds for k in ('kafka_brokers_sasl', 'user', 'password')):
        print('Error - missing credentials attributes.')
        sys.exit(-1)

    driver_options = {
        'bootstrap.servers': ','.join(mh_creds['kafka_brokers_sasl']),
        'security.protocol': 'SASL_SSL',
        'sasl.mechanisms': 'PLAIN',
        'sasl.username': mh_creds['user'],
        'sasl.password': mh_creds['password'],
        'api.version.request': True,
        'log.connection.close': False,
        'client.id': 'kafka-python-dh-producer'
    }

    producer = Producer(driver_options)

    # load sample data
    load_events_data()

    while True:
        message = get_next_message()
        sleep = 0.05
        try:
            producer.produce(topic, json.dumps(message), callback=on_delivery)
            # Trigger delivery callbacks from previous produce() calls
            producer.poll(0)
        except Exception as err:
            print('Failed sending message {0}'.format(message))
            print(err)
            sleep = 5  # Longer sleep before retrying
        time.sleep(sleep)


if __name__ == '__main__':
    main()
