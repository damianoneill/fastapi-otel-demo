#!/bin/bash

# Exit on error
set -e

# Default values
HOST="localhost"
PORT="8000"
DURATION=60
CONCURRENT_USERS=10
VERBOSE=false

# Help message
usage() {
    echo "Usage: $0 [-h <host>] [-p <port>] [-d <duration>] [-c <concurrent_users>] [-v]"
    echo "  -h  Host (default: localhost)"
    echo "  -p  Port (default: 8000)"
    echo "  -d  Duration in seconds (default: 60)"
    echo "  -c  Concurrent users (default: 10)"
    echo "  -v  Verbose output"
    exit 1
}

# Parse command line arguments
while getopts "h:p:d:c:v" opt; do
    case $opt in
        h) HOST=$OPTARG ;;
        p) PORT=$OPTARG ;;
        d) DURATION=$OPTARG ;;
        c) CONCURRENT_USERS=$OPTARG ;;
        v) VERBOSE=true ;;
        *) usage ;;
    esac
done

# Initialize counters
TOTAL_REQUESTS=0
SUCCESSFUL_REQUESTS=0
FAILED_REQUESTS=0

# Function to make requests
make_requests() {
    local user_id=$1
    local start_time=$2
    local my_requests=0
    local my_successful=0
    local my_failed=0

    while true; do
        current_time=$(date +%s)
        if [ $((current_time - start_time)) -ge $DURATION ]; then
            break
        fi

        # Random endpoint selection
        case $((RANDOM % 2)) in
            0) endpoint="/" ;;
            1) endpoint="/items/$((RANDOM % 100 + 1))" ;;
        esac

        # Make the request
        if $VERBOSE; then
            echo "User $user_id requesting: $endpoint"
        fi

        response=$(curl -s -w "\n%{http_code}" "http://$HOST:$PORT$endpoint")
        status_code=$(echo "$response" | tail -n1)
        my_requests=$((my_requests + 1))

        if [ "$status_code" = "200" ]; then
            my_successful=$((my_successful + 1))
        else
            my_failed=$((my_failed + 1))
            if $VERBOSE; then
                echo "Failed response: $response"
            fi
        fi

        if $VERBOSE; then
            echo "User $user_id received status: $status_code"
        fi

        # Random sleep between 0.1 and 1 second
        sleep 0.$(( (RANDOM % 9) + 1 ))
    done

    # Write results to temp files
    echo "$my_requests" > "/tmp/loadtest_total_$user_id"
    echo "$my_successful" > "/tmp/loadtest_success_$user_id"
    echo "$my_failed" > "/tmp/loadtest_failed_$user_id"
}

echo "Starting load test with $CONCURRENT_USERS concurrent users for $DURATION seconds"
echo "Target: http://$HOST:$PORT"
echo "Press Ctrl+C to stop"

# Record start time
START_TIME=$(date +%s)

# Clean up any existing temp files
rm -f /tmp/loadtest_* 2>/dev/null || true

# Start concurrent users
for i in $(seq 1 $CONCURRENT_USERS); do
    make_requests $i $START_TIME &
done

# Wait for all background processes to complete
wait

# Initialize result variables with defaults
TOTAL_REQUESTS=0
SUCCESSFUL_REQUESTS=0
FAILED_REQUESTS=0

# Aggregate results with error handling
for i in $(seq 1 $CONCURRENT_USERS); do
    if [ -f "/tmp/loadtest_total_$i" ]; then
        val=$(cat "/tmp/loadtest_total_$i")
        TOTAL_REQUESTS=$((TOTAL_REQUESTS + val))
    fi
    if [ -f "/tmp/loadtest_success_$i" ]; then
        val=$(cat "/tmp/loadtest_success_$i")
        SUCCESSFUL_REQUESTS=$((SUCCESSFUL_REQUESTS + val))
    fi
    if [ -f "/tmp/loadtest_failed_$i" ]; then
        val=$(cat "/tmp/loadtest_failed_$i")
        FAILED_REQUESTS=$((FAILED_REQUESTS + val))
    fi
done

# Clean up temp files
rm -f /tmp/loadtest_* 2>/dev/null || true

# Calculate results with error handling
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

if [ "$TOTAL_REQUESTS" -gt 0 ]; then
    REQUESTS_PER_SECOND=$(bc <<< "scale=2; $TOTAL_REQUESTS / $TOTAL_TIME")
    SUCCESS_RATE=$(bc <<< "scale=2; ($SUCCESSFUL_REQUESTS * 100) / $TOTAL_REQUESTS")
else
    REQUESTS_PER_SECOND="0.00"
    SUCCESS_RATE="0.00"
fi

# Print results
echo -e "\nLoad Test Results:"
echo "------------------------"
echo "Duration: $TOTAL_TIME seconds"
echo "Total Requests: $TOTAL_REQUESTS"
echo "Successful Requests: $SUCCESSFUL_REQUESTS"
echo "Failed Requests: $FAILED_REQUESTS"
echo "Requests per second: $REQUESTS_PER_SECOND"
echo "Success Rate: $SUCCESS_RATE%"