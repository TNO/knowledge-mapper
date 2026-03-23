class BaseAuth:
    def has_permission(self, kb_id, ki):
        raise NotImplementedError("Please implement this abstract method.")
    
    def add_knowledge_interaction(self, ki):
        """Called when a Knowledge Interaction is added to this Knowledge Mapper"""
        pass
