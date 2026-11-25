# Debian System Care

A graphical system maintenance and security application for Debian Linux.

## Features

- System cleanup and maintenance
- System monitoring
- Update management
- Firewall protection using UFW
- Antivirus integration using ClamAV

## Requirements

- Python 3
- python3-apt
- python3-gi
- GTK 3
- libnotify-bin
- pkexec
- ClamAV
- UFW

## Build and Installation

Clone the repository:

    git clone https://github.com/srdjanbaic/debian-system-care.git
    cd debian-system-care

Build the Debian package:

    dpkg-deb --build debian-system-care-package debian-system-care_2.1_all.deb

Install the package:

    sudo apt install ./debian-system-care_2.1_all.deb

## Source Code

https://github.com/srdjanbaic/debian-system-care

## License

No license has been specified yet.
