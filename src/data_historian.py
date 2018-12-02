import datetime
import json
from tuple_to_csv import TupleToCsv
from streamsx.topology import context
from streamsx.topology.topology import Topology
import streamsx.messagehub as messagehub
import streamsx.spl.op as op
from streamsx.topology.schema import *
from streamsx.topology import schema
import streamsx.objectstorage as cos


def load_vcap_json():
    vcap_file = open('../vcap.json')
    vcap_str = vcap_file.read()
    vcap_json = json.loads(vcap_str)
    return vcap_json


def build_streams_config(vcap_json):
    sa_instance = vcap_json['streaming-analytics'][0]
    config = {
        context.ConfigParams.SERVICE_DEFINITION: sa_instance['credentials'],
        context.ConfigParams.FORCE_REMOTE_BUILD: True
    }
    return config


def add_1min_aggregate(stream):
    # calling batch to declare a window containing any tuples that arrived in the last minute
    win = stream.batch(datetime.timedelta(minutes=1))
    agg_output_schema = schema.StreamSchema("tuple <rstring id,rstring tz,rstring dateutc,rstring time_stamp,"
                                            "float64 longitude,float64 latitude,float64 temperature_std1,"
                                            "float64 baromin_min1,float64 humidity_max1,float64 rainin_avg1>")
    agg = op.Map('spl.relational::Aggregate', win, schema=agg_output_schema, params={'groupBy': 'id'},
                 name="Aggregate_1_minute")
    agg.id = agg.output('Any(id)')
    agg.tz = agg.output('Any(tz)')
    agg.dateutc = agg.output('Any(dateutc)')
    agg.time_stamp = agg.output('Any(time_stamp)')
    agg.longitude = agg.output('Any(longitude)')
    agg.latitude = agg.output('Any(latitude)')
    agg.temperature_std1 = agg.output('PopulationStdDev(temperature)')
    agg.baromin_min1 = agg.output('Min(baromin)')
    agg.humidity_max1 = agg.output('Max(humidity)')
    agg.rainin_avg1 = agg.output('Average(rainin)')
    return agg


def add_3min_aggregate(stream):
    # calling batch to declare a window containing any tuples that arrived in the last 3 minutes
    win = stream.batch(datetime.timedelta(minutes=3))
    agg_output_schema = schema.StreamSchema("tuple <rstring id,rstring tz,rstring dateutc,rstring time_stamp,"
                                            "float64 longitude,float64 latitude,float64 temperature_std2,"
                                            "float64 baromin_min2,float64 humidity_max2,float64 rainin_avg2>")
    agg = op.Map('spl.relational::Aggregate', win, schema=agg_output_schema, params={'groupBy': 'id'},
                 name="Aggregate_3_minutes")
    agg.id = agg.output('Any(id)')
    agg.tz = agg.output('Any(tz)')
    agg.dateutc = agg.output('Any(dateutc)')
    agg.time_stamp = agg.output('Any(time_stamp)')
    agg.longitude = agg.output('Any(longitude)')
    agg.latitude = agg.output('Any(latitude)')
    agg.temperature_std2 = agg.output('PopulationStdDev(temperature_std1)')
    agg.baromin_min2 = agg.output('Min(baromin_min1)')
    agg.humidity_max2 = agg.output('Max(humidity_max1)')
    agg.rainin_avg2 = agg.output('Average(rainin_avg1)')
    return agg


def main():
    vcap_json = load_vcap_json()
    cos_config = vcap_json['cos']
    mh_config = vcap_json['messagehub']
    streams_conf = build_streams_config(vcap_json)

    topology = Topology("data_historian")

    # subscribe returns Stream object
    source = messagehub.subscribe(topology, schema=CommonSchema.Json, topic='dataHistorianStarterkitSampleData',
                                  credentials=mh_config)

    # define the message hub tuples schema
    incoming_schema = schema.StreamSchema("tuple <rstring id,rstring tz,rstring dateutc,rstring time_stamp,"
                                          "float64 longitude,float64 latitude,float64 temperature,float64 baromin,"
                                          "float64 humidity,float64 rainin>")
    source = source.map(lambda x: x, schema=incoming_schema)

    agg1 = add_1min_aggregate(source)
    agg2 = add_3min_aggregate(agg1.stream)

    # transform the stream of tuples to a stream of csv lines
    csv_order = ["id", "tz", "dateutc", "time_stamp", "longitude", "latitude", "temperature_std2", "baromin_min2",
                 "humidity_max2", "rainin_avg2"]
    csv_stream = agg2.stream.map(TupleToCsv(csv_order), schema=CommonSchema.String)

    # write the stream to COS
    cos.write(csv_stream, endpoint=cos_config["endpoint"], bucket=cos_config["bucket"],
              objectName='datahistorian_%TIME.csv', timePerObject=45.0, credentials=cos_config)

    # submit
    context.submit(context.ContextTypes.STREAMING_ANALYTICS_SERVICE, topology, config=streams_conf)


if __name__ == '__main__':
    main()
