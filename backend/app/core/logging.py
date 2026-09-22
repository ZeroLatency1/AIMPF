import json, logging, sys
class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'level':record.levelname,'logger':record.name,'message':record.getMessage(),'timestamp':self.formatTime(record),'service':'AIMPF'})
def configure_logging():
    handler=logging.StreamHandler(sys.stdout);handler.setFormatter(JsonFormatter());root=logging.getLogger();root.handlers.clear();root.addHandler(handler);root.setLevel(logging.INFO)
