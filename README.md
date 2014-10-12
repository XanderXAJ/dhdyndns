dhdyndns
========

Script for updating DreamHost domain DNS A records.  Useful if you're running a home server.

Run it by passing your [DreamHost API key](https://panel.dreamhost.com/?tree=home.api), your domain and the new IP address:
```
dhdyndns.py 1234567890ABCDEF example.com $(curl -s icanhazip.com)
```

View the latest usage information by passing `-h`:
```
dhdyndns.py -h
```

