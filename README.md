# HAUI CHAT - Django Project For Student Ha Noi University of Industry

This is a project connect students  and it's all free and Nonprofit. You want to join with me !! if you is a dev ?? or you is a student can use it. 

## Note
1. Current Celery 4.2.1 **ONLY SUPPORT Python (2.7, 3.4, 3.5, 3.6)**, **DO NOT** use Python 3.7 because of this [async keyword issue](https://github.com/celery/celery/issues/4500)
2. **ONLY USE** `redis==2.10.6` because of this [float issue](https://github.com/celery/celery/issues/5175) on redis 3.0.0

## What project structure?

1. All project apps are moved into `apps` folder for good structure
2. Different environments has its own settings that extend from `settings/base.py` file, instead of using default Django `settings.py` file:
    * `settings/dev.py` (For Development env)
    * `settings/prod.py` (For Production)
    * And you can add your own file, e.g `settings/test.py` for your Test env.
3. Customize `User` model, so you can extend the model to meet your function without using [profile model](https://docs.djangoproject.com/en/2.1/topics/auth/customizing/#extending-the-existing-user-model) method
4. Integrate and pre-config for [Celery Task Queue](http://www.celeryproject.org) include [Scheduled Tasks](http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html). I think our project eventually will need a task queue system.
5. Docker compose config. One command to run them all.

## Make Your Hand Dirty
 1. Install and run Redis server
 2. Install and run PosgreSQL server
 3. Run Celery worker
```bash
$ celery worker --app sixcents --loglevel info --logfile celery-worker.log --detach
```
## How to run it? 
1. it's so easy (install requirement)
```bash
$ pip install -r requirement.txt
```
2. The basic 

```bash
$ ./manage.py runserver
```
Boom, the server is running on: http://localhost:8000

## How to custom

## TODO
1.Build project

2.Build function 

## LICENSE
MIT License

Copyright (c) 2018 Tuan Pham <tuanpx96@gmail.com>