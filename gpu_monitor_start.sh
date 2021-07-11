# default values
port=8888
debug=0
config="config.yaml"

while true; do
  case $1 in
    -h|--help)
        echo "Usage: gpu_monitor_start [-h] [-p|--port <port>] [-d|--debug] [-c|--config]"
        shift 1;;
    -p|--port) port=$2;
        shift 2;;
    -d|--debug) debug=1;
        shift 1;;
    -c|--config) config=$2;
        shift 2;;
    *) break;;
  esac
done

MONITOR_CONFIG_FILE=$config FLASK_APP=main.py FLASK_DEBUG=$debug flask run --host=0.0.0.0 --port=$port
