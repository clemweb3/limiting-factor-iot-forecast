let lastDecision = "";

async function updateDashboard() {
    try {
        const res = await fetch('/history');
        const data = await res.json();
        if (!data || data.length === 0) return;

        const latest = data[0];
        const card = document.getElementById('main-card');

        // Trigger Yellow Blink if state changes
        if (lastDecision !== "" && lastDecision !== latest.decision) {
            card.classList.add('transitioning');
            setTimeout(() => {
                card.classList.remove('transitioning');
                renderData(latest);
            }, 3000); // 3-second yellow warning
        } else {
            renderData(latest);
        }
        lastDecision = latest.decision;
    } catch (e) { console.error("Data fetch failed", e); }
}

function renderData(latest) {
    // Logic to update text and colors based on latest.temperature
    document.getElementById('curr-temp').innerText = `${latest.temperature}°C`;
    document.getElementById('cta-text').innerText = latest.human_notes;
    // ... rest of your mapping logic
}

setInterval(updateDashboard, 3000);