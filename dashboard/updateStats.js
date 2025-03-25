/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const PROCESSING_STATS_API_URL = "http://172.22.0.8:8091/statistics";
const ANALYZER_API_URL = {
    stats: "http://172.22.0.9:8100/stats",
    snow: "http://172.22.0.9:8100/race_event?index=0",
    lift: "http://172.22.0.9:8100/telemetry_event?index=0"
};


// This function fetches and updates the general statistics
const makeReq = (url, cb) => {
    fetch(url)
        .then(res => res.json())
        .then((result) => {
            console.log("Received data: ", result)
            cb(result);
        }).catch((error) => {
            updateErrorMessages(error.message)
        })
}

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerText = JSON.stringify(result)

const getLocaleDateStr = () => (new Date()).toLocaleString()

const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr();

    // Processing stats
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"));

    // Analyzer stats
    makeReq(ANALYZER_API_URL.stats, (statsResult) => {
        updateCodeDiv(statsResult, "analyzer-stats");

        // Get random indexes within bounds
        const raceIndex = Math.floor(Math.random() * statsResult.race_events);
        const telemetryIndex = Math.floor(Math.random() * statsResult.telemetry_data);

        // Fetch random race event
        makeReq(`${ANALYZER_API_URL.snow.split("?")[0]}?index=${raceIndex}`, (result) =>
            updateCodeDiv(result, "event-race")
        );

        // Fetch random telemetry event
        makeReq(`${ANALYZER_API_URL.lift.split("?")[0]}?index=${telemetryIndex}`, (result) =>
            updateCodeDiv(result, "event-telemetry")
        );
    });
};




const updateErrorMessages = (message) => {
    const id = Date.now()
    console.log("Creation", id)
    msg = document.createElement("div")
    msg.id = `error-${id}`
    msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
    document.getElementById("messages").style.display = "block"
    document.getElementById("messages").prepend(msg)
    setTimeout(() => {
        const elem = document.getElementById(`error-${id}`)
        if (elem) { elem.remove() }
    }, 7000)
}

const setup = () => {
    getStats()
    setInterval(() => getStats(), 4000) // Update every 4 seconds
}

document.addEventListener('DOMContentLoaded', setup)
