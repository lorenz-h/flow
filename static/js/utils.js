document.getElementById("toggle-settings-visibility").addEventListener("click", function(){
    let settingsBox =document.getElementById("settings-box")
    settingsBox.classList.toggle("is-hidden");
})

document.getElementById("restart-raspi").addEventListener("click", function(){
    if (window.confirm("Raspberry wirklich neustarten? Dies kann einige Minuten dauern.")) {
        let url = "http://" + config["flow_api_host"] + ":" + config["flow_api_port"] + "/dev/restart"
        fetch(url, {method: "PUT"})
            .then(response => {
                return response.text()
            })
            .then(data => {
                console.log("Raspberry wird neugestartet...");
                location.reload();
            });
    }
})

document.addEventListener("DOMContentLoaded", function(){
    let realConsoleLog = console.log;
    console.log = function () {
        let message = [].join.call(arguments, " ");
        let newline = document.createElement("div");
        newline.innerHTML = "&gt; " + message;
        document.getElementById("console").appendChild(newline);
        realConsoleLog.apply(console, arguments);

        let maxLines = 60;
        let consoleDom = document.getElementById("console");

        if (consoleDom.childNodes.length > maxLines) {
            for (const i of Array(consoleDom.childNodes.length - maxLines).keys()) {
                consoleDom.removeChild(consoleDom.childNodes[0]);
            }
        }


    };
});