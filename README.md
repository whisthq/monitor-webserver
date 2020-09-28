# Fractal Monitor Webserver

![Python Webserver CI](https://github.com/fractalcomputers/monitor-webserver/workflows/Python%20Webserver%20CI/badge.svg)

**THIS REPOSITORY WAS ARCHIVED FOLLOWING OUR MIGRATION FROM VIRTUAL MACHINES TO CONTAINERS, WHICH DO NOT NEED MONITORING AS THEY ARE SPUN UP AND DOWN AS USERS REQUEST SPECIFIC APPLICATIONS. ALL HEROKU SLUGS, DATADOG HOSTS AND OTHER HOSTING SERVICES WERE DELETED. THE REPOSITORY IS LEFT AS ARCHIVED HERE FOR REFERENCE**

This repository contains the code that runs on our Heroku `fractal-monitor-webserver`, which is responsible for monitoring changes in the disks and Azure VMs live, 24/7. The one-off dyno can be interfaced via the Heroku CLI.

Our webserver is hosted on Heroku [here](https://fractal-monitor-server.herokuapp.com).

Our webserver logs are hosted on Datadog [here](https://app.datadoghq.com/logs?cols=core_host%2Ccore_service&from_ts=1593977274176&index=&live=true&messageDisplay=inline&stream_sort=desc&to_ts=1593978174176).

## Development

We have basic continuous integration set via GitHub Actions. For every PR to master, the commit will be built and a series of tests will be run via `pytest`. The runner will also check if the code is formatted with via Python Black and will report failure if not. See **Styling** below for setting pre-commit hooks and/or IDE integration for linting.

To see full documentation, check the repository's [Wiki](https://github.com/fractalcomputers/monitor-webserver/wiki).

### Local Setup (Windows/MacOS)

Since the monitor webserver runs independently from any other services, and that it already has access to the SQL databases, we currently do not do testing on local machines. If the time comes where we have testing SQL tables, the monitor webserver will be changed to accomodate local testing.

### Run on Heroku

Here are the main steps to run this webserver on Heroku. While developing mainly in Heroku, you should make sure to commit your latest code to GitHub, since this is where our development happens. The monitor is hosted at `https://git.heroku.com/fractal-monitor-server.git`.

To push to the Heroku server, you’ll first need to set up the Heroku CLI on your computer.

First, add the Heroku server as a remote: `heroku git:remote -a fractal-monitor-server`. You will need to have been added as a collaborator for the `fractal-monitor-server ` Heroku app on the Fractal Heroku team.

To push to the server, first make sure you’re in your own branch, then type `git add .`, `git commit -m “{COMMIT_MESSAGE}”`, then finally `git push heroku {YOUR_BRANCH_NAME}:master`. If you get a git pull error, git pull by typing `git pull heroku master` to pull from Heroku or `git pull origin master` to pull from GitHub.

To run the monitor script, type `heroku run:detached python monitor.py`.

To view the verbose server logs on Heroku, type `heroku logs --tail`. We also aggregate logs in Datadog via a HTTP sink. You can access them [here](https://app.datadoghq.com/logs?cols=core_host%2Ccore_service&from_ts=1593977274176&index=&live=true&messageDisplay=inline&stream_sort=desc&to_ts=1593978174176). If you need to modify the Datadog logging, refer to the [Heroku Webserver Datadog Logging](https://www.notion.so/fractalcomputers/Heroku-Webserver-Datadog-Logging-dfd38d40705a4226b9f0922ef262709c) document in the Engineering Wiki of the Fractal Notion.

To view the current running processes, type `heroku ps`.

## Publishing

Once you are ready to deploy to production, you can merge your code into `master` and then run `./update.sh`. The script will push your local code to Heroku on the `master` branch, and notify the team via Slack.

## Styling

To ensure that code formatting is standardized, and to minimize clutter in the commits, you should set up styling with [Python Black](https://github.com/psf/black) before making any PRs. We have [pre-commit hooks](https://pre-commit.com/) with Python Black support installed on this project, which you can initialize by first installing pre-commit via `pip install pre-commit` and then running `pre-commit install` to instantiate the hooks for Python Black.

You can always run Python Black directly from a terminal by first installing it via `pip install black` (requires Python 3.6+) and running `black .` to format the whole project. You can see and modify the project's Python Black settings in `pyproject.toml` and list options by running `black --help`. If you prefer, you can also install it directly within your IDE by via the following instructions:

### [VSCode](https://medium.com/@marcobelo/setting-up-python-black-on-visual-studio-code-5318eba4cd00)

1. Install it on your virtual env or in your local Python with the command: `pip install black`

2. Now install the Python extension for VS-Code by opening your VSCode, typing “Ctrl + P”, and pasting the line below:

```
ext install ms-python.python
```

3. Go to the settings in your VSCode by typing “Ctrl + ,” or clicking at the gear on the bottom left and selecting “Settings [Ctrl+,]” option.

4. Type “format on save” at the search bar on top of the Settings tab and check the box.

5. Search for “Python formatting provider” and select “Black”.

6. Now open/create a Python file, write some code and save it to see the magic happen!
