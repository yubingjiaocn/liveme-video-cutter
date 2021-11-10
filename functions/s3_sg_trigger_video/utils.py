def add_onlineTag_dance(source_raw):
    if '3' not in source_raw['online_tag']:
        source_raw['online_tag']['3'] = {}
    if '17' not in source_raw['online_tag']['3']:
        source_raw['online_tag']['3']['17'] = []
    if '5' not in source_raw['online_tag']['3']['17']:
        source_raw['online_tag']['3']['17'].append('5')
    return source_raw


def remove_onlineTag_dance(source_raw):
    try:
        source_raw['online_tag']['3']['17'].remove('5')
        if len(source_raw['online_tag']['3']['17']) == 0:
            source_raw['online_tag']['3'].pop('17', None)
        if not source_raw['online_tag']['3']:
            source_raw['online_tag'].pop('3', None)
    except:
        pass
    return source_raw


