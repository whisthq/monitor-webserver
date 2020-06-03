# Fractal Monitor Webserver

![Python App CI](https://github.com/fractalcomputers/monitor-webserver/workflows/Python%20Webserver%20CI/badge.svg)

This repo contains the code that runs on our Heroku webserver, that monitors for changes in the disks and VMs live, 24/7. The one-off dyno can be interfaced via the heroku CLI.

Heroku: https://fractal-monitor-server.herokuapp.com

Heroku Dashboard: https://dashboard.heroku.com/apps/fractal-monitor-server

## Development

Here are the main setups to run this webserver locally and on Heroku. If developing mainly in Heroku, you should make sure to commit your latest code to GitHub, since this is where our development happens. We have basic continuous integration set via GitHub Actions. For every push or PR to master, the commit will be built and formatted via Python Black, see below. You should always make sure that your code passes the tests in the Actions tab.

### Local setup (Windows/MacOS)

1. Set up the Heroku CLI on your computer
2. Check your python version by typing `python -V`.
  - If you have python 3.6.X:
    - Create a virtual environment for yourself by typing `virtualenv env` and then run the python executable listed in the install text, i.e. `source env\Scripts\activate` in Windows, or `source env/bin/activate` on Linux.
  - If you have Python >3.6 or Python <3.0:
    - Create a Python 3.6 virtual environment. To do this, first install python 3.6.8 from the Python website.
    - Find the directory where python.exe is installed. Make sure you are cd'ed into the vm-monitor folder, then type `virtualenv --python=[DIRECTORY PATH] venv` in your terminal. The terminal should output a "created virtual environment CPython3.6.8" message.
    - Activate it by typing `source venv\Scripts\activate` (Windows) or `source venv/bin/activate` (MacOS/Linux). You will need to type this last command every time to access your virtual environment.
3. Install everything by typing `pip install -r requirements.txt`. Make sure you're in the virtual environment when doing this.
4. Import the environment variables into your computer by typing `heroku config -s --app fractal-monitor-server >> .env`.
5. Type `python monitor.py` to start the monitor locally.

### Run on Heroku

`https://git.heroku.com/fractal-monitor-server.git`

To push to the Heroku servers, you’ll first need to set up the Heroku CLI on your computer.

First, add the Heroku server as a remote: `heroku git:remote -a fractal-monitor-server`. You will need to be added as a collaborator for the fractal-monitor-server Heroku app. Contact Ming, Phil or Jonathan to be added.

To push to the server, first make sure you’re in your own branch, then type `git add .`, `git commit -m “{COMMIT_MESSAGE}”`, then finally `git push heroku {YOUR_BRANCH_NAME}:master`. If you get a git pull error, git pull by typing `git pull heorku master` to pull from Heroku or `git pull origin master` to pull from Github.

To run the monitor script, type `heroku run:detached python monitor.py`.

To view the verbose server logs, type `heroku logs --tail`.  
The server also logs INFO, WARNING, ERROR, and CRITICAL logs to PaperTrail, as [MONITOR].

To view the current running processes, type `heroku ps`.

## Publishing

Once you are ready to deploy to production, you can merge your code into master and then run `./update.sh`. The script will push your local code to Heroku on the master branch, and notify the team via Slack.

## Styling

To ensure that code formatting is standardized, and to minimize clutter in the commits, you should set up styling with [Python black](https://github.com/psf/black) before making any PRs. You may find a variety of tutorial online for your personal setup. This README covers how to set it up on VSCode, Sublime Text and running it from the CLI.

### Python Black

#### [VSCode](https://medium.com/@marcobelo/setting-up-python-black-on-visual-studio-code-5318eba4cd00)

1. Install it on your virtual env or in your local python with the command:

```
$ pip install black
```

2. Now install the python extension for VS-Code, open your VS-Code and type “Ctrl + p”, paste the line bellow and hit enter:

```
ext install ms-python.python
```

3. Go to the settings in your VS-Code typing “Ctrl + ,” or clicking at the gear on the bottom left and selecting “Settings [Ctrl+,]” option.
4. Type “format on save” at the search bar on top of the Settings tab and check the box.
5. Search for “python formatting provider” and select “black”.
6. Now open/create a python file, write some code and save(Ctrl+s) it to see the magic happen!

#### [Sublime](https://github.com/jgirardet/sublack)

#### [CLI](https://github.com/psf/black)

Installation:  
Black can be installed by running `pip install black`. It requires Python 3.6.0+ to run but you can reformat Python 2 code with it, too.

Usage:  
To get started right away with sensible defaults:

```
black {source_file_or_directory}
```

Black doesn't provide many options. You can list them by running `black --help`:
