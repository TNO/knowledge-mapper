USE knowledge_mapper_db;

CREATE TABLE knowledge_interactions (
  id VARCHAR(512) NOT NULL,
  name VARCHAR(512),
  PRIMARY KEY(id)
);

CREATE TABLE policies (
  id INT NOT NULL AUTO_INCREMENT,
  knowledge_interaction_id VARCHAR(512),
  knowledge_base_id VARCHAR(512),
  PRIMARY KEY(id),
  FOREIGN KEY (knowledge_interaction_id) REFERENCES knowledge_interactions(id)
);
