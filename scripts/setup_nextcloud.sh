#!/bin/bash

# URL-encode function
urlencode() {
  local string="${1}"
  local strlen=${#string}
  local encoded=""
  local pos c o

  for (( pos=0 ; pos<strlen ; pos++ )); do
     c=${string:$pos:1}
     case "$c" in
        [-_.~a-zA-Z0-9] ) o="${c}" ;;
        * )               printf -v o '%%%02x' "'$c"
     esac
     encoded+="${o}"
  done
  echo "${encoded}"
}

# Prepare the data
data="install=true"
data+="&adminlogin=$(urlencode "admin")"
data+="&adminpass=$(urlencode "admin")"
data+="&directory=$(urlencode "/var/www/html/data")"
data+="&dbtype=$(urlencode "sqlite")"
data+="&dbuser="
data+="&dbpass="
data+="&dbpass-clone="
data+="&dbname="
data+="&dbhost=$(urlencode "localhost")"

# Send the POST request
response=$(curl -s -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "$data" \
  http://localhost:8080)

# Print the response
echo "Response:"
echo "$response"

# Optional: Check the HTTP status code
status_code=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "$data" \
  http://localhost:8080)

echo "Status Code: $status_code"
