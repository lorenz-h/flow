
class PowerFlowMeter {
    constructor(dom, radius, angle) {
        this.dom = dom
        this.dom.style.height = radius ;
        this.dom.style.transform = "translate(-50%, 0) rotate("+angle+"rad)";
        let icon = this.dom.getElementsByClassName("powerflow-meter-icon")[0]
        icon.style.transform = icon.style.transform + " rotate(-"+angle+"rad)";

        let label = this.dom.getElementsByClassName("powerflow-meter-label")[0];
        if (angle > Math.PI / 4){
            label.classList.add("is-top-label");
        } else {
            label.classList.add("is-bottom-label");
        }
    }

}

class PowerFlowCard {
    constructor() {
        this.meters = this.createMeters();
    }
    createMeters() {
        let meters = [];
        let doms = document.getElementsByClassName("powerflow-meter")
        for (let i = 0; i < doms.length; i += 1) {
            let angle = 2 * Math.PI / doms.length * i;
            console.log(angle);
            meters.push(new PowerFlowMeter(doms[i], "40%", angle))
        }
        console.log(meters.length);
        return meters;
    }

    update(){
        console.log("poweflow card updating")
    }
}

