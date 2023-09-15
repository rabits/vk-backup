# VK-Backup

This script can backup data from vk.com onto your storage. It will create backup directory, fill it by data and update it in next run time.

I returned to this project and found that oh boy oh boy it's not working anymore... What a shame,
so I tried my best to figure out what's up with it - and on python2 it was run well, but user
messages were not working, so I found that vk.com don't give access to `messages` for some weird
third-party apps (like vk-backup) anymore. I checked their backup solution - and it's a shame: no
media downloading - just really bad thing they've prepared to say "oh we have backup", NO you
don't!

I ported it to python3 and also prepared a workaround to get the user messages through UI API. So
it become a little bit less usable, but at least you can get something more than available tools...

## Features:

* Store known users & friends
* Dialogs
* Chats
* Attachments media
* Wall
* Photos

## Usage:

To use - first you need to download the repository files - both clone or zip files will work well.
```sh
git clone https://github.com/rabits/vk-backup.git
```

Run `./vk-backup/vk-backup.py --help` to see the available options.

You can use config ini file to store some of your configuration...

There are 2 API are used - and both needs their own way to authenticate and get required tokens:
* Regular API provided by vk.com: stable - used to get non-messages data
* UI API of vk.com: unstable one - is used to get messages data

So in order to properly run, you need to find those UI API credentials:
1. Login to vk.com with the account you want to backup
2. Open browser dev console (press F12 or find in menu), switch to Network tab
3. Go to your VK Messanger and find in dev console link starts with URL `https://vk.com/al_im.php`
4. Copy it's value as CURL

After that you need to run vk-backup like:
```
./vk-backup/vk-backup.py --config-file cfg.ini -- <PASTE_HERE>
```
It will be a quite huge command, that will look like:
```
./vk-backup/vk-backup.py --config-file cfg.ini -- curl 'https://vk.com/al_im.php?act=a_start' --compressed -X POST -H 'User-Agent: Mozilla/5.0 ...
```

It will ask you to enter the provided link into your browser and paste back the API url after login.

## Privacy

The script has no intent to anyhow share your login/password or any other private information with
the others. The sole purpose of the script is to download your profile data from vk.com. Script has
a relatively small codebase, so you can check yourself - only vk.com is accessed and no write API
functions are used in it.

## TODO

* Groups
* Photo albums, audio, video
* Advanced configuration

## Known issues

Tested on 2 profiles and works well, but if you will find some issues - please don't hesitate and
create a ticket or send PR to fix it, thanks!

## Requirements
* python 3.5

## Support
If you like kitties or my opensource development - you can support me by a small bitcoin donation :)

My bitcoin wallet: `15phQNwkVs3fXxvxzBkhuhXA2xoKikPfUy`

