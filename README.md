# AI-Assistant-with-openAI-

Building a human like virtual text assistant with LLM, Python flask, and openAI APIs
[Unit]
Description=Gunicorn instance to serve myapp
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/AI-Assistant-with-openAI
Environment="PATH=/home/ubuntu/AI-Assistant-with-openAI/venv/bin"
ExecStart=/home/ubuntu/AI-Assistant-with-openAI/venv/bin/gunicorn --workers 3 --bind unix:assistant.sock -m 007 main:app

[Install]
WantedBy=multi-user.target
