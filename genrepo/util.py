from eulcore.fedora.util import RequestFailed

def accessible(olist):
    '''Iterate through an input object list, and yield only those that exist
    and don't throw Fedora exceptions.'''
    for obj in olist:
        try:
            if obj.exists:
                yield obj
        except RequestFailed:
            pass
