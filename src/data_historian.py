import datetime
import os
import json
import tuple_to_csv
from streamsx.topology import context
from streamsx.topology.topology import Topology
import streamsx.messagehub as messagehub
import streamsx.spl.op as op
from streamsx.topology.schema import *
from streamsx.topology import schema


def build_streams_config(service_name, credentials):
    vcap_conf = {
        'streaming-analytics': [
            {
                'name': service_name,
                'credentials': credentials,
            }
        ]
    }

    config = {
        context.ConfigParams.VCAP_SERVICES: vcap_conf,
        context.ConfigParams.SERVICE_NAME: service_name,
        context.ConfigParams.FORCE_REMOTE_BUILD: True,
    }
    return config


def add_first_aggregate(stream):
    # calling last to declare a window containing any tuples that arrived in the last X minutes
    win = stream.last(datetime.timedelta(minutes=1))
    agg_output_schema = schema.StreamSchema("tuple <rstring id,rstring tz,rstring dateutc,rstring time_stamp,"
                                            "float64 longitude,float64 latitude,float64 temperature_std1,"
                                            "float64 baromin_min1,float64 humidity_max1,float64 rainin_avg1>")
    agg = op.Map('spl.relational::Aggregate', win, schema=agg_output_schema)
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


def add_second_aggregate(stream):
    # calling last to declare a window containing any tuples that arrived in the last X minutes
    win = stream.last(datetime.timedelta(minutes=3))
    agg_output_schema = schema.StreamSchema("tuple <rstring id,rstring tz,rstring dateutc,rstring time_stamp,"
                                            "float64 longitude,float64 latitude,float64 temperature_std2,"
                                            "float64 baromin_min2,float64 humidity_max2,float64 rainin_avg2>")
    agg = op.Map('spl.relational::Aggregate', win, schema=agg_output_schema)
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
    sa_creds_env = os.getenv('SA_CREDENTIALS', None)
    if sa_creds_env is None:
        print('Error - SA_CREDENTIALS environment variable is missing.')
        sys.exit(-1)
    sa_creds = json.loads(sa_creds_env)

    service_name = "streaming-analytics-container-hourly"  # TODO: get service name
    streams_conf = build_streams_config(service_name, sa_creds)

    topo = Topology("data_historian")

    # subscribe returns Stream object
    source = messagehub.subscribe(topo, schema=CommonSchema.Json, topic='dataHistorianStarterkitSampleData')

    incoming_schema = schema.StreamSchema("tuple <rstring id,rstring tz,rstring dateutc,rstring time_stamp,"
                                          "float64 longitude,float64 latitude,float64 temperature,float64 baromin,"
                                          "float64 humidity,float64 rainin>")
    source = source.map(lambda x: x, schema=incoming_schema)

    agg1 = add_first_aggregate(source)
    agg2 = add_second_aggregate(agg1.stream)

    # transform the stream of tuples to a stream of csv lines
    csv_order = ["id", "tz", "dateutc", "time_stamp", "longitude", "latitude", "temperature_std2", "baromin_min2",
                 "humidity_max2", "rainin_avg2"]
    csv_stream = agg2.stream.transform(tuple_to_csv.TupleToCsv(csv_order))

    # Termination of a Stream - write to COS
    # csv_stream.for_each(object_storage_sink.ObjectStorageSink(csv_order))

    # publish to MH until COS toolkit is ready
    string_stream = csv_stream.as_string()
    messagehub.publish(string_stream, topic='dataHistorianSampleDataOutput')

    # submit
    context.submit(context.ContextTypes.STREAMING_ANALYTICS_SERVICE, topo, config=streams_conf)


if __name__ == '__main__':
    main()
