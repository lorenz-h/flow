function updatePowerReadings() {
        fetch("/manager/powerwall/soe")
            .then(response => {
                if (!response.ok) {
                    for (let indicator of document.getElementsByClassName("pw-level-indicator")) {
                        indicator.innerText = "Unbekannt";
                    }
                    throw Error(response.statusText);
                }
                return response.json();
            })
            .then(json => {
                for (let indicator of document.getElementsByClassName("pw-level-indicator")) {
                        indicator.innerText = Math.round(json["percentage"]);
                }
            });

    fetch("/manager/meters")
        .then(response => {
            if (!response.ok) {
                // this.chargingTarget.innerText = "Unbekannt"
                throw Error(response.statusText);
            }
            return response.json()
        })
        .then(json => {
            console.log("Received power info from manager");
            document.getElementById("pr-solar").innerText = (json["solar"] / 1000).toPrecision(2);
            document.getElementById("pr-house").innerText = (json["house"] / 1000).toPrecision(2);
            document.getElementById("pr-battery").innerText = (json["battery"] / 1000).toPrecision(2);

            if (Math.abs(json["grid"]) > 80) {
                document.getElementById("pr-grid").innerText = (json["grid"] / 1000).toPrecision(2);
                if (json["grid"] < 0) {
                    document.getElementById("pr-grid").parentElement.classList.add("has-text-success");
                    document.getElementById("pr-grid").parentElement.classList.remove("has-text-danger");
                } else {
                    document.getElementById("pr-grid").parentElement.classList.add("has-text-danger");
                    document.getElementById("pr-grid").parentElement.classList.remove("has-text-success");
                }
            } else {
                document.getElementById("pr-grid").parentElement.classList.remove("has-text-danger");
                document.getElementById("pr-grid").parentElement.classList.remove("has-text-success");
                document.getElementById("pr-grid").innerText = "0.0";
            }

            if (json["battery"] < 0) {
                document.getElementById("pr-battery").parentElement.classList.add("has-text-success");
                document.getElementById("pr-battery").parentElement.classList.remove("has-text-danger");
            } else {
                document.getElementById("pr-battery").parentElement.classList.add("has-text-danger");
                document.getElementById("pr-battery").parentElement.classList.remove("has-text-success");
            }


            document.getElementById("pr-wallbox").innerText = (json["wallbox"] / 1000).toPrecision(2);

        }).catch((error) => {
        console.error('Could not get new power readings:', error);
    });

}

let ctx = document.getElementById('powerHistoryChart');
let powerHistoryChart = new Chart(ctx, {
    type: 'line',
    data: {
        datasets: [
            {
                label: 'Hausverbrauch',
                data: [],
                backgroundColor: 'rgba(54, 54, 54, 0.05)',
                borderColor: 'rgba(54, 54, 54, 0.6)',
            },
            {
                label: 'Netz',
                data: [],
                backgroundColor: 'rgba(255, 56, 96, 0.05)',
                borderColor: 'rgba(255, 56, 96, 0.6)',
            },
            {
                label: 'Wallbox',
                data: [],
                backgroundColor: 'rgba(32, 156, 238, 0.05)',
                borderColor: 'rgba(32, 156, 238, 0.6)',
            },
            {
                label: 'PV',
                data: [],
                backgroundColor: 'rgba(254, 221, 87, 0.05)',
                borderColor: 'rgba(254, 221, 87, 0.6)',
            },
            {
                label: 'Powerwall',
                data: [],
                backgroundColor: 'rgba(72, 199, 116, 0.05)',
                borderColor: 'rgba(72, 199, 116, 0.6)',
            }
        ]
    },
    options: {
        tooltips: {
            callbacks: {
                label: (item) => `${item.yLabel} kW`,
            },
        },
        maintainAspectRatio: false,

        legend: {
           position: "bottom",
            align: "left"
        },
        scales: {
            xAxes: [{
                type: 'time',
                ticks: {
                    autoSkip: true,
                    maxTicksLimit: 7
                }
            }],
            yAxes: [{
                ticks: {
                    // Include kW
                    callback: function(value, index, values) {
                        return value + "kW";
                    }
                }
            }]
        }
    }
});


let datasetNameMap = {
    Hausverbrauch: "house",
    Netz: "grid",
    PV: "solar",
    Powerwall: "battery",
    Wallbox: "wallbox"
}

function addData(chart, data) {
    data.forEach((entry) => {
        chart.data.labels.push(Math.floor(entry["timestamp"] * 1000));
        chart.data.datasets.forEach((dataset) => {
            dataset.data.push(entry[datasetNameMap[dataset.label]] / 1000);
        });
    });
    while (powerHistoryChart.data.length > 100) {
        removeOldestDataPoint(powerHistoryChart);
    }
    chart.update();
}

function removeOldestDataPoint(chart) {
    chart.data.labels.shift();
    chart.data.datasets.forEach((dataset) => {
        dataset.data.shift();
    });
    chart.update();
}

function updateHistoryChart() {
    let labels = powerHistoryChart.data.labels;
    let query = "";
    if (labels.length > 1) {
        query = "?timestamp=" + labels[labels.length - 1]
    }
    fetch("/manager/meters/history" + query)
        .then(response => {
            if (!response.ok) {
                console.log(response.statusText)
                throw Error(response.statusText);
            }
            return response.json()
        })
        .then(json => {
            console.log("Received history update from manager");
            addData(powerHistoryChart, json["history"])

        }).catch((error) => {
        console.error('Could not update wallbox info:', error);
    });
}

updateHistoryChart();
window.setTimeout(updateHistoryChart, 5000)