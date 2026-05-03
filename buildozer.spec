[app]
title = CampaignForge
package.name = campaignforge
package.domain = org.rpg

icon.filename = %(source.dir)s/icon.png

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 0.1.0

requirements = python3,kivy,pillow,android,pychromecast,zeroconf,ifaddr,protobuf

android.api = 35
android.minapi = 21
android.archs = arm64-v8a

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_MULTICAST_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_AUDIO,READ_MEDIA_VIDEO

orientation = portrait
fullscreen = 1

android.accept_sdk_license = True
android.private_storage = True

p4a.bootstrap = sdl2

log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
