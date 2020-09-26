function getBMWState(alias, allowCache) {
    let url = "/bmw/state?vehicle=" + alias + "&allow_cache=" + allowCache
    fetch(url)
        .then(response => {
            if (!response.ok) {
                this.chargingStatus.innerText = "Unbekannt";
                this.soc.innerText = 0;
                this.range.innerText = "Unbekannt";
                throw Error(response.statusText);
            }
            return response.json();
        })
        .then(json => {
            console.log("Received updated vehicle state...");
            this.chargingStatus.innerText = this.prettyChargingStates[json["chargingStatus"]];
            this.soc.innerText = json["chargingLevelHv"];
            this.range.innerText = json["remainingRangeElectric"];

        });
}


function updateVehicleCard(card, allowCache = true) {
    if (card.dataset.manufacturer === "bmw") {
        console.log("unknown manufacturer for card");
        //getBMWState(card.dataset.alias, allowCache);
    } else {
        console.log("unknown manufacturer for card");
    }
}

class VehicleCard {
    constructor(node) {
        this.rootNode = node;
        this.alias = this.rootNode.getAttribute('data-alias');
        this.name = this.rootNode.getAttribute("data-name");

        this.registerEventHandlers()

    }

    registerEventHandlers() {
        this.rootNode.getElementsByClassName("vehicle-manual-refresh")[0].addEventListener("click", this.requestManualRefresh.bind(this))
    }

    update() {
    }

    requestManualRefresh() {
        this.getState(false);
    }

    createRequestUrl(requestTarget, queryString = "") {
        queryString = "?vehicle=" + this.alias + "&" + queryString;
        return requestTarget + queryString;
    }

    getState(allowCache = false){
        throw "getState is abstract for VehicleCard"
    }
}



class BMWVehicleCard extends VehicleCard{

    prettyChargingStates = {
        INVALID: "Nicht verbunden",
        NOT_CHARGING: "Verbunden",
        FINISHED_NOT_FULL: "Laden abgeschlossen",
        FINISHED_FULLY_CHARGED: "Vollständig geladen",
        ERROR: "Fehler",
        CHARGING: "Ladung läuft",
        WAITING_FOR_CHARGING: "Wartet auf Wallbox"
    };


    constructor(node) {
        super(node);

        this.image = this.rootNode.getElementsByClassName("vehicle-thumbnail")[0];
        this.soc = this.rootNode.getElementsByClassName("vehicle-soc")[0];
        this.range = this.rootNode.getElementsByClassName("vehicle-range")[0];
        this.lastUpdate = this.rootNode.getElementsByClassName("vehicle-last-update")[0];
        this.chargingStatus = this.rootNode.getElementsByClassName("vehicle-status")[0];


        this.update();

    }

    update(){
        super.update()
        this.getState();
        this.getLastUpdate();
    }

    getLastUpdate() {
        let url = this.createRequestUrl("/bmw/last_update");

        fetch(url)
            .then(response => {
                if (!response.ok){
                    this.lastUpdate.innerText = "Unbekannt";
                    throw Error(response.statusText);
                }
                return response.json()
            })
            .then(json => {
                console.log("Received updated recent_data timestamp for " + this.name + "...");
                let ts = new Date(json["last_update"] * 1000);
                this.lastUpdate.innerText = ts.toLocaleDateString('de-DE', config["dateFormat"]);
            });
    }

    getState(allowCache = true) {
        let url = this.createRequestUrl("/bmw/state", "allow_cache=" + allowCache);
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    this.chargingStatus.innerText = "Unbekannt";
                    this.soc.innerText = 0;
                    this.range.innerText = "Unbekannt";
                    throw Error(response.statusText);
                }
                return response.json();
            })
            .then(json => {
                console.log("Received updated vehicle state for " + this.name + "...");
                this.chargingStatus.innerText = this.prettyChargingStates[json["chargingStatus"]];
                this.soc.innerText = json["chargingLevelHv"];
                this.range.innerText = json["remainingRangeElectric"];

            });
    }
}

function createVehicleCardObjects() {
    let vehicleCards = [];
    let vehicleCardNodes = document.getElementsByClassName("vehicle-info-card");
    for (let node of vehicleCardNodes) {
        let manufacturer = node.dataset.manufacturer;
        if (manufacturer === "bmw") {
            let card = new BMWVehicleCard(node);
            vehicleCards.push(card);
        } else {
            console.log("Unknown vehicle manufacturer " + manufacturer + ". No suitable card constructor available.");
        }
    }
    return vehicleCards
}