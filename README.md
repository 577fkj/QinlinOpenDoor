# Qinlin open door

## Run server.py

### Web
- http://127.0.0.1:5000/?token=<access_token>

### PWA
- http://127.0.0.1:5000/token:<access_token>

### SMS Receive

POST http://127.0.0.1:5000/receive_sms?token=<access_token>

Body
- `{"phone": "<phone number>", "content": "<sms content>"}`

GET
- http://127.0.0.1:5000/receive_sms?token=<access_token>&phone=<phone_number>&content=<sms_content>

## Docker compose

### Web
- http://127.0.0.1:7751/?token=<access_token>

### PWA
- http://127.0.0.1:7751/token:<access_token>

### SMS Receive

POST http://127.0.0.1:7751/receive_sms?token=<access_token>

Body
- `{"phone": "<phone number>", "content": "<sms content>"}`

GET
- http://127.0.0.1:7751/receive_sms?token=<access_token>&phone=<phone_number>&content=<sms_content>
