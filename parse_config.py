import os
import yaml
from pprint import pprint


def read_config(config_fn):
    if not os.path.exists(config_fn):
        raise Exception(f'config file {config_fn} does not exist')

    with open(config_fn, 'r') as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(f'Something is wrong with the provided config: {config_fn}. See YAML exception below.')
            print(exc)
            exit()
    return config


def get_default(params_dict, key, default_value=None, exception_msg=None):
    """If key is present in params_dict, returns params_dict[key].
    Otherwise, if default_value is not None, returns default_value.
    Otherwise, return exception with specified exception message exception_msg."""
    
    key_fields = key.split('/')
    val = params_dict
    field_present = True
    for key in key_fields:
        if key in val:
            val = val[key]
        else:
            field_present = False
            break
    if field_present:
        return val

    if default_value is not None:
        return default_value
    raise Exception(exception_msg)


def parse_config(config_filename, default_config_filename=None):
    config = read_config(config_filename)
    # print('Launch configuration:')
    # pprint(config)

    if default_config_filename is not None:
        default_config = read_config(default_config_filename)
    
        config['server_names'] = get_default(
            config, 'server_names', None, 'server_names not defined'
        )

        config['print_lab_names'] = get_default(
            config, 'lab_names/show', default_config['lab_names']['show']
        )
        if config['print_lab_names']:
            config['lab_names'] = get_default(
                config, 'lab_names/lab_names', None, 'lab_names not defined, but print_lab_names set to True'
            )
        else:
            config['lab_names'] = None
        
        config['print_top_utilizing_users'] = get_default(
            config, 'top_utilizing_users/show', default_config['top_utilizing_users']['show']
        )    # how many top users by GPU utilization to show.
        if config['print_top_utilizing_users']:
            config['n_top_users_to_show'] = get_default(
                config, 'top_utilizing_users/n_top_users_to_show', default_config['top_utilizing_users']['n_top_users_to_show']
            )    # how many top users by GPU utilization to show.
            config['critical_number_of_gpus'] = get_default(
                config, 'top_utilizing_users/critical_number_of_gpus', default_config['top_utilizing_users']['critical_number_of_gpus']
            )    # if user consumes at least critical_number_of_gpus GPUs,
                                                                                            # his record will be marked red and bold.
        config['print_lab_distribution'] = get_default(
            config, 'lab_distribution/show', default_config['lab_distribution']['show']
        )
        
        config['additional_stats_to_show'] = get_default(
            config, 'additional_stats_to_show', default_config['additional_stats_to_show']
        )
    
    return config
