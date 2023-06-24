from youtrack_reporter.app.database.orm import ORMConfig
import configparser

if __name__=='__main__':
    data = configparser.ConfigParser()
    data.read('local/example.ini')

    keys = [i for i in data['CONFIG']]
    vals = [data['CONFIG'][i] for i in data['CONFIG']]

    conf = ORMConfig(**(dict(zip(keys, vals))))
    
    print(conf.json())