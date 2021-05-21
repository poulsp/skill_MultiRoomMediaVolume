class MultiRoomMediaVolume_MultiRoomMediaVolume extends Widget {

	//-----------------------------------------------
	constructor(uid, widgetId) {
		super(uid, widgetId);

		this.widgetId = widgetId
		this.uid = uid

		this.aliceSettings = JSON.parse(window.sessionStorage.aliceSettings);

		this.myIframe = document.querySelector(`[data-ref="MultiRoomMediaVolume_controls_${this.uid}"]`)
		this.myExplanationDiv = document.querySelector(`[data-ref="MultiRoomMediaVolume_explanation_${this.uid}"]`)
		this.Myimg = document.querySelector(`[data-ref="MultiRoomMediaVolume_img_${this.uid}"]`)

		this.myIframe.style.display = "none";

		this.getBaseData()
		//this.subscribe('psp/radiomanager/widget/refresh', this.getBaseData)
	}


/*
	//-----------------------------------------------
	getWidgetSize() {

		fetch(`http://${this.aliceSettings['aliceIp']}:${this.aliceSettings['apiPort']}/api/v1.0.1/widgets/`, {
		  "method": "GET",
		  "headers": {
		    "auth": localStorage.getItem('apiToken')
	  }
		})
		.then((r) => r.json())
		.then((data) => {
			this.settings = data.widgets[this.widgetId].settings
		})
		.then(() => this.changeWidgetSize())


	}

	//TODO
	//-----------------------------------------------
	changeWidgetSize() {
		fetch(`http://${this.aliceSettings['aliceIp']}:${this.aliceSettings['apiPort']}/api/v1.0.1/widgets/${this.widgetId}/saveSize/`, {
		  method: 'PATCH',
		  body: `{ "x": ${this.settings.x}, "y": ${this.settings.y}, "w": 382, "h": 500 }`,
			headers: {
				'auth': localStorage.getItem('apiToken'),
				'content-type': 'application/json'
			},
		})
		//.then(() => this.showMediaVolume())
		.then(() => this.checkVolumeWidgetDisplay())

}
*/

	//-----------------------------------------------
	getBaseData() {
		fetch(`http://${this.aliceSettings['aliceIp']}:${this.aliceSettings['apiPort']}/api/v1.0.1/widgets/${this.widgetId}/function/baseData/`, {
			method: 'POST',
			body: '{}',
			headers: {
				'auth': localStorage.getItem('apiToken'),
				'content-type': 'application/json'
			}
		})
			// What is that for a contruct (r)??
			.then((r) => r.json())
				.then((data) => {
				this.siteIsUp = data.data.siteIsUp
			})
			.then(() => this.checkVolumeWidgetDisplay())
			//.then(() => this.getWidgetSize())

	}
				//this.snapcastPort = data.data.snapcastPort


	//-----------------------------------------------
	checkVolumeWidgetDisplay() {
		if (this.siteIsUp) {
			this.myExplanationDiv.style.display = "none";
			this.Myimg.style.display = "none";
			this.myIframe.style.display = "block";
			this.showMediaVolume()
		}
		else {
			this.myIframe.style.display = "none";
			//this.Myimg.src = `http://${window.location.hostname}:5001/api/v1.0.1/widgets/resources/img/MultiRoomMediaVolume/MultiRoomMediaVolumeWidget.png`
			//this.Myimg.src = `http://${this.aliceSettings['aliceIp']}:${this.aliceSettings['apiPort']}/api/v1.0.1/widgets/resources/img/MultiRoomMediaVolume/MultiRoomMediaVolumeWidget.png`
			//this.Myimg.style.display = "block";

			this.myExplanationDiv.style.display = "block";
		}
	}


	//-----------------------------------------------
	showMediaVolume() {
		this.myIframe.src = `http://${this.aliceSettings['aliceIp']}:1780`
	}

}
