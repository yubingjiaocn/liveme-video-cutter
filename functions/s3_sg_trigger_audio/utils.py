def add_onlineTag_audio(source_raw):
    if '2' not in source_raw['online_tag']:
        source_raw['online_tag']['2'] = {}
    if '12' not in source_raw['online_tag']['2']:
        source_raw['online_tag']['2']['12'] = []
    if '4' not in source_raw['online_tag']['2']['12']:
        source_raw['online_tag']['2']['12'].append('4')
    return source_raw

def remove_onlineTag_audio(source_raw):
    try:
        source_raw['online_tag']['2']['12'].remove('4')
        if len(source_raw['online_tag']['2']['12']) == 0:
            source_raw['online_tag']['2'].pop('12', None)
        if not source_raw['online_tag']['2']:
            source_raw['online_tag'].pop('2', None)
    except:
        pass
    return source_raw