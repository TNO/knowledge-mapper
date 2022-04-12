import logging as log
import mysql.connector
import time

MAX_CONNECTION_ATTEMPTS = 10
WAIT_BEFORE_RETRY = 2

class SqlAuth:
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connect()

    def connect(self, max_attempts=MAX_CONNECTION_ATTEMPTS, wait_between_attempts=WAIT_BEFORE_RETRY):
        success = False
        attempts = 0
        while not success:
            try:
                log.info(f'Attempting SQL connection to {self.database} in {self.host}:{self.port} for SQL auth...')
                self.conn = mysql.connector.connect(
                    user=self.user,
                    password=self.password,
                    host=self.host,
                    port=self.port,
                    database=self.database
                )
                self.ping()
                success = True
            except Exception as e:
                attempts += 1
                if attempts < MAX_CONNECTION_ATTEMPTS:
                    log.warning(f'SQL connection attempt to {self.database} in {self.host}:{self.port} failed. Retrying in {WAIT_BEFORE_RETRY} s.')
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
                    log.error(f'Failed to establish SQL connection.')
                    raise e
        log.info('Successfully made SQL connection for SQL auth.')
    
    def ping(self):
        self.conn.ping()

    def has_permission(self, kb_id, ki):
        cursor = self.conn.cursor(named_tuple=True)
        cursor.execute('SELECT COUNT(*) > 0 AS permission FROM rules WHERE knowledge_interaction_id=%s AND (knowledge_base_id=%s OR knowledge_base_id IS NULL);', (ki['id'], kb_id))
        row = cursor.fetchone()
        if row is None:
            raise Exception('Expected a row in the result set.')
        cursor.close()
        self.conn.commit()
        return row.permission
    
    def add_knowledge_interaction(self, ki):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO knowledge_interactions (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name=%s;', (ki['id'], ki['name'], ki['name']))
        self.conn.commit()
