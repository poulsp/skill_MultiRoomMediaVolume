"use strict";
class Host {
    constructor(json) {
        this.arch = "";
        this.ip = "";
        this.mac = "";
        this.name = "";
        this.os = "";
        this.fromJson(json);
    }
    fromJson(json) {
        this.arch = json.arch;
        this.ip = json.ip;
        this.mac = json.mac;
        this.name = json.name;
        this.os = json.os;
    }
}
class Client {
    constructor(json) {
        this.id = "";
        this.connected = false;
        this.fromJson(json);
    }
    fromJson(json) {
        this.id = json.id;
        this.host = new Host(json.host);
        let jsnapclient = json.snapclient;
        this.snapclient = { name: jsnapclient.name, protocolVersion: jsnapclient.protocolVersion, version: jsnapclient.version };
        let jconfig = json.config;
        this.config = { instance: jconfig.instance, latency: jconfig.latency, name: jconfig.name, volume: { muted: jconfig.volume.muted, percent: jconfig.volume.percent } };
        this.lastSeen = { sec: json.lastSeen.sec, usec: json.lastSeen.usec };
        this.connected = Boolean(json.connected);
    }
}
class Group {
    constructor(json) {
        this.name = "";
        this.id = "";
        this.stream_id = "";
        this.muted = false;
        this.clients = [];
        this.fromJson(json);
    }
    fromJson(json) {
        this.name = json.name;
        this.id = json.id;
        this.stream_id = json.stream_id;
        this.muted = Boolean(json.muted);
        for (let client of json.clients)
            this.clients.push(new Client(client));
    }
    getClient(id) {
        for (let client of this.clients) {
            if (client.id == id)
                return client;
        }
        return null;
    }
}
class Stream {
    constructor(json) {
        this.id = "";
        this.status = "";
        this.fromJson(json);
    }
    fromJson(json) {
        this.id = json.id;
        this.status = json.status;
        let juri = json.uri;
        this.uri = { raw: juri.raw, scheme: juri.scheme, host: juri.host, path: juri.path, fragment: juri.fragment, query: juri.query };
    }
}
class Server {
    constructor(json) {
        this.groups = [];
        this.streams = [];
        if (json)
            this.fromJson(json);
    }
    fromJson(json) {
        this.groups = [];
        for (let jgroup of json.groups)
            this.groups.push(new Group(jgroup));
        let jsnapserver = json.server.snapserver;
        this.server = { host: new Host(json.server.host), snapserver: { controlProtocolVersion: jsnapserver.controlProtocolVersion, name: jsnapserver.name, protocolVersion: jsnapserver.protocolVersion, version: jsnapserver.version } };
        this.streams = [];
        for (let jstream of json.streams) {
            this.streams.push(new Stream(jstream));
        }
    }
    getClient(id) {
        for (let group of this.groups) {
            let client = group.getClient(id);
            if (client)
                return client;
        }
        return null;
    }
    getGroup(id) {
        for (let group of this.groups) {
            if (group.id == id)
                return group;
        }
        return null;
    }
    getStream(id) {
        for (let stream of this.streams) {
            if (stream.id == id)
                return stream;
        }
        return null;
    }
}
class SnapControl {
    constructor(baseUrl) {
        this.server = new Server();
        this.baseUrl = baseUrl;
        //        this.baseUrl = 'ws://localhost:1780';
        this.msg_id = 0;
        this.status_req_id = -1;
        this.connect();
    }
    connect() {
        this.connection = new WebSocket(this.baseUrl + '/jsonrpc');
        this.connection.onmessage = (msg) => this.onMessage(msg.data);
        this.connection.onopen = () => { this.status_req_id = this.sendRequest('Server.GetStatus'); };
        this.connection.onerror = (ev) => { console.error('error:', ev); };
        this.connection.onclose = () => {
            console.info('connection lost, reconnecting in 1s');
            setTimeout(() => this.connect(), 1000);
        };
    }
    action(answer) {
        switch (answer.method) {
            case 'Client.OnVolumeChanged':
                let client = this.getClient(answer.params.id);
                client.config.volume = answer.params.volume;
                updateGroupVolume(this.getGroupFromClient(client.id));
                break;
            case 'Client.OnLatencyChanged':
                this.getClient(answer.params.id).config.latency = answer.params.latency;
                break;
            case 'Client.OnNameChanged':
                this.getClient(answer.params.id).config.name = answer.params.name;
                break;
            case 'Client.OnConnect':
            case 'Client.OnDisconnect':
                this.getClient(answer.params.client.id).fromJson(answer.params.client);
                break;
            case 'Group.OnMute':
                this.getGroup(answer.params.id).muted = Boolean(answer.params.mute);
                break;
            case 'Group.OnStreamChanged':
                this.getGroup(answer.params.id).stream_id = answer.params.stream_id;
                break;
            case 'Stream.OnUpdate':
                this.getStream(answer.params.id).fromJson(answer.params.stream);
                break;
            case 'Server.OnUpdate':
                this.server.fromJson(answer.params.server);
                break;
            default:
                break;
        }
    }
    getClient(client_id) {
        let client = this.server.getClient(client_id);
        if (client == null) {
            throw new Error(`client ${client_id} was null`);
        }
        return client;
    }
    getGroup(group_id) {
        let group = this.server.getGroup(group_id);
        if (group == null) {
            throw new Error(`group ${group_id} was null`);
        }
        return group;
    }
    getGroupVolume(group, online) {
        if (group.clients.length == 0)
            return 0;
        let group_vol = 0;
        let client_count = 0;
        for (let client of group.clients) {
            if (online && !client.connected)
                continue;
            group_vol += client.config.volume.percent;
            ++client_count;
        }
        if (client_count == 0)
            return 0;
        return group_vol / client_count;
    }
    getGroupFromClient(client_id) {
        for (let group of this.server.groups)
            for (let client of group.clients)
                if (client.id == client_id)
                    return group;
        throw new Error(`group for client ${client_id} was null`);
    }
    getStream(stream_id) {
        let stream = this.server.getStream(stream_id);
        if (stream == null) {
            throw new Error(`stream ${stream_id} was null`);
        }
        return stream;
    }
    setVolume(client_id, percent, mute) {
        percent = Math.max(0, Math.min(100, percent));
        let client = this.getClient(client_id);
        client.config.volume.percent = percent;
        if (mute != undefined)
            client.config.volume.muted = mute;
        this.sendRequest('Client.SetVolume', { id: client_id, volume: { muted: client.config.volume.muted, percent: client.config.volume.percent } });
    }
    setClientName(client_id, name) {
        let client = this.getClient(client_id);
        let current_name = (client.config.name != "") ? client.config.name : client.host.name;
        if (name != current_name) {
            this.sendRequest('Client.SetName', { id: client_id, name: name });
            client.config.name = name;
        }
    }
    setClientLatency(client_id, latency) {
        let client = this.getClient(client_id);
        let current_latency = client.config.latency;
        if (latency != current_latency) {
            this.sendRequest('Client.SetLatency', { id: client_id, latency: latency });
            client.config.latency = latency;
        }
    }
    deleteClient(client_id) {
        this.sendRequest('Server.DeleteClient', { id: client_id });
        this.server.groups.forEach((g, gi) => {
            g.clients.forEach((c, ci) => {
                if (c.id == client_id) {
                    this.server.groups[gi].clients.splice(ci, 1);
                }
            });
        });
        this.server.groups.forEach((g, gi) => {
            if (g.clients.length == 0) {
                this.server.groups.splice(gi, 1);
            }
        });
        show();
    }
    setStream(group_id, stream_id) {
        this.getGroup(group_id).stream_id = stream_id;
        this.sendRequest('Group.SetStream', { id: group_id, stream_id: stream_id });
    }
    setClients(group_id, clients) {
        this.status_req_id = this.sendRequest('Group.SetClients', { id: group_id, clients: clients });
    }
    muteGroup(group_id, mute) {
        this.getGroup(group_id).muted = mute;
        this.sendRequest('Group.SetMute', { id: group_id, mute: mute });
    }
    sendRequest(method, params) {
        let msg = {
            id: ++this.msg_id,
            jsonrpc: '2.0',
            method: method
        };
        if (params)
            msg.params = params;
        let msgJson = JSON.stringify(msg);
        console.log("Sending: " + msgJson);
        this.connection.send(msgJson);
        return this.msg_id;
    }
    onMessage(msg) {
        let answer = JSON.parse(msg);
        let is_response = (answer.id != undefined);
        console.log("Received " + (is_response ? "response" : "notification") + ", json: " + JSON.stringify(answer));
        if (is_response) {
            if (answer.id == this.status_req_id) {
                this.server = new Server(answer.result.server);
                show();
            }
        }
        else {
            if (Array.isArray(answer)) {
                for (let a of answer) {
                    this.action(a);
                }
            }
            else {
                this.action(answer);
            }
            // TODO: don't update everything, but only the changed,
            // e.g. update the values for the volume sliders
            show();
        }
    }
}
let snapcontrol;
let snapstream = null;
let hide_offline = true;
let autoplay_done = false;
//???let storageEnabled = false
function autoplayRequested() {
    return document.location.hash.match(/autoplay/) !== null;
}
//PS
function showDropdown() {
    let dropdownElem = document.getElementById('dropdown');
    dropdownElem.classList.toggle('special');
    const myDropdown = document.getElementById("myDropdown");
    myDropdown.classList.toggle("show");
}
//PS
function checkOfflineClients() {
    const checkbox = document.getElementById("offline_clients");
    (checkbox.checked ? 'false' : 'true');
    hide_offline = (checkbox.checked ? false : true);
    localStorage.setItem("hide_offline", hide_offline.toString());
    show();
}
function show() {
    // Render the page
    const versionElem = document.getElementsByTagName("meta").namedItem("version");
    console.log("Snapweb version " + (versionElem ? versionElem.content : "null"));
    let play_img;
    if (snapstream) {
        play_img = 'stop.png';
    }
    else {
        play_img = 'play.png';
    }
    let content = "";
    content += "<div class='navbar'>Radio Alice Snapcast";
    let serverVersion = snapcontrol.server.server.snapserver.version.split('.');
    if ((serverVersion.length >= 2) && (+serverVersion[1] >= 21)) {
        content += "    <img src='" + play_img + "' class='play-button' id='play-button'></a>";
        //PS
        content += "    <div id='dropdown' class='dropdown btn-right showLeft' onclick='showDropdown()'>";
        content += "      <div id='myDropdown' class='dropdown-content'>";
        content += "        <input type='checkbox' id='offline_clients' name='offline_clients' value='true' onclick='checkOfflineClients()' >";
        content += "        <label for='offline_clients'> Show offline clients </label>";
        content += "      </div>";
        content += "    </div>";
        // Stream became ready and was not playing. If autoplay is requested, start playing.
        if (!snapstream && !autoplay_done && autoplayRequested()) {
            autoplay_done = true;
            play();
        }
    }
    content += "</div>";
    content += "<div class='content'>";
    let server = snapcontrol.server;
    for (let group of server.groups) {
        if (hide_offline) {
            let groupActive = false;
            for (let client of group.clients) {
                if (client.connected) {
                    groupActive = true;
                    break;
                }
            }
            if (!groupActive)
                continue;
        }
        // Set mute variables
        let classgroup;
        let muted;
        let mute_img;
        if (group.muted == true) {
            classgroup = 'group muted';
            muted = true;
            mute_img = 'mute_icon.png';
        }
        else {
            classgroup = 'group';
            muted = false;
            mute_img = 'speaker_icon.png';
        }
        // Start group div
        content += "<div id='g_" + group.id + "' class='" + classgroup + "'>";
        // Create stream selection dropdown
        let streamselect = "<select id='stream_" + group.id + "' onchange='setStream(\"" + group.id + "\")' class='stream'>";
        for (let i_stream = 0; i_stream < server.streams.length; i_stream++) {
            let streamselected = "";
            if (group.stream_id == server.streams[i_stream].id) {
                streamselected = 'selected';
            }
            streamselect += "<option value='" + server.streams[i_stream].id + "' " + streamselected + ">" + server.streams[i_stream].id + ": " + server.streams[i_stream].status + "</option>";
        }
        streamselect += "</select>";
        // Group mute and refresh button
        content += "<div class='groupheader'>";
        content += streamselect;
        let clientCount = 0;
        for (let client of group.clients)
            if (!hide_offline || client.connected)
                clientCount++;
        if (clientCount > 1) {
            let volume = snapcontrol.getGroupVolume(group, hide_offline);
            content += "<a href=\"javascript:setMuteGroup('" + group.id + "'," + !muted + ");\"><img src='" + mute_img + "' class='mute-button'></a>";
            content += "<div class='slidergroupdiv'>";
            //PS
            content += "    <input type='range' draggable='false' min=0 max=100 step=1 id='vol_" + group.id + "' oninput='javascript:setGroupVolume(\"" + group.id + "\")' value=" + volume + " class='slider'>";
            content += "        <p class='slideroutput'>&nbsp<span id='group_vol_" + group.id + "'></span></p>";
            // content += "    <input type='range' min=0 max=100 step=1 id='vol_" + group.id + "' oninput='javascript:setVolume(\"" + client.id + "\"," + client.config.volume.muted + ")' value=" + client.config.volume.percent + " class='" + sliderclass + "'>";
            content += "</div>";
        }
        // transparent placeholder edit icon
        content += "<div class='edit-group-icon'>&#9998</div>";
        content += "</div>";
        content += "<hr class='groupheader-separator'>";
        // Create clients in group
        for (let client of group.clients) {
            if (!client.connected && hide_offline)
                continue;
            // Set name and connection state vars, start client div
            let name;
            let clas = 'client';
            if (client.config.name != "") {
                name = client.config.name;
            }
            else {
                name = client.host.name;
            }
            if (client.connected == false) {
                clas = 'client disconnected';
            }
            content += "<div id='c_" + client.id + "' class='" + clas + "'>";
            // Client mute status vars
            let muted;
            let mute_img;
            let sliderclass;
            if (client.config.volume.muted == true) {
                muted = true;
                sliderclass = 'slider muted';
                mute_img = 'mute_icon.png';
            }
            else {
                sliderclass = 'slider';
                muted = false;
                mute_img = 'speaker_icon.png';
            }
            // Populate client div
            content += "<a href=\"javascript:setVolume('" + client.id + "'," + !muted + ");\"><img src='" + mute_img + "' class='mute-button'></a>";
            content += "    <div class='sliderdiv'>";
            //PS
            content += "        <input type='range' min=0 max=100 step=1 id='vol_" + client.id + "' oninput='javascript:setVolume(\"" + client.id + "\"," + client.config.volume.muted + ")' value=" + client.config.volume.percent + " class='" + sliderclass + "'>";
            content += "        <p class='slideroutput'>&nbsp<span id='client_vol_" + client.id + "'>" + client.config.volume.percent + "%</span></p>";
            //            content += "        <p class='slideroutput'>&nbsp<span id='client_vol_" + client.id + "'></span></p>";
            content += "    </div>";
            content += "    <span class='edit-icons'>";
            content += "        <a href=\"javascript:openClientSettings('" + client.id + "');\" class='edit-icon'>&#9998</a>";
            if (client.connected == false) {
                content += "      <a href=\"javascript:deleteClient('" + client.id + "');\" class='delete-icon'>&#128465</a>";
                content += "   </span>";
            }
            else {
                content += "</span>";
            }
            content += "    <div class='name'>" + name + "</div>";
            content += "</div>";
        }
        content += "</div>";
    }
    content += "</div>"; // content
    content += "<div id='client-settings' class='client-settings'>";
    content += "    <div class='client-setting-content'>";
    content += "        <form action='javascript:closeClientSettings()'>";
    content += "        <label for='client-name'>Name</label>";
    content += "        <input type='text' class='client-input' id='client-name' name='client-name' placeholder='Client name..'>";
    content += "        <label for='client-latency'>Latency</label>";
    content += "        <input type='number' class='client-input' min='-10000' max='10000' id='client-latency' name='client-latency' placeholder='Latency in ms..'>";
    content += "        <label for='client-group'>Group</label>";
    content += "        <select id='client-group' class='client-input' name='client-group'>";
    content += "        </select>";
    content += "        <input type='submit' value='Submit'>";
    content += "        </form>";
    content += "    </div>";
    content += "</div>";
    // Pad then update page
    content = content + "<br><br>";
    document.getElementById('show').innerHTML = content;
    let playElem = document.getElementById('play-button');
    playElem.onclick = () => {
        play();
    };
    for (let group of snapcontrol.server.groups) {
        if (group.clients.length > 1) {
            let slider = document.getElementById("vol_" + group.id);
            if (slider == null)
                continue;
            let output = document.getElementById('group_vol_' + group.id);
            ;
            output.innerHTML = slider.value + "%";
            slider.addEventListener('pointerdown', function () {
                groupVolumeEnter(group.id);
            });
            slider.addEventListener('touchstart', function () {
                groupVolumeEnter(group.id);
            });
        }
        for (let group of snapcontrol.server.groups) {
            if (group.clients.length > 1) {
                //clients = group.clients
                for (let client of group.clients) {
                    let slider = document.getElementById('vol_' + client.id);
                    if (slider) {
                        let output = document.getElementById('client_vol_' + client.id);
                        ;
                        output.innerHTML = slider.value + "%";
                    }
                }
            }
        }
    }
    //PS
    // set  hide_offline in browser datastore
    const checkbox = document.getElementById("offline_clients");
    checkbox.checked = !hide_offline;
}
function updateGroupVolume(group) {
    let group_vol = snapcontrol.getGroupVolume(group, hide_offline);
    let slider = document.getElementById("vol_" + group.id);
    if (slider == null)
        return;
    console.log("updateGroupVolume group: " + group.id + ", volume: " + group_vol + ", slider: " + (slider != null));
    slider.value = String(group_vol);
    let output = document.getElementById('group_vol_' + group.id);
    ;
    output.innerHTML = slider.value + "%";
}
let client_volumes;
let group_volume;
function setGroupVolume(group_id) {
    let group = snapcontrol.getGroup(group_id);
    let percent = document.getElementById('vol_' + group.id).valueAsNumber;
    console.log("setGroupVolume id: " + group.id + ", volume: " + percent);
    // show()
    let delta = percent - group_volume;
    let ratio;
    if (delta < 0)
        ratio = (group_volume - percent) / group_volume;
    else
        ratio = (percent - group_volume) / (100 - group_volume);
    for (let i = 0; i < group.clients.length; ++i) {
        let new_volume = client_volumes[i];
        if (delta < 0)
            new_volume -= ratio * client_volumes[i];
        else
            new_volume += ratio * (100 - client_volumes[i]);
        let client_id = group.clients[i].id;
        // TODO: use batch request to update all client volumes at once
        let groupSlider = document.getElementById('vol_' + group.id);
        let output = document.getElementById('group_vol_' + group.id);
        ;
        output.innerHTML = groupSlider.value + "%";
        snapcontrol.setVolume(client_id, new_volume);
        let slider = document.getElementById('vol_' + client_id);
        if (slider) {
            slider.value = String(new_volume);
            //PS
            let output = document.getElementById('client_vol_' + client_id);
            ;
            output.innerHTML = slider.value + "%";
        }
    }
}
function groupVolumeEnter(group_id) {
    let group = snapcontrol.getGroup(group_id);
    let percent = document.getElementById('vol_' + group.id).valueAsNumber;
    console.log("groupVolumeEnter id: " + group.id + ", volume: " + percent);
    group_volume = percent;
    //PS
    let slider = document.getElementById('vol_' + group.id);
    let output = document.getElementById('group_vol_' + group.id);
    ;
    output.innerHTML = slider.value + "%";
    client_volumes = [];
    for (let i = 0; i < group.clients.length; ++i) {
        client_volumes.push(group.clients[i].config.volume.percent);
        let slider = document.getElementById('vol_' + group.clients[i].id);
        if (slider) {
            let output = document.getElementById('client_vol_' + group.clients[i].id);
            output.innerHTML = slider.value + "%";
        }
    }
    // show()
}
function setVolume(id, mute) {
    console.log("setVolume id: " + id + ", mute: " + mute);
    let percent = document.getElementById('vol_' + id).valueAsNumber;
    let client = snapcontrol.getClient(id);
    let needs_update = (mute != client.config.volume.muted);
    snapcontrol.setVolume(id, percent, mute);
    let slider = document.getElementById('vol_' + id);
    //PS
    let output = document.getElementById('client_vol_' + id);
    ;
    output.innerHTML = slider.value + "%";
    let group = snapcontrol.getGroupFromClient(id);
    updateGroupVolume(group);
    if (needs_update)
        show();
}
function play() {
    if (snapstream) {
        snapstream.stop();
        snapstream = null;
    }
    else {
        snapstream = new SnapStream(config.baseUrl);
        //        snapstream = new SnapStream('ws://localhost:1780');
    }
    show();
}
function setMuteGroup(id, mute) {
    snapcontrol.muteGroup(id, mute);
    show();
}
function setStream(id) {
    snapcontrol.setStream(id, document.getElementById('stream_' + id).value);
    show();
}
function setGroup(client_id, group_id) {
    console.log("setGroup id: " + client_id + ", group: " + group_id);
    let server = snapcontrol.server;
    // Get client group id
    let current_group = snapcontrol.getGroupFromClient(client_id);
    // Get
    //   List of target group's clients
    // OR
    //   List of current group's other clients
    let send_clients = [];
    for (let i_group = 0; i_group < server.groups.length; i_group++) {
        if (server.groups[i_group].id == group_id || (group_id == "new" && server.groups[i_group].id == current_group.id)) {
            for (let i_client = 0; i_client < server.groups[i_group].clients.length; i_client++) {
                if (group_id == "new" && server.groups[i_group].clients[i_client].id == client_id) { }
                else {
                    send_clients[send_clients.length] = server.groups[i_group].clients[i_client].id;
                }
            }
        }
    }
    if (group_id == "new")
        group_id = current_group.id;
    else
        send_clients[send_clients.length] = client_id;
    snapcontrol.setClients(group_id, send_clients);
}
function setName(id) {
    // Get current name and lacency
    let client = snapcontrol.getClient(id);
    let current_name = (client.config.name != "") ? client.config.name : client.host.name;
    let current_latency = client.config.latency;
    let new_name = window.prompt("New Name", current_name);
    let new_latency = Number(window.prompt("New Latency", String(current_latency)));
    if (new_name != null)
        snapcontrol.setClientName(id, new_name);
    if (new_latency != null)
        snapcontrol.setClientLatency(id, new_latency);
    show();
}
function openClientSettings(id) {
    let modal = document.getElementById("client-settings");
    let client = snapcontrol.getClient(id);
    let current_name = (client.config.name != "") ? client.config.name : client.host.name;
    let name = document.getElementById("client-name");
    name.name = id;
    name.value = current_name;
    let latency = document.getElementById("client-latency");
    latency.valueAsNumber = client.config.latency;
    let group = snapcontrol.getGroupFromClient(id);
    let group_input = document.getElementById("client-group");
    while (group_input.length > 0)
        group_input.remove(0);
    let group_num = 0;
    for (let ogroup of snapcontrol.server.groups) {
        let option = document.createElement('option');
        option.value = ogroup.id;
        option.text = "Group " + (group_num + 1) + " (" + ogroup.clients.length + " Clients)";
        group_input.add(option);
        if (ogroup == group) {
            console.log("Selected: " + group_num);
            group_input.selectedIndex = group_num;
        }
        ++group_num;
    }
    let option = document.createElement('option');
    option.value = option.text = "new";
    group_input.add(option);
    modal.style.display = "block";
}
function closeClientSettings() {
    let name = document.getElementById("client-name");
    let id = name.name;
    console.log("onclose " + id + ", value: " + name.value);
    snapcontrol.setClientName(id, name.value);
    let latency = document.getElementById("client-latency");
    snapcontrol.setClientLatency(id, latency.valueAsNumber);
    let group_input = document.getElementById("client-group");
    let option = group_input.options[group_input.selectedIndex];
    setGroup(id, option.value);
    let modal = document.getElementById("client-settings");
    modal.style.display = "none";
    show();
}
function deleteClient(id) {
    let client = snapcontrol.getClient(id);
    //PS
    let name = client.config.name;
    if (name == "")
        name = client.host.name;
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
        snapcontrol.deleteClient(id);
    }
}
//PS
function setCookieHideOffline(key, value, exdays = -1) {
    let d = new Date();
    if (exdays < 0)
        exdays = 10 * 365;
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    let expires = "expires=" + d.toUTCString();
    document.cookie = key + "=" + value + ";" + expires + ";sameSite=Strict;path=/";
}
//PS
function getCookieHideOffline(cname) {
    let name = cname + "=";
    let ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}
window.onload = function () {
    snapcontrol = new SnapControl(config.baseUrl);
    //PS
    // set/get  hide_offline in browser datastore
    if (typeof (Storage) !== "undefined") {
        //??        storageEnabled = true
        let valueOfHideOffline = localStorage.getItem("hide_offline");
        if (valueOfHideOffline == null) {
            // Store
            localStorage.setItem("hide_offline", hide_offline.toString());
            valueOfHideOffline = hide_offline.toString();
        }
        hide_offline = (valueOfHideOffline === 'true');
    }
    else {
        console.warn("Sorry! No Web Storage support..");
        /*
                // Fallback to cookies if localStorage is not available.
        //??        storageEnabled = false
                let valueOfHideOffline = localStorage.getItem("hide_offline")
        
                if (!valueOfHideOffline) {
                    // Store
                    setCookie("hide_offline", hide_offline.toString())
                }
        
        */
        /*
                // Fallback to cookies if localStorage is not available.
                let name = key + "=";
                let decodedCookie = decodeURIComponent(document.cookie);
                let ca = decodedCookie.split(';');
                for (let c of ca) {
                    c = c.trimLeft();
                    if (c.indexOf(name) == 0) {
                        return c.substring(name.length, c.length);
                    }
                }
                setCookie(key, defaultValue);
                return defaultValue;
        */
    }
    /*
    //    if (Boolean(valueOfHideOffline)) {
            //console.warn("valueOfHideOffline: " + valueOfHideOffline)
            console.warn("localStorage.getItem('hide_offline'): " + localStorage.getItem("hide_offline"))
    //        let valueOfHideOffline = localStorage.getItem("hide_offline")
            let valueOfHideOffline = (localStorage.getItem("hide_offline") === 'true');
            console.warn("valueOfHideOffline: " + typeof valueOfHideOffline)
            console.warn("valueOfHideOffline: " + valueOfHideOffline)
    
            hide_offline = valueOfHideOffline
    */
    //}
    //     if (hide_offline1) { console.warn("hide_offline1: " + hide_offline1) }
};
// When the user clicks anywhere outside of the modal, close it
window.onclick = function (event) {
    let modal = document.getElementById("client-settings");
    if (event.target == modal) {
        modal.style.display = "none";
    }
};
//# sourceMappingURL=snapcontrol.js.map