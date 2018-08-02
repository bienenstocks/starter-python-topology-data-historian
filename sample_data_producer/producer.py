from confluent_kafka import Producer
import sys
import time
import json
import random
import datetime

events_dict = {}
curr_state_map = {}


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
            curr_state_map[msg['id']] = 0


def get_next_message():
    id, msg_array = random.choice(list(events_dict.items()))
    next_for_id = curr_state_map[id]
    msg = msg_array[next_for_id]
    msg['time_stamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    curr_state_map[id] = curr_state_map[id] + 1
    if curr_state_map[id] == len(msg_array):
        curr_state_map[id] = 0
    return msg


def main():
    mh_creds = {
        "api_key": "t_J0_K-pHHCapto8oTC2mjjZMFoIBc6BNxz-0CkYUKKZ",
        "apikey": "t_J0_K-pHHCapto8oTC2mjjZMFoIBc6BNxz-0CkYUKKZ",
        "iam_apikey_description": "Auto generated apikey during resource-key operation for Instance - crn:v1:bluemix:public:messagehub:us-south:a/f730dc759b4c3f320e480cec27def0d9:c7a58adb-96a2-4d4a-9ee4-0b8c949650cd::",
        "iam_apikey_name": "auto-generated-apikey-11aad236-9181-4777-b89d-41590ddd784d",
        "iam_role_crn": "crn:v1:bluemix:public:iam::::serviceRole:Manager",
        "iam_serviceid_crn": "crn:v1:bluemix:public:iam-identity::a/f730dc759b4c3f320e480cec27def0d9::serviceid:ServiceId-27773766-78ae-43aa-867a-02d9f9ccc24d",
        "instance_id": "c7a58adb-96a2-4d4a-9ee4-0b8c949650cd",
        "kafka_admin_url": "https://mh-toysgwbjqxesretuwazhfjw.us-south.containers.appdomain.cloud",
        "kafka_brokers_sasl": [
            "kafka-0.mh-toysgwbjqxesretuwazhfjw.us-south.containers.appdomain.cloud:9093",
            "kafka-1.mh-toysgwbjqxesretuwazhfjw.us-south.containers.appdomain.cloud:9093",
            "kafka-2.mh-toysgwbjqxesretuwazhfjw.us-south.containers.appdomain.cloud:9093"
        ],
        "password": "t_J0_K-pHHCapto8oTC2mjjZMFoIBc6BNxz-0CkYUKKZ",
        "user": "token"
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
