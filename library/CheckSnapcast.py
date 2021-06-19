#!./venv/bin/python
# -*- coding: utf-8 -*-

#  Copyright (c) 2021 Poul Spang
#
#  This file, CheckSnapcast.py, is part of Project skill_MultiRoomMediaVolume.
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


import platform
import shlex
import subprocess
import time
from os import path #, symlink


# HELP TO DEVELOPMENT.
# sudo apt-get purge snapserver -y && sudo rm /dev/shm/snapfifo;cd ~/ProjectAlice;./venv/bin/pip uninstall snapcastcontrol -y
# Test stream
# ffmpeg -v 0 -y -rtbufsize 15M -i http://stream.srg-ssr.ch/m/rsj/aacp_96 -f u16le -acodec pcm_s16le -ac 2 -ar 48000 /dev/shm/snapfifo


SNAP_SERVER_RELEASE 	= '0.25.0'

_URL 			= 'https://github.com/badaix/snapcast/releases/download'
_WGET_URL = f"{_URL}/v{SNAP_SERVER_RELEASE}/snapserver_{SNAP_SERVER_RELEASE}"

_PLATFORM_MACHINE  = platform.machine()


class CheckSnapcast():

	#-----------------------------------------------
	@staticmethod
	def snapcastInstallPip(parent):
		_SNAPCASTCONTROL_VERSION = '0.1.0'

		if not path.exists('./venv/lib/python3.7/site-packages/snapcastcontrol'):
			cmd = shlex.split('./venv/bin/pip install snapcastcontrol')
			result = parent.Commons.runSystemCommand(cmd)
			if result.returncode:
				raise Exception(result.stderr)
		else:
			try:
				_output = subprocess.check_output(
					"/home/pi/ProjectAlice/venv/bin/pip show snapcastcontrol|grep Version|awk '{print $2}'",
					stderr=subprocess.STDOUT,
					shell=True
				).decode('utf-8').replace('\n','')

				if _output != _SNAPCASTCONTROL_VERSION:

					cmd = shlex.split('./venv/bin/pip install snapcastcontrol --upgrade')
					result = parent.Commons.runSystemCommand(cmd)
					if result.returncode:
						raise Exception(result.stderr)

			except subprocess.CalledProcessError as e:
				raise e


	#-----------------------------------------------
	@staticmethod
	def installSnapserver(parent):
		CheckSnapcast.snapcastInstallPip(parent)

		# cmd = 'snapserver --logging.sink=null --server.datadir=${HOME}.config/snapserver > /dev/null 2>&1 &'
		try:
			subprocess.check_output(
				"dpkg-query -l snapserver",
				stderr=subprocess.STDOUT,
				shell=True
			).decode('utf-8').replace('\n','')

			subprocess.call('sudo systemctl restart snapserver', shell=True)
			# we need this sleep, otherwise our snapcast server/clients will not be able to connect to the snapcast server we just started in the line above.
			time.sleep(1.0)

		except subprocess.CalledProcessError:
			# Install snapserver
			parent.logInfo(f'Checking dependencies **{parent.NAME}**')
			sedCmd1 	= shlex.split('sudo sed -i "s/doc_root = \/usr\/share\/snapserver\/snapweb/doc_root = \/home\/pi\/ProjectAlice\/skills\/MultiRoomMediaVolume\/snapweb\/aliceRadio/" /etc/snapserver.conf')
			sedCmd2 	= shlex.split('sudo sed -i "s/\.*source = pipe:\/\/\/tmp\/snapfifo?name=default/source = pipe:\/\/\/dev\/shm\/snapfifo?name=default/" /etc/snapserver.conf')
			sedCmd3 = shlex.split('sudo sed -i "s/\.*stream = pipe:\/\/\/tmp\/snapfifo?name=default/stream = pipe:\/\/\/dev\/shm\/snapfifo?name=default/" /etc/snapserver.conf')
			sedCmd4 = shlex.split('sudo sed -i "s/\.*User=snapserver/User=pi/" /lib/systemd/system/snapserver.service')
			sedCmd5 = shlex.split('sudo sed -i "s/\.*Group=snapserver/Group=pi/" /lib/systemd/system/snapserver.service')
			sedCmd6 = shlex.split('sudo sed -i "s/--logging.sink=system --server.datadir=\${HOME}/--logging.sink=null  --server.datadir=\${HOME}\/\.config\/snapserver/" /lib/systemd/system/snapserver.service')

			if _PLATFORM_MACHINE == "x86_64":
				if path.exists(f'./skills/MultiRoomMediaVolume/system/snapserver_0.25.0-1_amd64.deb'):
					#Is installed in the Docker image.
					cmd = "sudo apt-get install ./skills/MultiRoomMediaVolume/system/snapserver_0.25.0-1_amd64.deb -y >/dev/null 2>&1"
					subprocess.call(cmd, shell=True)
					subprocess.call('sudo apt-get -f install -y >/dev/null 2>&1', shell=True)


				else:
					downloadUrl = f"{_WGET_URL}-1_amd64.deb"
					snapServerDeb = f"snapserver_{SNAP_SERVER_RELEASE}-1_amd64.deb"
					subprocess.call(f'wget {downloadUrl} >/dev/null 2>&1', shell=True)
					subprocess.call(f'sudo dpkg -i  {snapServerDeb} >/dev/null 2>&1', shell=True)
					subprocess.call('sudo systemctl stop snapserver', shell=True)
					subprocess.call('sudo apt-get -f install -y >/dev/null 2>&1', shell=True)
					subprocess.call(f'sudo systemctl stop snapserver', shell=True)
					subprocess.call(f'rm {snapServerDeb} >/dev/null 2>&1', shell=True)

				subprocess.run(sedCmd1)
				subprocess.run(sedCmd2)
				subprocess.run(sedCmd3)
				subprocess.run(sedCmd4)
				subprocess.run(sedCmd5)
				subprocess.run(sedCmd6)

				# if not a Docker container
				# Tilføjet
				# subprocess.call('sudo systemctl daemon-reload', shell=True)
				subprocess.call('sudo systemctl restart snapserver', shell=True)
				# we need this sleep, otherwise our snapcast server/clients will not be able to connect to the snapcast server we just started in the line above.
				time.sleep(1.0)


			elif _PLATFORM_MACHINE == "armv7l" or _PLATFORM_MACHINE == "armv6l":
				if path.exists(f'./skills/MultiRoomMediaVolume/system/snapserver_0.25.0-1_armhf.deb'):
					cmd = "sudo apt-get install ./skills/MultiRoomMediaVolume/system/snapserver_0.25.0-1_armhf.deb -y"
					subprocess.call(cmd, shell=True)
					subprocess.call('sudo apt-get -f install -y >/dev/null 2>&1', shell=True)
					subprocess.call('sudo systemctl stop snapserver', shell=True)

				else:
					downloadUrl = f"{_WGET_URL}-1_armhf.deb"
					snapServerDeb = f"snapserver_{SNAP_SERVER_RELEASE}-1_armhf.deb"
					subprocess.call(f'wget {downloadUrl} >/dev/null 2>&1', shell=True)
					subprocess.call(f'sudo dpkg -i  {snapServerDeb} >/dev/null 2>&1', shell=True)
					subprocess.call('sudo apt-get -f install -y >/dev/null 2>&1', shell=True)
					subprocess.call(f'rm {snapServerDeb} >/dev/null 2>&1', shell=True)
					subprocess.call('sudo systemctl stop snapserver', shell=True)
					subprocess.call(f'rm {snapServerDeb} >/dev/null 2>&1', shell=True)

				subprocess.run(sedCmd1)
				subprocess.run(sedCmd2)
				subprocess.run(sedCmd3)
				subprocess.run(sedCmd4)
				subprocess.run(sedCmd5)
				subprocess.run(sedCmd6)
				#Tilføjet
				subprocess.call('sudo systemctl daemon-reload', shell=True)
				subprocess.call('sudo systemctl restart snapserver', shell=True)
				# we need this sleep, otherwise our snapcast server/clients will not be able to connect to the snapcast server we just started in the line above.
				time.sleep(1.0)

	#-----------------------------------------------
	@staticmethod
	def removeSnapserver():
		try:
			subprocess.check_output(
				"dpkg-query -l snapserver",
				stderr=subprocess.STDOUT,
				shell=True
			).decode('utf-8').replace('\n','')

			subprocess.call('sudo systemctl stop snapserver', shell=True)
			subprocess.call('sudo rm /dev/shm/snapfifo >/dev/null 2>&1', shell=True)
			subprocess.call('sudo apt-get purge snapserver -y >/dev/null 2>&1', shell=True)

		except subprocess.CalledProcessError:
			pass
