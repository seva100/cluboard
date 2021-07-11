import os
import math
import re
from typing import ClassVar
from utils import match_server_names_to_aliases, unflatten_list
from functools import reduce
from collections import Counter
from flask import Flask, render_template, request
from flask import json
import paramiko

from interval import Interval
from parse_config import parse_config

# Initializing the app object.
app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.route("/")
def main():
    global intervals
    if intervals is None:
        intervals = [Interval(.5, save_machine_info, args=(i,))
                    for i in range(len(server_names))]
        for i in range(len(server_names)):
            if ssh_connections[i] is not None:
                intervals[i].start()
    
    n_rows = len(config['server_names'])
    n_cols = max([len(inner_list) for inner_list in config['server_names']])

    return render_template("index.html",
                           n_rows=n_rows,
                           n_cols=n_cols,
                           print_top_utilizing_users=config['top_utilizing_users']['show'],
                           print_lab_names=config['lab_names']['show'],
                           print_lab_distribution=config['lab_distribution']['show'],
                           lab_names=config['lab_names']['lab_names'],
                           lab_names_pane_width=config['lab_names']['pane_width'])     


def suppress_ssh_exception(function, *args, **kwargs):
    # while True:  # until no exception was raised
        try:
            result = function(*args, **kwargs)
        except paramiko.ssh_exception.ChannelException:
            pass
        except paramiko.ssh_exception.SSHException:
            pass
        except paramiko.ssh_exception.NoValidConnectionsError:
            pass
        else:
            return result


def get_user_gpu_stats(gpustat_output):
    gpustat_output = gpustat_output.split('\n')
    cntr = Counter()
    for line in gpustat_output:
        users_on_gpu = re.findall('([.\w]+)/\d+', line)
        users_on_gpu = list(set(users_on_gpu))
        for user in users_on_gpu:
            cntr[user] += 1
    del cntr['root']
    return cntr


def update_users_stats_overall():
    global latest_users_stats_overall
    latest_users_stats_overall = reduce(Counter.__add__, latest_users_stats)


def cmd_output_on_server(server_no, cmd):
    try:
        cur_data = ssh_connections[server_no].exec_command(cmd)[1] \
            .read().decode('utf-8')
    except paramiko.ssh_exception.ChannelException:
        print('paramiko.ssh_exception.ChannelException caught -- continuing')
        return
    cur_data = cur_data.strip()
    return cur_data


def get_additional_data(server_no, stat_type):
    # stat_type is one of {'cpu', 'ram', 'swap'}
    cmd = None
    if stat_type == 'cpu':
        cmd = r'''
            echo "CPU `LC_ALL=C top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}'`%"
            '''
    elif stat_type == 'ram':
        cmd = '''
            echo "RAM `free -m | awk '/Mem:/ { printf("%3.1f%%", $3/$2*100) }'`"
            '''
    elif stat_type == 'swap':
        cmd = '''
            echo "Swap `free -m | awk '/Swap:/ { printf("%3.1f%%", $3/(($2==0)?1:$2)*100) }'`"
            '''
    return cmd_output_on_server(server_no, cmd)


def get_gpustat_output(server_no):
    cmd = '''
    gpustat -p -P -u
    '''
    return cmd_output_on_server(server_no, cmd)


def save_machine_info(server_no):
    if ssh_connections[server_no] is None:
        return
    cur_data = get_gpustat_output(server_no)
    cur_data = cur_data.strip()
    latest_users_stats[server_no] = get_user_gpu_stats(cur_data)
    update_users_stats_overall()
    # occupied_gpus = acquire_gpus_occuiped_by_lsf(server_no)

    additional_stats = {stat_name: get_additional_data(server_no, stat_name)
                        for stat_name in config['additional_stats_to_show']}

    # setting some basic color
    cur_data = cur_data.split('\n')
    for i, line_raw in enumerate(cur_data):
        
        line_parts = line_raw.split(' ')
        line_parts = [part for part in line_parts if 'root' not in part or '5M' not in part]
        line = ' '.join(line_parts)

        if '|' not in line:
            line = line.split(' ')
            alias = names2aliases[line[0].strip()]
            line[0] = f'<b>{alias}</b>'
            cur_data[i] = ' '.join(line)
            for stat_name in config['additional_stats_to_show']:
                cur_data[i] += ' | ' + additional_stats[stat_name]
        else:
            if line.rstrip().endswith('|'):    # no gpu-consuming processes, but some LSF jobs allocated
                chosen_color = '777777'
                cur_data[i] = f'<span style="color: #{chosen_color}">{line}</span>'    # green
            else:    # there are some gpu-consuming processes 
                chosen_color = '8B0000'  # red
                cur_data[i] = f'<span style="color: #{chosen_color}">{line}</span>'
            if '%' in cur_data[i]:
                cur_data[i] = cur_data[i].split(' ')
                percent_idx = cur_data[i].index('%,')
                cur_data[i][percent_idx - 1] = f'<b>{cur_data[i][percent_idx - 1]}</b>'
                cur_data[i] = ' '.join(cur_data[i])

    cur_data = '\n'.join(cur_data)
    cur_data = f"<pre>{cur_data}</pre>"
    latest_gpustat[server_no] = cur_data


@app.route('/get_gpustat', methods=['POST'])
def get_gpustat():
    server_i = int(request.form['i']) 
    server_j = int(request.form['j']) 
    if (0 <= server_i < len(config['server_names']) 
        and 0 <= server_j < len(config['server_names'][server_i])):
        server_no = group_inds[server_i] + server_j
        data = {"text": latest_gpustat[server_no]}
    else:
        data = {"text": ""}
    
    return (json.dumps(data),
            200,
            {'Content-Type': 'application/json'})


@app.route('/get_top_users', methods=['POST'])
def get_top_users():
    list_with_top_users = latest_users_stats_overall.most_common(config['top_utilizing_users']['n_top_users_to_show'])
    # list_with_top_users = [f'{name} ({gpus_used})' for name, gpus_used in list_with_top_users]
    top_users_text = []
    for name, gpus_used in list_with_top_users:
        if gpus_used < config['top_utilizing_users']['critical_number_of_gpus']:
            top_users_text.append(f'{name} ({gpus_used})')
        else:
            top_users_text.append(f'<b>{name} <span style="color: #8B0000">({gpus_used})</span></b>')
    top_users_text = '\n'.join(top_users_text)
    data = {"text": top_users_text}
    return (json.dumps(data),
            200,
            {'Content-Type': 'application/json'})


if __name__ == "main":    # Proper test block for the Flask app 
                          # (corresponds to the basename of the "main.py" script)
    
    # Reading and processing configuration file.
    config_file = 'config.yaml'
    default_config_file = 'templates/default_config.yaml'

    if 'MONITOR_CONFIG_FILE' in os.environ:
        config_file = os.environ['MONITOR_CONFIG_FILE']
    
    config = parse_config(config_file)

    server_names, group_inds = unflatten_list(config['server_names'])
    names2aliases = match_server_names_to_aliases(config['server_names'], config['server_aliases'])

    # Opening SSH connections
    intervals = None
    ssh_connections = [None for i in range(len(server_names))]

    for i in range(len(server_names)):
        ssh_connections[i] = paramiko.SSHClient()
        ssh_connections[i].load_system_host_keys()
        # suppress_ssh_exception(ssh_connections[i].connect, config['server_names'][i], username=login_username)
        suppress_ssh_exception(ssh_connections[i].connect, server_names[i])
        print("Connection established with", names2aliases[server_names[i]])

    latest_gpustat = ["" for _ in server_names]
    latest_users_stats = [Counter() for _ in server_names]
    latest_users_stats_overall = Counter()

    # Starting the app
    app.run(host="0.0.0.0", port=8080)
