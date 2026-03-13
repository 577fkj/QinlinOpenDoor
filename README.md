# Qinlin open door

## Run server.py

### Web
- http://127.0.0.1:5000/{access_token}/

### SMS Receive

POST http://127.0.0.1:5000/{access_token}/api/receive_sms

Body
- `{"phone": "<phone number>", "content": "<sms content>"}`

## Docker compose

### Web
- http://127.0.0.1:7751/{access_token}/

### SMS Receive

POST http://127.0.0.1:7751/{access_token}/api/receive_sms

Body
- `{"phone": "<phone number>", "content": "<sms content>"}`
