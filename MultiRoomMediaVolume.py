#  Copyright (c) 2021 Poul Spang
#
#  This file, MultiRoomMediaVolume.py, is part of Project skill_MultiRoomMediaVolume.
#
#  Project skill_MultiRoomMediaVolume is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>


# ~/.local/bin/projectalice-sk validate --paths ~/ProjectAlice/skills/MultiRoomMediaVolume


import asyncio
import json
from snapcastcontrol.control.SnapControl import SnapControl

from core.base.model.AliceSkill import AliceSkill
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import IntentHandler
from core.util.Decorators import MqttHandler


from skills.MultiRoomMediaVolume.library.Topics import(	_MULTIROOM_VOLUME,
																									_MULTIROOM_ENTRY_VOLUME,
																									_MULTIROOM_GESTURE_SENSOR_VOLUME_UP,
																									_MULTIROOM_GESTURE_SENSOR_VOLUME_DOWN,
																									_MULTIROOM_VOLUME_CONTROL_TYPE_SET,
																									_MULTIROOM_VOLUME_CONTROL_TYPE_GET,
																									_MULTIROOM_VOLUME_OFFSET_SET,
																									_MULTIROOM_VOLUME_OFFSET_GET,
																									_MULTIROOM_CLIENT_LATENCY_SET
																								)

from skills.MultiRoomMediaVolume.library.CheckSnapcast import(CheckSnapcast)


#-----------------------------------------------
def runThreadSafe(function, *args, **kwargs):
	print(f'##### runAsyncMethod("{function}", {args}, {kwargs}')
	#return asyncio.run_coroutine_threadsafe(function(*args, **kwargs), snapControl._loop)


#-----------------------------------------------
class Group():
	"""docstring for Group"""
	def __init__(self, id, muted, name, stream_id, parent=None):
		# super(Group, self).__init__()
		self._id = id
		self._muted = muted
		self._name = name
		self._stream_id = stream_id
		self._parent = parent
		#self._clients = clients


#-----------------------------------------------
	def __repr__(self):
		rep = f'Group({self._id}, {self._muted}, {self._name}, {self._stream_id})'
		return rep


#-----------------------------------------------
class Client():
	"""docstring for Client"""

	def __init__(self, ID, clientSite, ip, name='Unknown', volume='1', volumeOffset='0', latency='0', connected=False, muted=False, group_id=None):

		self._id 						= ID
		self._clientSite 		= clientSite
		self._name 					= name
		self._ip 						= ip
		self._volumeOffset 	= volumeOffset
		self._volume 				= volume
		self._latency				= latency
		self._connected 		= connected
		self._muted 				= muted
		self._group_id 			= group_id


	#-----------------------------------------------
	def setVolume(self, volume):
		self._volume = volume + self._volumeOffset


	#-----------------------------------------------
	def __repr__(self):
		# rep = f'Client({self._id}, {self._clientSite}, {self._ip}, {self._name}, {self._volume}, {self._volumeOffset}, {self._latency}, {self._connected}, {self._muted}, {self._group_id})'
		rep = f'Client({self._id}, {self._clientSite}, {self._ip}, {self._name}, {self._volume}, _volumeOffset: {self._volumeOffset}, _latency: {self._latency}, {self._connected}, {self._muted}, {self._group_id})'
		return rep


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
		self._entryVolume 						= 1
		self._activeSoundApp					= ""
		self._snapcastcontrol = None
		self.entrance = False

		self._groups = list()
		self._clients = list()
		self._PspPlayers = dict()


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
		# self._volumeControlType = self.getConfig('volumeControl')
		self._volumeControlType = 'snapcast'
		self._beQuiet           = 1
		self._volume 						= "40"
		self._activeSoundApp		= ""
		self._isMuted           = False
		self._PspPlayers        = dict()

		CheckSnapcast.installSnapserver(self)

		multiRoomMediaNotificationCallbacks = {
			'onServerDisconnect': self._onSnapServerDisconnect,
			'onVolumeChange':     self._onSnapVolumeChange,
			'onLatencyChanged':		self._onLatencyChanged,
			'onServerCreated':		self._onSnapServerCreated,
			'onServerUpdate': 		self._onSnapServerUpdate,
			'onGroupMute':				self._onSnapGroupMute,
			'onClientConnect':		self._onSnapClientConnect,
			'onClientDisconnect':	self._onSnapClientDisconnect,
		}

		# >>> Available notificationCallbacks.
		#   'onVolumeChange':
		#   'onLatencyChanged':
		#   'onServerDisconnect':
		#   'onGroupMute':
		#   'onClientConnect':
		#   'onClientDisconnect':
		#   'onServerUpdate':
		#   'onClientNameChanged':
		#   'onGroupStreamchanged':
		#   'onStreamUpdate':
		#   'onServerCreated':


		self._snapcastcontrol = SnapControl(1, "ThreadSnapControl", 'localhost', reconnect=True, notificationCallbacks=multiRoomMediaNotificationCallbacks)

		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': 'onStart'}))

		# Send mixer type to player.
		self.ThreadManager.doLater(interval=0.3, func=self.publishVolumeControlType, args=[self._volumeControlType])


	#-----------------------------------------------
	def _onSnapServerDisconnect(self, exception):
		pass
		# self.logInfo(f"### This is the callback from SnapcastControl - to self.onServerDisconnect - exception: {exception} ")


	#-----------------------------------------------
	def _onSnapVolumeChange(self, data):
		percent = data['params'].get('volume').get('percent')
		muted   = data['params'].get('volume').get('muted')
		clientId  = data['params'].get('id')

		for client in self._clients:
			if client._id == clientId:
				client._muted = muted
				client._volume = percent


#-----------------------------------------------
	def _onLatencyChanged(self, data):
		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onLatencyChanged - data: {data}")

		clientId = data.get('params').get('id')
		for client in self._clients:
			if client._id == clientId:
				client._latency = data.get('params').get('latency')
				self.publish(_MULTIROOM_CLIENT_LATENCY_SET,  json.dumps({'playSite': client._clientSite, 'id': client._id, 'latency': client._latency , 'info': 'onLatencyChanged'}))
				# print(client.__repr__())


	#-----------------------------------------------
	def _onSnapServerCreated(self, data):
		self.publish(_MULTIROOM_VOLUME_OFFSET_GET,  json.dumps({'playSite': 'everywhere'}))

		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapServerCreated - data: {data}\n\n ")
		# self.logInfo(f"\n### This is the callback from SnapcastControl - to self._onSnapServerCreated\n ")


		self._groups = list()
		self._clients = list()
		# Add/chamge Snapcast groups to self._groups.
		for group in data.get('groups'):
			ID 				= group.get('id')
			muted 		= group.get('muted')
			name 			= group.get('name')
			stream_id = group.get('stream_id')

			grp = Group(ID, muted, name, stream_id, parent=self)
			self._groups.append(grp)
			for client in group['clients']:
				ID 				 		= client.get('id')
				clientSite 		= '' #client.get
				ip 						= client.get('host').get('ip')
				name 					= client.get('host').get('name')
				volumeOffset 	= '0'
				latency 			= client.get('config').get('latency')
				connected 		= client.get('connected')
				muted 				= client.get('config').get('volume').get('muted')
				volume 				= client.get('config').get('volume').get('percent')
				group_id 			= grp._id
				cli = Client(ID, clientSite, ip, name, volume, volumeOffset, latency, connected, muted, group_id)
				self._clients.append(cli)
				if volume > 90:
					self._setSnapcastVolume4Client(cli._id, self._entryVolume)


	#-----------------------------------------------
	def _onSnapServerUpdate(self, data):
		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapServerUpdate - data: {data} ")
		self._onSnapServerCreated(data)


	#-----------------------------------------------
	def _onSnapGroupMute(self, data):
		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapGroupMute - data: {data} ")

		for group in self._groups:
			if group._id == data.get('id'):
				group.muted = data.get('mute')


	#-----------------------------------------------
	def _onSnapClientConnect(self, data):
		self.publish(_MULTIROOM_VOLUME_OFFSET_GET,  json.dumps({'playSite': 'everywhere'}))

		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapClientConnect - data: {data} ")
		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapClientConnect ")
		for client in self._clients:
			if client._id == data.get('params').get('id'):
				client._connected = data.get('params').get('client').get('connected')
				client._muted 		= data.get('params').get('client').get('config').get('volume').get('muted')
				client._volume 		= data.get('params').get('client').get('config').get('volume').get('percent')


	#-----------------------------------------------
	def _onSnapClientDisconnect(self, data):
		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapClientDisconnect - data: {data} ")
		# self.logInfo(f"### This is the callback from SnapcastControl - to self._onSnapClientDisconnect")
		for client in self._clients:
			if client._id == data.get('params').get('id'): #data.id:
				client._connected = data.get('params').get('client').get('connected')
				client._muted 		= data.get('params').get('client').get('config').get('volume').get('muted')
				client._volume 		= data.get('params').get('client').get('config').get('volume').get('percent')


	#-----------------------------------------------
	def onStop(self):
		self._snapcastcontrol.closeConnection()

		self._volume = self._startupVolume
		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': 'onStop'}))
		self._setSnapcastVolume(self._volume)


	#-----------------------------------------------
	def onHotwordToggleOff(self, deviceUid: str, session: DialogSession): #b5 rc1
	# def onHotwordToggleOff(self, siteId: str, session: DialogSession): #b4

		# self.logDebug(f"###################### onHotwordToggleOff")
		if session == None:
			return

		for group in self._groups:
			group._muted = True
			self._setSnapcastGroupMute(group._id, True)

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self.beQuiet, 'info': 'onHotwordToggleOff'}))


	#-----------------------------------------------
	def onHotwordToggleOn(self, deviceUid: str, session: DialogSession):  #b5 rc1
	# def onHotwordToggleOn(self, siteId: str, session: DialogSession):  #b4
		# self.logDebug(f"###################### onHotwordToggleOn")


		for group in self._groups:
			group._muted = False
			self._setSnapcastGroupMute(group._id, False)

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': 'onHotwordToggleOn'}))


	#-----------------------------------------------
	def _setSnapcastVolume4Client(self, clientId, volume):
		volume = max(0, min(100, int(volume)))

		for client in self._clients:
			if client._id == clientId:
				client._volume = volume
				vol = int(volume) + int(client._volumeOffset)
				asyncio.run_coroutine_threadsafe(self._snapcastcontrol.setVolume(client._id, vol, client._muted), self._snapcastcontrol._loop)
				break


	#-----------------------------------------------
	def _setSnapcastVolume(self, volume, muted=False, minVolume=0, maxVolume=100 ):
		volume = max(0, min(100, int(volume)))

		for client in self._clients:
			vol = int(volume) + int(client._volumeOffset)
			asyncio.run_coroutine_threadsafe(self._snapcastcontrol.setVolume(client._id, vol, client._muted), self._snapcastcontrol._loop)


	#-----------------------------------------------
	def _setInternalMediaVolume(self, percent = '40'):
		percent = max(0, min(100, int(percent)))

		self._volume = str(percent)


	#-----------------------------------------------
	def _setMediaVolume(self, percent='40', setOnlyInternal=False):
		percent = max(0, min(100, int(percent)))

		self._volume = str(percent)

		if not setOnlyInternal:
			if not self.isMuted:
				self._setSnapcastVolume(self._volume)
			else:
				self._setSnapcastVolume(self._volume, muted=True)


	#-----------------------------------------------
	def _setSnapcastGroupMute(self, group_id, mute):
		asyncio.run_coroutine_threadsafe(self._snapcastcontrol.muteGroup(group_id, mute), self._snapcastcontrol._loop)


	#-----------------------------------------------
	def _setClientLatency(self, client_id, latency):
		for client in self._clients:
			if client._id == client_id:
				if latency != client._latency:
					asyncio.run_coroutine_threadsafe(self._snapcastcontrol.setClientLatency(client_id, int(latency)), self._snapcastcontrol._loop)
					client._latency = latency


	#-----------------------------------------------
	def setVolumeStepsUpDown(self, volumeStepsUpDown :str) -> bool:
		self._volumeStepsUpDown = volumeStepsUpDown

		return True


	#-----------------------------------------------
	def _publishChangeVolumeControlType(self, volume, info="No info"):
			self.publish(_MULTIROOM_VOLUME_CONTROL_TYPE_SET,  json.dumps({'volume': volume, 'volumeControlType': self._volumeControlType, 'info': info}))
			# config.json.template, we have removed the "volumeControl" not in use anymore with the new snapcastcontrol.
			# {
			# 	"volumeStepsUpDown": {
			# 		"defaultValue": 6,
			# 		"dataType": "integer",
			# 		"isSensitive": false,
			# 		"description": "How many step in percent the volume increase/decrease.",
			# 		"onUpdate": "setVolumeStepsUpDown"
			# 	},
			# 	"volumeControl": {
			# 		"defaultValue": "snapcast",
			# 		"dataType": "list",
			# 		"isSensitive": false,
			# 		"values": ["snapcast", "alsamixer"],
			# 		"description": "Which volume control to use snapcast | alsamixer. Further explanation needed.",
			# 		"onUpdate": "publishVolumeControlType"
			# 	}
			# }


	#-----------------------------------------------
	def publishVolumeControlType(self, volumeControl :str) -> bool:
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
	@MqttHandler(_MULTIROOM_VOLUME_OFFSET_SET)
	def setClientVolumeOffset(self, session: DialogSession):
		clientInfo = session.payload

		ID = clientInfo.get('idIp').get('id')
		clientSite 		= clientInfo.get('clientSite')
		ip 						= clientInfo.get('idIp').get('ip')
		volumeOffset 	= clientInfo.get('volumeOffset')
		latency 			= clientInfo.get('latency')

		try:
			if self._PspPlayers[ID]:
				insides = { 'clientSite': clientSite, 'ip': ip, 'volumeOffset': volumeOffset, 'latency': latency }
				self._PspPlayers[ID] = insides

		except Exception as e:
			print(f"player Exception e: {e}")
			insides = { 'clientSite': clientSite, 'ip': ip, 'volumeOffset': volumeOffset, 'latency': latency }
			self._PspPlayers[ID] = insides


		for client in self._clients:
			if client._id == ID:
				client._clientSite 		= self._PspPlayers[client._id]['clientSite']
				client._volumeOffset 	= self._PspPlayers[client._id]['volumeOffset']
				if client._latency != self._PspPlayers[client._id]['latency']:
					self._setClientLatency(client._id, self._PspPlayers[client._id]['latency'])
					client._latency				= self._PspPlayers[client._id]['latency']


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_VOLUME_CONTROL_TYPE_GET)
	def getHandler(self, session: DialogSession):
		self.publishVolumeControlType(self._volumeControlType)


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_GESTURE_SENSOR_VOLUME_UP)
	def gestureSensorVolumeUp(self, session: DialogSession):
		percent = int(self._volume) + self._volumeStepsUpDown
		self._volume = str(percent)

		for client in self._clients:
			vol = client._volume  + self._volumeStepsUpDown
			self._setSnapcastVolume4Client(client._id, vol)

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': '_MULTIROOM_GESTURE_SENSOR_VOLUME_UP'}))


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_GESTURE_SENSOR_VOLUME_DOWN)
	def gestureSensorVolumeDown(self, session: DialogSession):
		percent = int(self._volume) - self._volumeStepsUpDown
		self._volume = str(percent)

		for client in self._clients:
			vol = client._volume - self._volumeStepsUpDown
			self._setSnapcastVolume4Client(client._id, vol)

		if not self.isMuted:
			self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': '_MULTIROOM_GESTURE_SENSOR_VOLUME_UP'}))


	#-----------------------------------------------
	@IntentHandler('volumeUp')
	def volumeUp(self, session: DialogSession):
		percent	= '0' if 'Percent' not in session.slots else session.slotValue('Percent')

		percent = int(percent)

		for client in self._clients:
			if percent == 0:
				vol = client._volume  + self._volumeStepsUpDown
			else:
				vol = client._volume  + int(session.slotValue('Percent'))

			self._setSnapcastVolume4Client(client._id, vol)

		self.endDialog(session.sessionId, '')


	#-----------------------------------------------
	@IntentHandler('volumeDown')
	def volumeDown(self, session: DialogSession):
		percent	= '0' if 'Percent' not in session.slots else session.slotValue('Percent')

		percent = int(percent)

		for client in self._clients:
			if percent == 0:
				vol = client._volume  - self._volumeStepsUpDown
			else:
				vol = client._volume  - int(session.slotValue('Percent'))

			self._setSnapcastVolume4Client(client._id, vol)

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

		for group in self._groups:
			self._setSnapcastGroupMute(group._id, True)

		self.endDialog(session.sessionId, self.randomTalk('volumeMute'))


	#-----------------------------------------------
	@IntentHandler('volumeUnmute')
	def volumeUnmute(self, session: DialogSession):
		self.isMuted = False
		self._onHotwordVolume = self._volume

		for group in self._groups:
			self._setSnapcastGroupMute(group._id, False)

		self.endDialog(session.sessionId, self.randomTalk('volumeUnmute'))


	#-----------------------------------------------
	@MqttHandler(_MULTIROOM_ENTRY_VOLUME)
	def setStationEntryVolume(self, session: DialogSession, **_kwargs):
		try:
			self._activeSoundApp = session.payload['activeSoundApp']
		except Exception as e:
			print(f"################# except Exception as e: {e}")

		self._entryVolume = self._volume = session.payload['stationVolume']




		#'sendFrom': 'PspBluetoothStreamer'
		# if self._activeSoundApp == 'PspBluetoothStreamer' in list(session.payload.values()):
		# 	self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._volume, 'info': 'BluetoothStreamer'}))
		self.publish(_MULTIROOM_VOLUME,  json.dumps({'playSite': 'everywhere', 'volume': self._entryVolume, 'info': 'entryVolume'}))

		self._setSnapcastVolume(self._entryVolume)


	#-----------------------------------------------
	def onSkillDeleted(self, skill: str):
		CheckSnapcast.removeSnapserver()
		super()
