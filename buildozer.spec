[app]
title = Campaign Forge
package.name = campaignforge
package.domain = org.campaignforge

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf

version = 0.1.3

requirements = python3,kivy==2.3.0,pillow,android,pyjnius,pychromecast,zeroconf,ifaddr,protobuf,cython==0.29.36
android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_MULTICAST_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_AUDIO,READ_MEDIA_VIDEO

orientation = portrait
fullscreen = 1

android.accept_sdk_license = True
android.private_storage = False

p4a.branch = v2024.01.21
android.enable_androidx = True

p4a.bootstrap = sdl2

log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
