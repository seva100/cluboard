def unflatten_list(nested_list):
    unflattened = []
    group_inds = []

    if nested_list:
        group_inds.append(0)
    
    for el in nested_list:
        unflattened.extend(el)
        group_inds.append(group_inds[-1] + len(el))
    
    return unflattened, group_inds


def match_server_names_to_aliases(names, aliases):
    match = dict()
    for i in range(len(names)):
        for j in range(len(names[i])):
            if (isinstance(aliases, list) 
                and i < len(aliases) and j < len(aliases[i]) 
                and isinstance(aliases[i][j], str)):
                match[names[i][j]] = aliases[i][j]
            else:
                match[names[i][j]] = names[i][j]
    return match
