
direnv allow


# server in watch mode
watchexec -r -w mock_b12_server.py -- python mock_b12_server.py

http://127.0.0.1:8000


./submit_sample.sh http://localhost:8000


./submit_application.py


