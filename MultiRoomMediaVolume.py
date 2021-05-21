# ~/.local/bin/projectalice-sk validate --paths ~/ProjectAlice/skills/MultiRoomMediaVolume


import json

from core.base.model.AliceSkill import AliceSkill
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import IntentHandler
from core.util.Decorators import MqttHandler


from skills.MultiRoomMediaVolume.library.Topics import(	_MULTIROOM_VOLUME,
																									_MULTIROOM_ENTRY_VOLUME,
																									_MULTIROOM_GESTURE_SENSOR_VOLUME_UP,
																									_MULTIROOM_GESTURE_SENSOR_VOLUME_DOWN,
																									_MULTIROOM_VOLUME_CONTROL_TYPE_SET,
																									_MULTIROOM_VOLUME_CONTROL_TYPE_GET
																								)


from skills.MultiRoomMediaVolume.library.CheckSnapcast import(CheckSnapcast)

#-----------------------------------------------
class MultiRoomMediaVolume(AliceSkill):
	"""
	Author: poulsp
	Description: Manage volume in the synchronous multiroom audio system.
	"""
	NAME = 'MultiRoomMediaVolume'


	#-----------------------------------------------
	def __init__(self):
		super().__init__()

		self._volumeStepsUpDown = None
		self._beQuiet                 = 1
		self._startupVolume           = "0"
		self._isMuted                 = False
		self._volume 									= self._beQuiet
		self._activeSoundApp					= ""
		self._loop = None
		self._server = None

		self.entrance = False


	#-----------------------------------------------
	@property
	def beQuiet(self):
		return self._beQuiet


	#-----------------------------------------------
	@property
	def isMuted(self):
		return self._isMuted


	#-----------------------------------------------
	@isMuted.setter
	def isMuted(self, boolValue):
		self._isMuted = boolValue


	#-----------------------------------------------
	@property
	def volume(self):
		return self._volume


	#-----------------------------------------------
	@volume.setter
	def volume(self, value):
		self._volume = value


	#-----------------------------------------------
	def onStart(self):
		super().onStart()
		self._volumeStepsUpDown = self.getConfig('volumeStepsUpDown')
		self._volumeControlType = self.getConfig('volumeControl')
		self._beQuiet           = 1
		self._volume 						= "40"
		self._activeSoundApp		= ""
		self._isMuted           = False

		CheckSnapcast.installSnapserver(self)
		self.logInfo

		# We import these here because snapcast.control throw an exception if it can't connect to port 1705 in the top of this file.
		import asyncio
		import snapcast.control


		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': ''}))
		self._loop = asyncio.get_event_loop()
		self._server = self._loop.run_until_complete(snapcast.control.create_server(self._loop, 'localhost'))

		# Send mixer type to player.
		self.ThreadManager.doLater(interval=0.3, func=self.publishVolumeControlType, args=[self._volumeControlType])


	#-----------------------------------------------
	def onStop(self):
		self._volume = self._startupVolume
		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': ''}))
		self._setSnapcastVolume(self._volume)


	#-----------------------------------------------
	def onHotwordToggleOff(self, deviceUid: str, session: DialogSession): #b5 rc1
	# def onHotwordToggleOff(self, siteId: str, session: DialogSession): #b4
		if session == None:
			return

		if not self.isMuted:
			self._onHotwordVolume = self._volume
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self.beQuiet, 'info': 'onHotwordToggleOff'}))
			self._setSnapcastVolume(self._volume)


	#-----------------------------------------------
	def onHotwordToggleOn(self, deviceUid: str, session: DialogSession):  #b5 rc1
	# def onHotwordToggleOn(self, siteId: str, session: DialogSession):  #b4
		#self.logDebug(f"###################### onHotwordToggleOn")

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': 'onHotwordToggleOn'}))
			self._setSnapcastVolume(self._volume)


	#-----------------------------------------------
	def _setSnapcastVolume(self, volume, muted=False, gyffe=True, minVolume=0, maxVolume=100 ):
		volume = int(volume)
		if int(volume) <= minVolume:
			volume = minVolume
		elif int(volume) >= maxVolume:
			volume = maxVolume

		if self._volumeControlType == "alsamixer" and gyffe:
			volume = 100

		clients = self._server.clients
		for xClient in clients:
			self._loop.run_until_complete(self._server.client_volume(xClient.identifier, {'percent': volume, 'muted': muted}))


	#-----------------------------------------------
	def _setMediaVolume(self, percent = '40', maxVolume=94):
		if self._volumeControlType != "alsamixer":
			maxVolume=100

		percent = int(percent)
		if percent == 0:
			percent = 1
		else:
			if percent >= maxVolume:
				percent = maxVolume
			elif percent <= 0:
				percent = 1

		self._volume = str(percent)

		if not self.isMuted:
			self._setSnapcastVolume(self._volume)
		else:
			self._setSnapcastVolume(self._volume, muted=True)


	#-----------------------------------------------
	def setVolumeStepsUpDown(self, volumeStepsUpDown :str) -> bool:
		self._volumeStepsUpDown = volumeStepsUpDown

		return True


	#-----------------------------------------------
	def _publishChangeVolumeControlType(self, volume, info="No info"):
			self.publish(_MULTIROOM_VOLUME_CONTROL_TYPE_SET,  json.dumps({'volume': volume, 'volumeControlType': self._volumeControlType, 'info': info}))


	#-----------------------------------------------
	def publishVolumeControlType(self, volumeControl :str) -> bool:
		# When changing volume Control, we must set the volume to 0 on the Players/alsamixer and snap controller.
		# When we switch to alsamixer it must be set to self._volume and snapcontroler to 100%.
		# Conversely, alsamixer should be set to 100% and snap controller to self._volume.

		# Why do we use delayed method calls here, amongst other times issues between published/mqtt alsamixer setting and the quicker snap controller.
		#
		# Another reason is, when we are inside this method we are inside a Thread made in Alice core and here are the snapcast clients out of scope.
		# So, when we use delayed methods call here we'll be out of this jailhouse quickly and when the "do_later" fire and execute our methods the clients are back in scope again.


		self._volumeControlType = volumeControl

		isMuted = False
		if self.isMuted:
			isMuted = True

		self.ThreadManager.doLater(interval=0.1, func=self._setSnapcastVolume, args=["1", isMuted, False])
		self.ThreadManager.doLater(interval=0.3, func=self._publishChangeVolumeControlType, args=["1"])


		if self._volumeControlType == 'alsamixer':
			self.ThreadManager.doLater(interval=0.8, func=self._setSnapcastVolume, args=["100", isMuted, False])
			self.ThreadManager.doLater(interval=0.5, func=self._publishChangeVolumeControlType, args=[self._volume])

		else:
			self.ThreadManager.doLater(interval=0.3, func=self._publishChangeVolumeControlType, args=["100"])
			self.ThreadManager.doLater(interval=0.8, func=self._setSnapcastVolume, args=[self._volume, isMuted, False])


		return True


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_VOLUME_CONTROL_TYPE_GET)
	def getHandler(self, session: DialogSession):
		self.publishVolumeControlType(self._volumeControlType)


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_GESTURE_SENSOR_VOLUME_UP)
	def gestureSensorVolumeUp(self, session: DialogSession):
		percent = int(self._volume) + self._volumeStepsUpDown
		self._volume = str(percent)
		self._setMediaVolume(self._volume)

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': ''}))


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_GESTURE_SENSOR_VOLUME_DOWN)
	def gestureSensorVolumeDown(self, session: DialogSession):
		percent = int(self._volume) - self._volumeStepsUpDown
		self._volume = str(percent)
		self._setMediaVolume(self._volume)

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': ''}))


	#-----------------------------------------------
	@IntentHandler('volumeUp')
	def volumeUp(self, session: DialogSession):
		percent	= '0' if 'Percent' not in session.slots else session.slotValue('Percent')

		percent = int(percent)
		if percent == 0:
			percent = int(self._volume) + self._volumeStepsUpDown
		else:
			percent = int(self._volume) + int(session.slotValue('Percent'))

		self._volume = str(percent)
		self._setMediaVolume(self._volume)

		self.endDialog(session.sessionId, '')


	#-----------------------------------------------
	@IntentHandler('volumeDown')
	def volumeDown(self, session: DialogSession):
		percent	= '0' if 'Percent' not in session.slots else session.slotValue('Percent')

		percent = int(percent)
		if percent == 0:
			percent = int(self._volume) - self._volumeStepsUpDown
		else:
			percent = int(self._volume) - int(session.slotValue('Percent'))

		self._volume = str(percent)
		self._setMediaVolume(self._volume)

		self.endDialog(session.sessionId, '')


	#-----------------------------------------------
	@IntentHandler('setVolume')
	def setVolume(self, session: DialogSession):
		percent	= '0' if 'Percent' not in session.slots else session.slotValue('Percent')

		self._setMediaVolume(percent)
		self.endDialog(session.sessionId, self.randomTalk('setVolume', [self._volume]))


	#-----------------------------------------------
	@IntentHandler('getVolume')
	def getVolume(self, session: DialogSession):
		self.endDialog(session.sessionId, self.randomTalk('getVolume', [self._volume]))


	#-----------------------------------------------
	@IntentHandler('volumeMute')
	def volumeMute(self, session: DialogSession):
		self.isMuted = True
		self._onHotwordVolume = self._volume
		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self.beQuiet, 'muted': True}))
		self._setSnapcastVolume(self._volume, muted=True)

		self.endDialog(session.sessionId, self.randomTalk('volumeMute'))


	#-----------------------------------------------
	@IntentHandler('volumeUnmute')
	def volumeUnmute(self, session: DialogSession):
		self.isMuted = False
		self._onHotwordVolume = self._volume
		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'muted': False}))
		self._setSnapcastVolume(self._volume, muted=False)

		self.endDialog(session.sessionId, self.randomTalk('volumeUnmute'))


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_ENTRY_VOLUME)
	def setStationEntryVolume(self, session: DialogSession, **_kwargs):
		try:
			self._activeSoundApp = session.payload['activeSoundApp']
		except Exception as e:
			print(f"################# except Exception as e: {e}")


		# Volume is passed to players via onHotwordToggleOn/Off
		self._volume = session.payload['stationVolume']

		#'sendFrom': 'PspBluetoothStreamer'
		# if self._activeSoundApp == 'PspBluetoothStreamer' in list(session.payload.values()):
		# 	self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume}))
		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume}))
		self._setSnapcastVolume(self._volume)


	#-----------------------------------------------
	def onSkillDeleted(self, skill: str):
		CheckSnapcast.removeSnapserver()
		super()
