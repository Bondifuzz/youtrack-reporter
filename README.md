# youtrack-integration

## Local development

To run this server locally you should run next commands:

* `cd local && docker-compose up -d` - run __ArangoDB__ and __SQS__ services.
* `./run_youtrack.sh` - run local instance of YouTrack. (At first you have to [pull docker image](https://hub.docker.com/r/jetbrains/youtrack/) and follow instructions on their docker hub page)
* `cd .. && python -m youtrack_reporter` - run main server

## Deploy

`docker build -t youtrack-reporter .` - build image

`docker run --net=host --rm -it --name=youtrack-reporter --env-file=.env youtrack-reporter bash` - run container

## Testing

* For testing an API of YouTrack Reporter Service you can use Postman. In Postman you can import file `local/openapi.json` and make some requests to the API
* `python -m local.{script_name}` - run script from "__./local__" directory, for example `python -m local.tests.yt_api` - testing of YouTrackAPI
* Also you can `cd local/tests/mq_producers` and run `python producer.py {config id}` - it will produce message to __"youtrack-reporter.crashes.duplicate"__ and __"youtrack-reporter.crashes.unique"__ chanels using config with specified id

