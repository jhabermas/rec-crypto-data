# Supervisor config

1. Install [supervisor](http://supervisord.org/index.html)
2. Adjust paths in `rec_data.ini`
3. Place the ini file in `/etc/supervisord.d/`
4. Restart supervisor service

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

5. Monitor and manage the process

```bash
sudo supervisorctl start rec_data
sudo supervisorctl status
sudo supervisorctl stop rec_data
```
