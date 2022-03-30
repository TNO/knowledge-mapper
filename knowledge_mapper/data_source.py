from knowledge_mapper.knowledge_base import KnowledgeBase

class DataSource:
    def test(self):
        raise NotImplementedError("Please implement this abstract method.")
    def handle(self, ki, binding_set, requesting_kb):
        raise NotImplementedError("Please implement this abstract method.")
    
    def set_knowledge_base(self, kb: KnowledgeBase):
        self.kb = kb
