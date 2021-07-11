def unflatten_list(nested_list):
    unflattened = []
    group_inds = []

    if nested_list:
        group_inds.append(0)
    
    for el in nested_list:
        unflattened.extend(el)
        group_inds.append(group_inds[-1] + len(el))
    
    return unflattened, group_inds
