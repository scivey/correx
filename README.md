### an experiment in python log + db query correlation

This is a simple Python application testing out some ideas around logging and tracing.  It isn't a library, and it won't do anything useful for you out of the box.

This is mostly a response to some of the sticking points I've seen in an existing application based on Flask, Celery and psycopg2 (Postgres), and so a very similar stack is used here.  Some of the logging deficiencies described below may be particular to this stack, but the general ideas should be applicable anywhere.

So far, the coolest thing that this lets you do is correlate a given database query with the web request or Celery task that initiated it.

Instructions for running it are below.  Scroll down to the bottom for an explanation of the goals.



## installation + startup
From the repo root, run the dev-init script.  This initializes a virtualenv and installs pip requirements.
```bash
./scripts/dev-init.sh
```

The application has three moving parts, and each runs in the foreground by default.  The simplest way to run these is to just open multiple terminal tabs.

In the first terminal, run this to bring up the dockerized Postgres and Redis servers:
```bash
sudo docker-compose up
```

In the second, run this to start uWSGI+Flask:
```bash
# will listen on default port (9020)
./scripts/run-flask.sh

# if you aren't easygoing, you can specify the port yourself
./scripts/run-flask.sh 9027
```

And in the third, run this to start the Celery worker:
```bash
./scripts/run-celery.sh
```



## HTTP API
There are three endpoints.

### `/api/v1/inspect-db`
Returns a list of all queries currently running in Postgres, along with associated metadata.  For each query, metadata pulled directly from Postgres's `pg_catalog.pg_stat_activity` table is available under a "db_metadata" key.  Metadata injected by our application is under "app_metadata."

This endpoint is useless by itself -- it's here to let you observe the effects of the other two endpoints.


### `/api/v1/sleep-in-web?seconds={number}`
This endpoint sends a `pg_sleep` query to postgres, which will sleep for the given number of seconds (defaulting to 15).  This query is sent directly from the web server (uWSGI) to Postgres.


### `/api/v1/sleep-in-worker?seconds={number}`
This endpoint results in a call to `pg_sleep` just like `/api/v1/sleep-in-web`, but the query is made by a background Celery task instead of directly by the uWSGI request thread.  The uWSGI thread then blocks until the task finishes and returns a status object.


## testing it


### trace a flask->postgres query

Assuming the server is listening on port `9020`, make a GET to this endpoint:
```
http://localhost:9020/api/v1/sleep-in-web?seconds=20
```

While waiting for that request to return, make a GET to this endpoint:
```
http://localhost:9020/api/v1/inspect-db
```

The response will look like this, though UUIDs and timestamps will vary:
```json
{
  "flask_request_id": "j8FPsLnn3PKBAZEWKjCi5F", 
  "queries": [
    {
      "app_metadata": {
        "celery_task_id": null, 
        "client_pid": 16604, 
        "context_type": "FLASK", 
        "cursor_id": "jio2niZtXyUNELTMSTWnA7", 
        "flask_req_id": "4rtTDg8Fb6Kb29UTttwG9W", 
        "os_user": "ubuntu", 
        "pg_conn_id": "wNJ9pmSyWUmAiumKbsax7G"
      }, 
      "db_metadata": {
        "application_name": "", 
        "backend_start": "Tue, 21 Feb 2017 04:20:24 GMT", 
        "backend_xid": null, 
        "backend_xmin": "548", 
        "client_addr": "172.20.0.1", 
        "client_hostname": null, 
        "client_port": 53538, 
        "datid": 16384, 
        "datname": "correx_db", 
        "pid": 615, 
        "query_start": "Tue, 21 Feb 2017 04:20:24 GMT", 
        "state": "active", 
        "state_change": "Tue, 21 Feb 2017 04:20:24 GMT", 
        "usename": "correx_user", 
        "usesysid": 16385, 
        "wait_event": null, 
        "wait_event_type": null, 
        "xact_start": "Tue, 21 Feb 2017 04:20:24 GMT"
      }, 
      "query": "select * from pg_sleep(20)"
    }
  ]
}
```

Above, the `app_metadata` key contains all of the metadata injected by our Python application.  `db_metadata` contains values already found in the `pg_catalog.pg_stat_activity` table.

Things to note in `app_metadata`:
* `celery_task_id` is `null`, because this query didn't happen in a Celery task.
* `flask_req_id` is not null, because this *did* happen during a flask request.
* `client_pid` is the PID of the uWSGI worker that served the request.  (The `pid` key under `db_metadata` refers to the Postgres process handling the connection, not our client.)
* `pg_conn_id` is a unique ID that our Python code assigns to each new connection object it creates.  This makes it easier to link queries from the same connection object.  (A given connection may be placed in a pool and reused over multiple requests.  Alternately, a given request may open ten new connections when it ought to be using a pool.  Either way, it's useful information.)
* `cursor_id` serves a similar purpose to `pg_conn_id`, but is assigned to each new cursor object created.


Finally, look at the log entries in the terminal you ran `./scripts/run-flask.sh` in.  You should notice a `FLASK_CID` matching the value for `flask_req_id` in the `app_metadata` object above:

```
2017-02-20 23:20:24,628 correx.flask_app.db_sleep_in_web INFO - calling pg_sleep(20) [FLASK_CID:4rtTDg8Fb6Kb29UTttwG9W]
2017-02-20 23:20:24,628 correx.pg_lib INFO - will send pg_sleep(20) to postgres [FLASK_CID:4rtTDg8Fb6Kb29UTttwG9W]
2017-02-20 23:20:44,651 correx.pg_lib INFO - finished pg_sleep(20) [FLASK_CID:4rtTDg8Fb6Kb29UTttwG9W]
```



### trace a celery->postgres query

Assuming the server is listening on port `9020`, make a GET to this endpoint:
```
http://localhost:9020/api/v1/sleep-in-worker?seconds=20
```

While waiting for that request to return, make a GET to this endpoint:
```
http://localhost:9020/api/v1/inspect-db
```

The response will have the same format as the prior example.  `db_metadata` is truncated here, since `app_metadata` is the important part.

```json
{
  "flask_request_id": "MT2fxUwTn7rHufC8Wv7qhM", 
  "queries": [
    {
      "app_metadata": {
        "celery_task_id": "03a2dc17-e1fb-4ab8-a734-86ef7cdf9efa", 
        "client_pid": 16101, 
        "context_type": "CELERY", 
        "cursor_id": "B5nSuyvZeoF3P5FRnUwUnF", 
        "flask_req_id": null, 
        "os_user": "ubuntu", 
        "pg_conn_id": "z6ZVJ77cM3YX2meW9bPN6A"
      }, 
      "db_metadata": {
        "truncated_for_brevity": true
      }, 
      "query": "select * from pg_sleep(20)"
    }
  ]
}
```

Above, the keys in `app_metadata` have the same meaning as before.  The main difference is that `celery_task_id` and `flask_req_id` are switched:  `flask_req_id` is `null` because we are not in a Flask context, while `celery_task_id` contains the UUID of the associated task.


If you switch to the terminal where you ran `./scripts/run-celery.sh`, you should see log entries with a `CELERY_CID` value matching  `celery_task_id` in the `app_metadata` object above:

```
2017-02-20 23:39:25,352 celery.worker.strategy INFO - Received task: correx.celery_app.pg_sleep_in_worker[03a2dc17-e1fb-4ab8-a734-86ef7cdf9efa]   [CELERY_CID:NONE]
2017-02-20 23:39:25,355 correx.celery_app.pg_sleep_in_worker INFO - seconds=20 [CELERY_CID:03a2dc17-e1fb-4ab8-a734-86ef7cdf9efa]
2017-02-20 23:39:25,355 correx.pg_lib INFO - will send pg_sleep(20) to postgres [CELERY_CID:03a2dc17-e1fb-4ab8-a734-86ef7cdf9efa]
2017-02-20 23:39:45,378 correx.pg_lib INFO - finished pg_sleep(20) [CELERY_CID:03a2dc17-e1fb-4ab8-a734-86ef7cdf9efa]
2017-02-20 23:39:45,379 correx.celery_app.pg_sleep_in_worker INFO - done with pg_sleep(20) [CELERY_CID:03a2dc17-e1fb-4ab8-a734-86ef7cdf9efa]
```




## approach

TODO




## goals

There are two.

### grouping log statements within a layer
Within a single layer of an application, I want an easier way to group log statements together within a given context/request/task.  This isn't really a revolutionary idea.  I feel like there must be a logging library out there that does what I have in mind, but I haven't found it.

For web requests, this means:  I want a unique id associated with each request/response cycle, and I want it to appear in each log message emitted during that cycle.

For background tasks, this means: I want a per-task unique id to appear in each log message emitted during execution of a given Celery task.  Celery tasks already have UUIDs, but only a few log statements from the Celery parent process expose them.

In both cases, easy grouping of related log statements also implies easy attachment of additional per-context metadata: we just have to log it with the same unique ID attached.


### correlating log statements / events across layers
I want to be able to easily links log messages and other events across layers of the application.  This could mean many things, so I'll make it more concrete.

Let's say we're logging all slow queries from Postgres.  We're also centralizing application logs from our own code (Python), the uWSGI request log, and the nginx request log (which we have in front of uWSGI).

If the number of slow queries in the Postgres log spikes, I want to be able to link each query with the unique ID of the individual web request or Celery task responsible.  Extraction of any relevant entries from the application log should be automatic.  In the case of a web request, I also want easy correlation with entries from the associated uWSGI and nginx logs.
