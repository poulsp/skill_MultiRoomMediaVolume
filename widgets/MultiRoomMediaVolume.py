import urllib.request
#import json
import sqlite3

from core.webui.model.Widget import Widget
from core.webui.model.WidgetSizes import WidgetSizes


class MultiRoomMediaVolume(Widget):

	# w_large: 300x300
	# w_large_wide: 400x300
	# w_large_tall: 300x400
	# w_extralarge: 500x500
	# w_extralarge_wide: 700x500
	# w_extralarge_tall: 500x700

	#DEFAULT_SIZE = WidgetSizes.w_extralarge_wide
	DEFAULT_SIZE = WidgetSizes.w_small
	DEFAULT_OPTIONS: dict = dict()

	def __init__(self, data: sqlite3.Row):
		super().__init__(data)

		if self.settings:
			self.settings['title'] = False
			self.settings['borders'] = False
			self.w = self.skillInstance.getConfig('widgetSizeW')
			self.h = self.skillInstance.getConfig('widgetSizeH')

			# self.w = 382
			# self.h = 468


	##-----------------------------------------------
	def baseData(self) -> dict:

		siteIsUp = False
		try:
			webUrl  = urllib.request.urlopen(f"http://localhost:1780")
			siteIsUp = webUrl.getcode() == 200
		except Exception:
			siteIsUp = False

		return {
			'siteIsUp': siteIsUp
		}
