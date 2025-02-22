# Fact Check-in

> Validate if the attendee is registered for the conference by ticket code, name and email

## Features

1. Validate if the attendee is registered for the conference by ticket code and name
2. Validate if the attendee is registered by email
3. Provide information about the registration type (attendee, speaker, sponsor, organizer, etc.)

## Use Cases

1. Automatically add the attendee to the conference Discord assigning roles based on the registration type
2. Allow access to a video-streaming platform for conference talks


The REST-API returns the following information:

Important: run with ONE worker only!
```
uvicorn main:app --port 8080 --host "0.0.0.0" 
```

It takes about 30 sec to launch, data is loaded and process from Tito

## Set-Up

Add a `.env` file with the following content:

```text
TITO_TOKEN="your_secret_token"
ACCOUNT_SLUG="account_slug_from_tito"
EVENT_SLUG="event_slug_from_tito"
```
