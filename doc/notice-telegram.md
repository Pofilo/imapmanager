# How to get Token and chatID for Telegram notifier

Official notice is available [here](https://core.telegram.org/bots#6-botfather).

## How to create your bot?

+ Speak to [@botfather](https://t.me/BotFather) and type `/start`.
+ Type `/newbot`, then:
  + Give a **name** to your bot (you can give it any name).
  + Give a **username** to your bot (it must end with `bot` and is unique).
+ Save the API token in `TOKEN` in your configuration file.

## How to generate chatID?

Each conversation (with only one person) has an identifier called **ChatID**.
In this conversation, the bot should have been invited to be able to send messages.

### For a simple chat with your bot

+ Initiate a conversation with your bot (search it with its **username**).

Then, communicate with **cid_bot**:
+ Speak to [@cid_bot](https://t.me/cid_bot) and type `/start`.
+ Type `chatid` to get **your** ChatID.
+ Save it in the `CHATID` in your configuration file.

### For a group chat

+ Create or go to the wanted group.
+ Invite your bot (search it with its **username**).
+ Invite `@cid_bot` to the group.
+ Type `chatid` to get the ChatID of the group.
+ Save it in the `CHATID` in your configuration file.
+ You can now remove `@cid_bot` from the group.

## Implementation

You can find the implementation in `imap.py`.
