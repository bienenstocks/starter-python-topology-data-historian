#!/bin/bash

echo "Install jq..."
wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64
chmod +x ./jq
cp jq /usr/bin

echo "Install IBM Cloud CLI..."
if ! [ -x "$(command -v bx)" ]; then
    curl -fsSL https://clis.ng.bluemix.net/install/linux | sh
fi

API_ENV=$(echo ${PIPELINE_API_URL} | sed -e 's/.*devops-\(.*\)\/.*\/.*/\1/')
bx login --apikey $PIPELINE_API_KEY -a $API_ENV
bx target --cf

# get Streaming analytics credentials
echo "Get Streaming Analytics Credentials..."
bx resource service-key-delete "SA_${APP_NAME}" -f
SA_KEY=$(bx resource service-key-create "SA_${APP_NAME}" Manager --instance-name "${SA_INSTANCE}")
API_KEY=$(echo ${SA_KEY} | awk 'BEGIN{FS="apikey: "} {print $2}' | awk '{ print $1 }')
if [ -z "$API_KEY" ]; then
   echo "Error generating Streaming Analytics credentials: ${SA_KEY}"
fi
echo "generating vcap.json"
echo "{
    \"streaming-analytics\":[{
        \"name\" : \"streaming-analytics\",
        \"credentials\" : {
            \"apikey\": \"${API_KEY}\",
            \"v2_rest_url\": \"$(echo ${SA_KEY} | awk 'BEGIN{FS="v2_rest_url: "} {print $2}' | awk '{ print $1 }')\"
        }
    }]" > vcap.json

# get COS credentials
if [ $COS_INSTANCE ]; then
    echo "Get Cloud Object Storage Credentials..."
    bx resource service-key-delete "COS_${APP_NAME}" -f
    COS_KEY=$(bx resource service-key-create "COS_${APP_NAME}" Manager --instance-name "${COS_INSTANCE}" --p {\"HMAC\":true})
    API_KEY=$(echo ${COS_KEY} | awk 'BEGIN{FS="apikey: "} {print $2}' | awk '{ print $1 }')
    if [ -z "$API_KEY" ]; then
     echo "Error generating COS credentials: ${COS_KEY}"
    fi
    token=$(curl -X "POST" "https://iam.bluemix.net/oidc/token" \
        -H 'Accept: application/json' \
        -H 'Content-Type: application/x-www-form-urlencoded' \
        --data-urlencode "apikey=${API_KEY}" \
        --data-urlencode "response_type=cloud_iam" \
        --data-urlencode "grant_type=urn:ibm:params:oauth:grant-type:apikey" | jq -r '.access_token')
    curl -X "PUT" "https://s3-api.us-geo.objectstorage.softlayer.net/${APP_NAME}" \
        -H "Authorization: Bearer ${token}" \
        -H "ibm-service-instance-id: $(echo ${COS_KEY} | awk 'BEGIN{FS="resource_instance_id: "} {print $2}' | awk '{ print $1 }')"
    echo ",
        \"cos\": {
            \"endpoint\": \"s3-api.us-geo.objectstorage.softlayer.net\",
            \"accessKeyId\": \"$(echo ${COS_KEY} | awk 'BEGIN{FS="access_key_id: "} {print $2}' | awk '{ print $1 }')\",
            \"secretKey\": \"$(echo ${COS_KEY} | awk 'BEGIN{FS="secret_access_key: "} {print $2}' | awk '{ print $1 }')\",
            \"bucket\": \"${APP_NAME}\",
            \"filePrefix\": \"prefix\"
        }" >> vcap.json
fi

# get MH credentials
if [ $MH_INSTANCE ] ; then
    echo "Get Cloud Object Storage Credentials..."
    # Get service instance guid of MH Instance to be used to get/create a service key
    bx cf curl /v2/service_instances?q=name:"${MH_INSTANCE}" --output mh_inst_out.json
    MH_GUID=$(cat mh_inst_out.json | jq -r '.resources[] | .metadata.guid')
    bx cf curl /v2/service_keys?q=name:"MH_${APP_NAME}" --output mh_key_out.json
    # If service key doesnt already exist, then create it.
    if [[ "$(cat mh_key_out.json | jq -r '.total_results')" -eq 0 ]]; then
        bx cf curl /v2/service_keys -d "{\"service_instance_guid\":\"${MH_GUID}\",\"name\":\"MH_${APP_NAME}\"}"
        bx cf curl /v2/service_keys?q=name:"MH_${APP_NAME}" --output mh_key_out.json
    fi

    brokers=$(cat mh_key_out.json | jq -r '.resources[] | .entity.credentials.kafka_brokers_sasl')
    brokersstrip=$(echo $brokers | tr -d '"' | tr -d '[' | tr -d ']')
    echo ",
          \"messagehub\": {
            \"user\": \"$(cat mh_key_out.json | jq -r '.resources[] | .entity.credentials.user')\",
            \"password\": \"$(cat mh_key_out.json | jq -r '.resources[] | .entity.credentials.password')\",
            \"kafka_brokers_sasl\": [\"${brokersstrip}\"]
          }" >> vcap.json
fi

echo "}" >> vcap.json
cat vcap.json

pip3 install -r requirements.txt 
python3 ./src/data_historian.py