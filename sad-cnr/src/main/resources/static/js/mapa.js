(() => {
    const BAURU = [-22.3149, -49.0606];
    const map = L.map("map", { zoomControl: true }).setView(BAURU, 13);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap"
    }).addTo(map);

    let heatLayer = null;
    let zonasLayer = null;

    const statusEl = document.getElementById("uploadStatus");
    const totalEl = document.getElementById("totalPacientes");
    const zonasEl = document.getElementById("totalZonas");
    const btn = document.getElementById("btnRefresh");

    function setStatus(msg, ok) {
        statusEl.textContent = msg || "";
        statusEl.className = "status" + (ok === true ? " ok" : ok === false ? " err" : "");
    }

    async function atualizarResumo() {
        try {
            const res = await fetch("/api/predicoes/resumo");
            if (!res.ok) return;
            const data = await res.json();
            totalEl.textContent = `${data.totalPacientes} pacientes`;
            zonasEl.textContent = `· ${data.totalZonas} zonas IA`;
        } catch (_) {
            /* ignore */
        }
    }

    async function carregarZonas() {
        const res = await fetch("/api/predicoes/zonas");
        if (!res.ok) return;
        const geojson = await res.json();
        if (zonasLayer) {
            map.removeLayer(zonasLayer);
        }
        zonasLayer = L.geoJSON(geojson, {
            pointToLayer: (feature, latlng) => {
                const intens = feature.properties.intensidade || 0.5;
                return L.circleMarker(latlng, {
                    radius: 8 + intens * 10,
                    color: "#c53030",
                    weight: 1,
                    fillColor: "#e53e3e",
                    fillOpacity: 0.35
                }).bindPopup(
                    `<strong>${feature.properties.rotulo || "Zona"}</strong><br/>` +
                    `Intensidade: ${(intens * 100).toFixed(0)}%<br/>` +
                    `Pacientes: ${feature.properties.n_pacientes}<br/>` +
                    `Método: ${feature.properties.metodo}`
                );
            }
        }).addTo(map);
    }

    async function carregarHeatmap() {
        const res = await fetch("/api/predicoes/heatmap");
        if (!res.ok) {
            throw new Error("Falha ao carregar /api/predicoes/heatmap");
        }
        const pontos = await res.json();
        if (heatLayer) {
            map.removeLayer(heatLayer);
        }
        heatLayer = L.heatLayer(pontos, {
            radius: 28,
            blur: 22,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.2: "#2b6cb0",
                0.45: "#38a169",
                0.7: "#d69e2e",
                1.0: "#c53030"
            }
        }).addTo(map);

        if (pontos.length > 0) {
            const bounds = L.latLngBounds(pontos.map((p) => [p[0], p[1]]));
            map.fitBounds(bounds.pad(0.15));
        }
        await carregarZonas();
        await atualizarResumo();
        return pontos.length;
    }

    btn.addEventListener("click", async () => {
        btn.disabled = true;
        setStatus("Atualizando predicoes...", null);
        try {
            const n = await carregarHeatmap();
            setStatus(
                n === 0
                    ? "Sem dados. Execute: python scripts/modelo_preditivo_ia.py"
                    : `Heatmap IA com ${n} pontos carregados.`,
                n > 0
            );
        } catch (err) {
            setStatus(err.message || "Falha ao atualizar", false);
        } finally {
            btn.disabled = false;
        }
    });

    carregarHeatmap()
        .then((n) => {
            if (n === 0) {
                setStatus("Nenhuma predicao no banco. Rode o pipeline Python de IA.", null);
            } else {
                setStatus(`Heatmap IA carregado (${n} pontos).`, true);
            }
        })
        .catch(() => setStatus("Nao foi possivel carregar o mapa (API offline?).", false));
})();
