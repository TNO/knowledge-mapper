import logging as log

from knowledge_mapper.auth.base_auth import BaseAuth

class StaticAuth(BaseAuth):
    def __init__(self, _conf):
        pass

    def has_permission(self, kb_id, ki):
        if 'permitted' in ki:
            if ki['permitted'] != "*":
                # check whether the requesting kb is in the permitted list                      
                if kb_id in ki['permitted']:
                    permission = True
                else:
                    log.info('Knowledge base %s is not permitted to do this request!', kb_id)
            else: # permission is set to *, so every one is permitted
                permission = True
        else:
            permission = False
        return permission
