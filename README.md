# pac-server

A simple PAC server

# Install

    git clone https://github.com/brglng/pac-server.git
    cd pac-server
    pip install --user .

# Run

    pac-server

# Configration

On first run, the program will generate its configuration file at
`~/.config/pac-server/config.ini`, its content is like this:

```ini
[server]
host = 127.0.0.1
port = 1091
pac-path = /pac
update-interval = 43200

[pac]
proxy = PROXY 127.0.0.1:8118;
gfwlist = https://github.com/gfwlist/gfwlist/raw/master/gfwlist.txt
precise = no

[user-rules]
||google.com
||google.co.jp
||google.co.hk
||bbc.co.uk
||googleapis.com
||googlesyndication.com
||github.com
||wikipedia.org
```

The configuration syntax is very straight forward. The `user-rules` section
uses the same syntax as `gfwlist`.

<!-- vim: cc=79
-->
