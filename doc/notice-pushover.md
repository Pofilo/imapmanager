# How to get Token and user key for Pushover notifier

Official notice is available [here](https://pushover.net/api).

## How to get your user key?

The **user key** identifies the account receiving the notifications.

+ Log in on [pushover.net](https://pushover.net).
+ The **Your User Key** field is displayed at the top right of the dashboard.
+ Save it in the `user_key` in your configuration file.

You also need the Pushover application installed on at least one device
(Android, iOS or desktop) and logged in with that same account, otherwise there
is nowhere to deliver the notifications.

## How to create your application (token)?

Each application sending notifications has its own **API token**.

+ Go to [pushover.net/apps/build](https://pushover.net/apps/build).
+ Give a **name** to your application (for example `imapmanager`).
+ Choose the type `Application` and accept the terms, then create it.
+ The **API Token/Key** is displayed on the application page.
+ Save it in the `token` in your configuration file.

## Configuration

```yaml
pushover:
  token: "xx"
  user_key: "yy"
```

## Implementation

You can find the implementation in `notifiers.py`.
