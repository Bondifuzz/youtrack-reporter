docker run -it --name youtrack-server-instance  \
    -v ~/Work/yt_reporter/instance_youtrack/data:/opt/youtrack/data \
    -v ~/Work/yt_reporter/instance_youtrack/conf:/opt/youtrack/conf  \
    -v ~/Work/yt_reporter/instance_youtrack/logs:/opt/youtrack/logs  \
    -v ~/Work/yt_reporter/instance_youtrack/backups:/opt/youtrack/backups  \
    -p 31337:8080 \
    jetbrains/youtrack:2022.2.51836
