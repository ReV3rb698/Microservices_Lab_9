/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const PROCESSING_STATS_API_URL = "/processing/statistics";
const ANALYZER_API_URL = {
    stats: "/analyzer/stats",
    snow: "/analyzer/race_event",
    lift: "/analyzer/telemetry_event",
    checks: "/consistency/checks",
    update: "/consistency/update"
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

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerText = JSON.stringify(result, null, 2)

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
    
    // Get consistency check results
    makeReq(ANALYZER_API_URL.checks, (result) => {
        updateCodeDiv(result, "consistency-results");
        
        // Update the last check time
        if (result.last_updated) {
            const dateVal = result.last_updated;
            const date = typeof dateVal === "number"
                ? new Date(dateVal * 1000)
                : new Date(Date.parse(dateVal));

            document.getElementById("last-check-time").innerText = isNaN(date)
                ? "Unknown"
                : date.toLocaleString();
        }
        
        // Update summary stats
        if (result.counts) {
            document.getElementById("missing-db-count").innerText = result.missing_in_db ? result.not_in_db.length : 0;
            document.getElementById("missing-queue-count").innerText = result.missing_in_queue ? result.not_in_queue.length : 0;
        }
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

const runConsistencyCheck = () => {
    document.getElementById("check-status").innerText = "Running...";
    document.getElementById("check-button").disabled = true;
    
    fetch(ANALYZER_API_URL.update, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("check-status").innerText = `Completed in ${data.processing_time_ms}ms`;
        document.getElementById("check-button").disabled = false;
        // Refresh stats to show new consistency check data
        getStats();
    })
    .catch(error => {
        document.getElementById("check-status").innerText = "Failed";
        document.getElementById("check-button").disabled = false;
        updateErrorMessages(`Error running consistency check: ${error}`);
    });
}

const setup = () => {
    getStats()
    setInterval(() => getStats(), 4000) // Update every 4 seconds
    
    // Add event listener for consistency check button
    document.getElementById("check-form").addEventListener("submit", (e) => {
        e.preventDefault();
        runConsistencyCheck();
    });
}

document.addEventListener('DOMContentLoaded', setup)
