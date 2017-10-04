## Auth (with token)

### Details
**URL**
```
POST https://android.clients.google.com/auth HTTP/1.1
```

**HEADERS**
```
device: <hidden_device_id>
app: com.google.android.gms
Accept-Encoding: gzip
User-Agent: GoogleAuth/1.4 (A0001 NJH47F); gzip
content-length: 638
content-type: application/x-www-form-urlencoded
Host: android.clients.google.com
Connection: Keep-Alive
```

**URLEncoded query string**
```
androidId=<hidden>&lang=en_US&google_play_services_version=11509438&sdk_version=25&device_country=it&request_visible_actions=&client_sig=38918a453d07199354f8b19af05ec6562ced5788&callerSig=38918a453d07199354f8b19af05ec6562ced5788&Email=<hidden>&service=oauth2%3Ahttps%3A%2F%2Fwww.googleapis.com%2Fauth%2Fplacesserver&app=com.google.android.gms&check_email=1&token_request_options=CAA4AQ%3D%3D&system_partition=1&callerPkg=com.google.android.gms&Token=<hidden>
```

**URLEncoded parsed**
```
androidId:                    <hidden>
lang:                         en_US
google_play_services_version: 11509438
sdk_version:                  25
device_country:               it
request_visible_actions:
client_sig:                   38918a453d07199354f8b19af05ec6562ced5788
callerSig:                    38918a453d07199354f8b19af05ec6562ced5788
Email:                        <hidden>
service:                      oauth2:https://www.googleapis.com/auth/placesserver
app:                          com.google.android.gms
check_email:                  1
token_request_options:        CAA4AQ==
system_partition:             1
callerPkg:                    com.google.android.gms
Token:                        <hidden>
```

### Notes

Token in the URLEncoded query is the Master Token, not the Auth Token.
Some info on Master Token [here](https://sbktech.blogspot.it/2014/01/inside-android-play-services-magic.html)
