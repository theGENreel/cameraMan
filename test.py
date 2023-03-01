from onvif import ONVIFCamera

cam = ONVIFCamera('10.222.0.105', user='admin', passwd='8ftu3QMtuW!F', port=80)

media = cam.create_media_service()
profiles = cam.media.GetProfiles()
stream = cam.media.GetStreamUri({'StreamSetup':{'Stream':'RTP-Unicast','Transport':'RTSP'},'ProfileToken':profiles[1]['token']})
pass
