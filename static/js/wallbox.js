function toggleAutoMode(enable) {
    let url = "/manager/mode";
    if (enable) {
        url += "?mode=automatic";
    } else {
        url += "?mode=manual";
    }
    fetch(url, {method: "PUT"})
        .then(response => {
            if (!response.ok) {
                throw Error(response.statusText);
            }
            return response.json()
        })
        .then(json => {
            console.log("changed manager mode");
        }).catch((error) => {
        console.error('Could not get new manager mode info:', error);
    });
}

function changeWallboxPowerLimit(power){
    let url = "/manager/limit?limit="+power;

    fetch(url, {method: "PUT"})
        .then(response => {
            if (!response.ok) {
                throw Error(response.statusText);
            }
            return response.json()
        })
        .then(json => {
            console.log("changed manager manual power limit");
        }).catch((error) => {
        console.error('Could not set new manual power limit:', error);
    });
}

document.getElementById("wallbox-mode-toggle").addEventListener('change', function () {
    if (this.checked) {
        document.getElementById("wallbox-manual-charge-menu").classList.add("is-hidden");
    } else {
        document.getElementById("wallbox-manual-charge-menu").classList.remove("is-hidden");
    }
    toggleAutoMode(this.checked)
});

document.getElementById("wallbox-manual-current").addEventListener("change", function(){
    changeWallboxPowerLimit(this.value);
})

window.setInterval(function () {
    if (document.getElementById("wallbox-mode-toggle").checked) {
        document.getElementById("wallbox-manual-charge-menu").classList.add("is-hidden");
    } else {
        document.getElementById("wallbox-manual-charge-menu").classList.remove("is-hidden");
    }
}, 1000);

window.setInterval(function () {
    fetch("/manager/mode")
        .then(response => {
            if (!response.ok) {
                throw Error(response.statusText);
            }
            return response.json()
        })
        .then(json => {
            document.getElementById("wallbox-mode-toggle").checked = json["mode"] !== "manual";
            console.log("Received mode info from manager");
        }).catch((error) => {
        console.error('Could not get new manager mode info:', error);
    });
}, 2000)

class WallboxCard {
    constructor() {
        this.root = document.getElementById("wallbox-info-box");
        this.update();
    }

    update() {
        fetch("/manager/session")
            .then(response => {
                if (!response.ok) {
                    // this.chargingTarget.innerText = "Unbekannt"
                    throw Error(response.statusText);
                }
                return response.json()
            })
            .then(json => {
                console.log("Received charging session info from wallbox");
                if (json["reason"] === 0) {
                    this.root.getElementsByClassName("vehicle-name-text")[0].innerText = json["vehicle name"];
                } else {
                    this.root.getElementsByClassName("vehicle-name-text")[0].innerText = "nicht verbunden";
                }
                this.root.getElementsByClassName("wb-session-energy")[0].innerText = json["E pres"] / 10000;
            }).catch((error) => {
            console.error('Could not update wallbox info:', error);
        });
        fetch("/keba/power")
            .then(response => {
                if (!response.ok) {
                    // this.chargingTarget.innerText = "Unbekannt"
                    throw Error(response.statusText);
                }
                return response.json()
            })
            .then(json => {
                console.log("Received power info from wallbox");
                this.root.getElementsByClassName("wb-momentary-power")[0].innerText = (json["power"] / 1000).toPrecision(2);

            }).catch((error) => {
            console.error('Could not update wallbox info:', error);
        });
    }
}