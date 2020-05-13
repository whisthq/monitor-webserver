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
