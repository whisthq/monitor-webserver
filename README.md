# Fractal Monitor Webserver

This repo contains the code that runs on our AWS EC2 instance, that monitors for changes in the disks and VMs live, 24/7. Our instance is a basic Ubuntu machine, that can be connected to via SSH and FileZilla.

## Set up

### SSH to the EC2 instance

This readme covers how to connect to the instance via Putty.

1. Install PuTTY on your computer.
   - (Linux) Install PuTTYGen on your computer
2. Obtain the private SSH key to connect to the instance. You can contact Jonathan or Ming for the key.
3. Use PuTTYGen to convert the key from `.pem` format to `.ppk`, the PuTTY format.

- (Windows)
  - Open PuTTYGen and click the 'Load' button, in the field 'Load an existing private key file'
  - List all file types in the file explorer, and select the `.pem` key you obtained. It should be named `MonitorServer.pem` by default.
  - In the 'Parameters' field, select 'RSA' and set '2048' for 'Number of bits in a generated key'.
  - Save the key as a private key.
- (Linux)
  - Run the following:
    ```shell
    sudo apt install putty-tools
    puttygen FractalMonitor.pem -O private -o FractalMonitor.ppk
    ```

4. Open PuTTY
   - (Windows)
     - Set the 'hostname' field to `ubuntu@ec2-52-91-235-140.compute-1.amazonaws.com`
   - (Linux)
     - Set the 'hostname' field to `ec2-52-91-235-140.compute-1.amazonaws.com`
   - Set the 'port' field to `22`
   - On the settings bar on the left, select 'connection > SSH > auth'. In the field 'Priavte key file for authentication', hit the 'Browse' button, and select the `.ppk` file you generated.
   - Save your SSH profile under 'session' by giving it a name and clicking the 'save' button.
   - Press the 'open' button.
   - (Linux)
     - When prompted for the username, enter `ubuntu`

### FTP to the EC2 instance

This readme covers how to send files to the instance via FileZilla.

1. Install FileZilla Client.
2. Under 'File > Site Manager' (ctrl-S), create a 'New site'
3. Set the 'Protocol' field to `SFTP`, 'Host' field to `ec2-52-91-235-140.compute-1.amazonaws.com`, 'Logon Type' field to `Key file`, 'User' field to `ubuntu`, and browse for the `.ppk` file for the 'Key File' field.
4. Hit the 'Conect' button, and transfer files using FTP.

## Interfacing

### Environment variables

**Load environment variables:**

1. On SSH, run: `source ~/.bashrc`
   _Note_: You will have to source bashrc for each screen instance you make.

**Read environment variables in python3:**

Example code:

```python
import os
print(os.environ['LOCATION'])
```

**Change environment variables:**

1. On FileZilla Client, copy the `.bashrc` file from the EC2 instance to your local computer.
2. Make the necessary changes, like adding an environment variable to the end: `export TEST_VAR='Hello world!'`
3. Save the file, and overwrite the existing file on the EC2 instance using FileZilla.
4. On SSH, run: `source ~/.bashrc`

### Run scripts concurrently

On the Ubuntu EC2 instance, you can simply type `screen` to open a new terminal screen in SSH without interfering with your other screens. You can run Python scripts here 24/7.

To exit screen, press `ctrl+A+D` on Windows. To reenter screen, type `screen -r`.

To kill the screen you're in, press `ctrl + a` and then press `k`, then press `y`

## Run on Heroku

`https://git.heroku.com/fractal-monitor-server.git`

To push to the Herokuservers, you’ll first need to set up the Heroku CLI on your computer.

First, add the Heroku server as a remote:

To push to the server, first make sure you’re in your own branch, then type `git add .`, then `git commit -m “COMMIT MESSAGE”`, then finally `git push heroku {YOUR_BRANCH_NAME}:master`. If you get a git pull error, git pull by typing `git pull heorku master` to pull from Heroku or `git pull origin master` to pull from Github.

To run the monitor script, type `heroku run python monitor.py`.

To view the server logs, type `heroku logs --tail --remote staging`.

## Styling

To ensure that code formatting is standardized, and to minimize clutter in the commits, you should set up styling with [Python black](https://github.com/psf/black) before making any PRs. You may find a variety of tutorial online for your personal setup. This README covers how to set it up on VSCode.

### Python Black on VSCode

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

<sub>[Source](https://medium.com/@marcobelo/setting-up-python-black-on-visual-studio-code-5318eba4cd00)</sub>
